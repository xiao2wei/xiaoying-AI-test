"""Deterministic Web adapter tests. Fixtures are not real-model quality evidence."""
import copy
import http.client
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path

from policy_agent.webapp import APIError, MAX_TURNS, WebRuntime, WebServer, public_trace


class CorpusFixture:
    chunks = [{"doc_id": "D01"}]


class RunnerFixture:
    def __init__(self):
        self.calls = []
        self.entered = threading.Event()
        self.release = threading.Event()
        self.release.set()

    def __call__(self, question, retriever, history, **kwargs):
        self.calls.append((question, copy.deepcopy(history), kwargs))
        self.entered.set()
        self.release.wait(3)
        return {"question": question, "history": history,
                "output": {"status": "insufficient_evidence", "claims": [],
                           "gaps": ["确定性测试夹具：需要提供适用制度。"],
                           "answer": "确定性测试夹具：需要提供适用制度。"},
                "trace": [], "read_ids": [], "model_calls": 0, "tool_calls": 0,
                "seconds": 0, "real_model": False}


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.runner = RunnerFixture()
        self.runtime = WebRuntime(CorpusFixture(), runner=self.runner,
                                  configured=True, log_dir=Path(self.temp.name))
        self.sid = self.runtime.create()["id"]

    def tearDown(self):
        self.runner.release.set()
        self.runtime.close()
        self.temp.cleanup()

    def wait_job(self, sid, rid):
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            result = self.runtime.job(sid, rid)
            if result["state"] != "running":
                return result
            time.sleep(.01)
        self.fail("Web fixture did not finish")

    def test_question_validation_does_not_call_model(self):
        for value in ["", "  ", "x" * 2001, None, {}]:
            with self.assertRaises(APIError) as c:
                self.runtime.start(self.sid, value, "request-001")
            self.assertEqual(c.exception.status, 400)
        self.assertEqual(self.runner.calls, [])

    def test_request_identity_prevents_duplicate_runs(self):
        self.runner.release.clear()
        first = self.runtime.start(self.sid, "测试问题", "request-001")
        self.assertTrue(self.runner.entered.wait(1))
        duplicate = self.runtime.start(self.sid, "测试问题", "request-001")
        self.assertEqual(first["id"], duplicate["id"])
        with self.assertRaises(APIError):
            self.runtime.start(self.sid, "另一问题", "request-001")
        self.assertEqual(len(self.runner.calls), 1)
        self.runner.release.set()
        self.wait_job(self.sid, "request-001")
        self.assertEqual(self.runtime.start(self.sid, "测试问题", "request-001")["state"], "completed")
        self.assertEqual(len(self.runner.calls), 1)

    def test_server_history_and_turn_limits_are_passed_to_existing_runner(self):
        self.runtime.start(self.sid, "第一问", "request-001")
        result = self.wait_job(self.sid, "request-001")
        self.runtime.start(self.sid, "那它呢？", "request-002")
        self.wait_job(self.sid, "request-002")
        history = self.runner.calls[1][1]
        self.assertEqual([x["role"] for x in history], ["user", "assistant"])
        self.assertEqual(history[0]["content"], "第一问")
        self.assertEqual(json.loads(history[1]["content"]), result["result"]["output"])
        self.assertEqual(self.runner.calls[1][2], {"max_tools": 10, "max_rounds": 12})

    def test_new_conversation_has_isolated_history(self):
        self.runtime.start(self.sid, "第一段", "request-001")
        self.wait_job(self.sid, "request-001")
        sid = self.runtime.create()["id"]
        self.runtime.start(sid, "第二段", "request-002")
        self.wait_job(sid, "request-002")
        self.assertEqual(self.runner.calls[1][1], [])

    def test_conversation_cap_is_not_bypassed(self):
        for i in range(MAX_TURNS):
            rid = f"request-{i:03}"
            self.runtime.start(self.sid, f"第{i}问", rid)
            self.wait_job(self.sid, rid)
        with self.assertRaises(APIError) as c:
            self.runtime.start(self.sid, "额外问题", "request-extra")
        self.assertEqual(c.exception.code, "CONVERSATION_LIMIT")
        self.assertEqual(len(self.runner.calls), MAX_TURNS)

    def test_missing_key_never_falls_back_to_mock(self):
        self.runtime.configured = False
        with self.assertRaises(APIError) as c:
            self.runtime.start(self.sid, "问题", "request-001")
        self.assertEqual(c.exception.code, "MODEL_NOT_CONFIGURED")
        self.assertFalse(self.runner.calls)

    def test_busy_turn_blocks_delete_and_extra_run(self):
        self.runner.release.clear()
        self.runtime.start(self.sid, "问题", "request-001")
        self.assertTrue(self.runner.entered.wait(1))
        with self.assertRaises(APIError):
            self.runtime.delete(self.sid)
        with self.assertRaises(APIError):
            self.runtime.start(self.sid, "重复点击", "request-002")
        self.assertEqual(len(self.runner.calls), 1)

    def test_non_real_answered_result_is_rejected(self):
        original = self.runner
        def invalid(*args, **kwargs):
            r = original(*args, **kwargs)
            r["output"]["status"] = "answered"
            return r
        self.runtime.runner = invalid
        self.runtime.start(self.sid, "不能假装真实", "request-001")
        self.assertEqual(self.wait_job(self.sid, "request-001")["state"], "error")

    def test_public_trace_omits_provider_bodies_and_keeps_actual_tool_error(self):
        raw = [
            {"kind": "model", "model": "example", "response_id": "fixture-response",
             "content": "private-body", "reasoning_content": "hidden", "headers": {"Authorization": "secret"}},
            {"kind": "tool", "name": "search", "arguments": {"query": "q"},
             "result": {"ok": False, "error": {"code": "TEMPORARY_UNAVAILABLE"}}, "attempt_number": 1}]
        public = public_trace(raw)
        text = json.dumps(public)
        self.assertNotIn("private-body", text)
        self.assertNotIn("reasoning_content", text)
        self.assertNotIn("Authorization", text)
        self.assertEqual(public[1]["result"]["error"]["code"], "TEMPORARY_UNAVAILABLE")


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.runner = RunnerFixture()
        self.runtime = WebRuntime(CorpusFixture(), runner=self.runner, configured=True,
                                  log_dir=Path(self.temp.name) / "logs")
        static = Path(self.temp.name) / "dist"
        static.mkdir()
        (static / "index.html").write_text("<html>fixture</html>", encoding="utf-8")
        self.server = WebServer(("127.0.0.1", 0), self.runtime, static_dir=static)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.runner.release.set()
        self.server.shutdown()
        self.server.server_close()
        self.runtime.close()
        self.temp.cleanup()

    def request(self, method, path, body=None, headers=None):
        h = {"Content-Type": "application/json", "X-Policy-CSRF": self.server.csrf}
        h.update(headers or {})
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=4)
        conn.request(method, path, body=json.dumps(body).encode() if body is not None else None, headers=h)
        response = conn.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        conn.close()
        return result

    def test_csrf_origin_and_host_reject_requests_before_model_use(self):
        cases = [{"X-Policy-CSRF": ""}, {"Origin": "https://untrusted.example"},
                 {"Host": f"untrusted.example:{self.server.server_port}"}]
        for headers in cases:
            self.assertEqual(self.request("POST", "/api/conversations", {}, headers)[0], 403)
        self.assertFalse(self.runner.calls)

    def test_config_does_not_return_model_credentials(self):
        status, _, raw = self.request("GET", "/api/config")
        self.assertEqual(status, 200)
        data = json.loads(raw)
        self.assertNotIn("DEEPSEEK_API_KEY", data)
        self.assertNotIn("api_key", data)
        self.assertTrue(data["model_configured"])
        self.assertFalse(self.runner.calls)

    def test_only_dist_and_fixed_pdf_are_served(self):
        for path in ["/.env", "/src/policy_agent/model.py", "/assets/../../.env", "/api/unknown"]:
            self.assertEqual(self.request("GET", path)[0], 404)
        self.assertEqual(self.request("GET", "/")[0], 200)
        status, headers, body = self.request("GET", "/api/source.pdf", headers={"Range": "bytes=0-15"})
        self.assertEqual(status, 206)
        self.assertEqual(len(body), 16)
        self.assertTrue(body.startswith(b"%PDF"))
        self.assertIn("bytes 0-15/", headers["Content-Range"])

    def test_javascript_mime_does_not_depend_on_windows_registry(self):
        from unittest.mock import patch
        asset = self.server.static_dir / "assets" / "app.js"
        asset.parent.mkdir()
        asset.write_text("export const ok = true", encoding="utf-8")
        with patch("policy_agent.webapp.mimetypes.guess_type", return_value=("text/plain", None)):
            status, headers, _ = self.request("GET", "/assets/app.js")
        self.assertEqual(status, 200)
        self.assertTrue(headers["Content-Type"].startswith("text/javascript"))

    def test_browser_cannot_supply_fake_assistant_history(self):
        _, _, raw = self.request("POST", "/api/conversations", {})
        sid = json.loads(raw)["id"]
        status, _, _ = self.request("POST", f"/api/conversations/{sid}/turns",
                                   {"question": "q", "request_id": "request-001", "history": []})
        self.assertEqual(status, 400)
        self.assertFalse(self.runner.calls)

    def test_unknown_session_is_not_silently_recreated(self):
        status, _, _ = self.request("POST", "/api/conversations/" + "0" * 32 + "/turns",
                                   {"question": "q", "request_id": "request-001"})
        self.assertEqual(status, 404)
        self.assertFalse(self.runner.calls)


if __name__ == "__main__":
    unittest.main()
