"""Loopback-only HTTP adapter for the existing real Agent. No alternative model path."""
import argparse
import copy
import json
import mimetypes
import re
import secrets
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

from .common import ROOT, env, load, now, save

MAX_TURNS = 8
MAX_QUESTION = 2000
MAX_TOOLS = 10
MAX_ROUNDS = 12
SESSION_TTL = 3600
MAX_SESSIONS = 30


class APIError(Exception):
    def __init__(self, status, code, message):
        self.status, self.code, self.message = status, code, message
        super().__init__(message)


def public_trace(trace):
    """Expose actual decisions/observations, never model message bodies or reasoning."""
    rows = []
    for event in trace:
        kind = event.get("kind")
        if kind == "decision":
            rows.append({k: copy.deepcopy(event.get(k)) for k in
                         ("kind", "step", "action", "arguments", "reason")})
        elif kind == "tool":
            result = event.get("result", {})
            observation = {"ok": bool(result.get("ok"))}
            if not observation["ok"]:
                observation["error"] = copy.deepcopy(result.get("error", {}))
            if "hits" in result:
                observation["hits"] = [
                    {k: hit.get(k) for k in
                     ("chunk_id", "doc_id", "title", "article", "pdf_pages")}
                    for hit in result["hits"]]
            if "chunk" in result:
                observation["chunk"] = {k: result["chunk"].get(k) for k in
                                        ("chunk_id", "doc_id", "title", "article", "pdf_pages")}
                observation["excerpt"] = result["chunk"].get("text", "")[:300]
            rows.append({"kind": "tool", "name": event.get("name"),
                         "arguments": copy.deepcopy(event.get("arguments", {})),
                         "result": observation, "seconds": event.get("seconds"),
                         "attempt_number": event.get("attempt_number")})
        elif kind == "model":
            rows.append({k: event[k] for k in
                         ("kind", "purpose", "model", "response_model", "response_id",
                          "http_status", "seconds", "usage", "error", "attempt")
                         if k in event})
        elif kind == "service_block":
            rows.append({"kind": kind, "request_sent": False, "error": event.get("error")})
    return rows


def public_result(result):
    return {"question": result["question"], "output": copy.deepcopy(result["output"]),
            "trace": public_trace(result.get("trace", [])),
            "read_ids": result.get("read_ids", []),
            "model_calls": result.get("model_calls", 0),
            "tool_calls": result.get("tool_calls", 0),
            "seconds": result.get("seconds", 0),
            "real_model": bool(result.get("real_model")),
            "validation_errors": result.get("validation_errors", [])}


class WebRuntime:
    """Owns conversation history; clients cannot insert assistant messages or tools."""
    def __init__(self, retriever, runner=None, configured=None, log_dir=None):
        if runner is None:
            from .agent import agent
            runner = agent
        self.retriever, self.runner = retriever, runner
        self.configured = bool(env().get("DEEPSEEK_API_KEY")) if configured is None else configured
        self.log_dir = Path(log_dir) if log_dir else ROOT / "work/web-runs"
        self.sessions = {}
        self.lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="policy-web")
        self.busy = False

    def close(self):
        self.executor.shutdown(wait=True)

    def _session(self, sid):
        session = self.sessions.get(sid)
        if not session:
            raise APIError(404, "SESSION_NOT_FOUND", "对话不存在或服务已重启，请新建对话。")
        if time.monotonic() - session["touched"] > SESSION_TTL and not session["busy"]:
            del self.sessions[sid]
            raise APIError(410, "SESSION_EXPIRED", "对话已过期，请新建对话。")
        session["touched"] = time.monotonic()
        return session

    def create(self):
        with self.lock:
            self.sessions = {k: s for k, s in self.sessions.items()
                             if s["busy"] or time.monotonic() - s["touched"] <= SESSION_TTL}
            if len(self.sessions) >= MAX_SESSIONS:
                raise APIError(429, "SESSION_CAPACITY", "本地会话已达上限，请删除不用的对话。")
            sid = uuid.uuid4().hex
            self.sessions[sid] = {"id": sid, "title": "新对话", "created_at": now(),
                                  "touched": time.monotonic(), "busy": False,
                                  "history": [], "turns": {}}
            return self._view(self.sessions[sid])

    @staticmethod
    def _view(session):
        return {"id": session["id"], "title": session["title"],
                "created_at": session["created_at"], "busy": session["busy"],
                "turns": copy.deepcopy(list(session["turns"].values())),
                "remaining_turns": MAX_TURNS - len(session["turns"])}

    def get(self, sid):
        with self.lock:
            return self._view(self._session(sid))

    def list(self):
        with self.lock:
            expired = [sid for sid, s in self.sessions.items()
                       if not s["busy"] and time.monotonic() - s["touched"] > SESSION_TTL]
            for sid in expired:
                del self.sessions[sid]
            return [{"id": s["id"], "title": s["title"], "busy": s["busy"],
                     "turn_count": len(s["turns"]), "created_at": s["created_at"]}
                    for s in reversed(list(self.sessions.values()))]

    def delete(self, sid):
        with self.lock:
            s = self._session(sid)
            if s["busy"]:
                raise APIError(409, "SESSION_BUSY", "回答尚未完成，暂不能删除该对话。")
            del self.sessions[sid]

    def start(self, sid, question, request_id):
        if not isinstance(question, str) or not question.strip() or len(question) > MAX_QUESTION:
            raise APIError(400, "INVALID_QUESTION", "问题须为1至2000字的非空文本。")
        if not isinstance(request_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{8,80}", request_id):
            raise APIError(400, "INVALID_REQUEST_ID", "请求标识无效，请刷新后重试。")
        question = question.strip()
        with self.lock:
            s = self._session(sid)
            old = s["turns"].get(request_id)
            if old:
                if old["question"] != question:
                    raise APIError(409, "REQUEST_ID_CONFLICT", "同一请求标识不能用于不同问题。")
                return copy.deepcopy(old)
            if not self.configured:
                raise APIError(503, "MODEL_NOT_CONFIGURED", "请先在项目根目录.env配置DeepSeek密钥并重启服务。")
            if s["busy"] or self.busy:
                raise APIError(409, "AGENT_BUSY", "已有回答正在运行，请等待完成后再发送。")
            if len(s["turns"]) >= MAX_TURNS:
                raise APIError(409, "CONVERSATION_LIMIT", "本次对话已达到8轮上限，请新建对话。")
            job = {"id": request_id, "question": question, "state": "running", "created_at": now()}
            s["turns"][request_id] = job
            if len(s["turns"]) == 1:
                s["title"] = question[:22] + ("…" if len(question) > 22 else "")
            s["busy"] = self.busy = True
            history = copy.deepcopy(s["history"])
            self.executor.submit(self._run, sid, request_id, question, history)
            return copy.deepcopy(job)

    def _run(self, sid, rid, question, history):
        try:
            result = self.runner(question, self.retriever, history=history,
                                 max_tools=MAX_TOOLS, max_rounds=MAX_ROUNDS)
            if result["output"]["status"] == "answered" and not result.get("real_model"):
                raise RuntimeError("An answered Web turn must come from the real model")
            public = public_result(result)
            # Private working files are deliberately outside the submitted examples.
            save(self.log_dir / sid / (rid + ".json"), result)
            with self.lock:
                s = self.sessions[sid]
                s["turns"][rid].update(state="completed", result=public, completed_at=now())
                s["history"].extend([
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": json.dumps(result["output"], ensure_ascii=False)}])
        except Exception as ex:
            # No credentials, raw exceptions, request headers or messages cross the API.
            with self.lock:
                self.sessions[sid]["turns"][rid].update(
                    state="error", completed_at=now(),
                    error={"code": "WEB_AGENT_ERROR",
                           "message": "Agent未能完成本轮，请检查本地配置、索引或服务日志。"})
            print("Web Agent task failed:", type(ex).__name__, flush=True)
        finally:
            with self.lock:
                self.sessions[sid]["busy"] = self.busy = False
                self.sessions[sid]["touched"] = time.monotonic()

    def job(self, sid, rid):
        with self.lock:
            s = self._session(sid)
            if rid not in s["turns"]:
                raise APIError(404, "TURN_NOT_FOUND", "本轮请求不存在。")
            return copy.deepcopy(s["turns"][rid])


def metadata(runtime):
    e = env()
    migration = load(ROOT / "evaluation/source-path-migration.json")
    manifest = load(ROOT / "data/processed/manifest.json")
    return {
        "service": "policy-agent-web", "model_configured": runtime.configured,
        "model": e.get("DEEPSEEK_MODEL", "deepseek-flash"),
        "source": {"title": Path(migration["new_path"]).stem, "url": "/api/source.pdf",
                   "pages": manifest.get("page_count", 229),
                   "documents": len({c["doc_id"] for c in runtime.retriever.chunks}),
                   "chunks": len(runtime.retriever.chunks)},
        "limits": {"question_chars": MAX_QUESTION, "turns_per_conversation": MAX_TURNS,
                   "tools_per_turn": MAX_TOOLS, "decision_rounds_per_turn": MAX_ROUNDS,
                   "session_idle_minutes": SESSION_TTL // 60},
        "examples": [
            {"title": "校内申诉期限", "question": "校内申诉从知道权利受侵害之日起多久内提出？因不可抗力逾期，障碍消除后多久可以提起？"},
            {"title": "请假与考勤", "question": "仅按2023请假补充规定，在校工作期间登记结婚可请多少日婚假，须在多久内申请，能分次使用吗？"},
            {"title": "在职进修要求", "question": "在职读博入学第五年还能申请脱产学习吗？首次和累计脱产时间限制是什么？"},
            {"title": "临时用工管理", "question": "临时用工合同期限与试用期一般多久？续签有哪些前提？"}]}


class WebServer(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, address, runtime, static_dir=None, dev_origin=None):
        super().__init__(address, Handler)
        self.runtime = runtime
        self.static_dir = Path(static_dir or ROOT / "frontend/dist").resolve()
        self.csrf = secrets.token_urlsafe(32)
        self.allowed_origins = {f"http://127.0.0.1:{self.server_port}",
                                f"http://localhost:{self.server_port}"}
        if dev_origin:
            if dev_origin not in {"http://127.0.0.1:5173", "http://localhost:5173"}:
                raise ValueError("Only loopback Vite development origins are supported")
            self.allowed_origins.add(dev_origin)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # URLs contain only random IDs, never prompts or credentials.
        print(self.log_date_time_string(), fmt % args, flush=True)

    def _headers(self, status, mime, length, extra=None):
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store" if mime != "application/pdf" else "private, max-age=3600")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("X-Frame-Options", "DENY")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()

    def _json(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self._headers(status, "application/json; charset=utf-8", len(body))
        if self.command != "HEAD":
            self.wfile.write(body)

    def _guard(self, write=False):
        host = self.headers.get("Host", "")
        allowed = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
        if host not in allowed:
            raise APIError(403, "INVALID_HOST", "仅允许本机访问。")
        origin = self.headers.get("Origin")
        if origin and origin not in self.server.allowed_origins:
            raise APIError(403, "INVALID_ORIGIN", "请求来源不受信任。")
        if write and not secrets.compare_digest(self.headers.get("X-Policy-CSRF", ""), self.server.csrf):
            raise APIError(403, "INVALID_CSRF", "页面已失效，请刷新后重试。")

    def _body(self):
        if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
            raise APIError(415, "JSON_REQUIRED", "请求必须为JSON。")
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise APIError(400, "INVALID_BODY", "请求长度无效。")
        if not 0 < length <= 16384:
            raise APIError(413, "BODY_LIMIT", "请求过大或为空。")
        try:
            data = json.loads(self.rfile.read(length))
        except (ValueError, UnicodeDecodeError):
            raise APIError(400, "INVALID_JSON", "JSON格式无效。")
        if not isinstance(data, dict):
            raise APIError(400, "INVALID_BODY", "请求必须为JSON对象。")
        return data

    def _file(self, path, mime):
        if not path.is_file():
            raise APIError(404, "FILE_NOT_FOUND", "文件不存在；前端请先执行npm run build。")
        size = path.stat().st_size
        start, end, code = 0, size - 1, 200
        headers = {"Accept-Ranges": "bytes"}
        requested = self.headers.get("Range")
        if requested:
            match = re.fullmatch(r"bytes=(\d*)-(\d*)", requested)
            if not match or not any(match.groups()):
                raise APIError(416, "INVALID_RANGE", "无效的文件范围。")
            a, b = match.groups()
            if a:
                start = int(a)
                end = min(int(b), size - 1) if b else size - 1
            else:
                start = max(0, size - int(b))
            if start > end or start >= size:
                raise APIError(416, "INVALID_RANGE", "文件范围越界。")
            code = 206
            headers["Content-Range"] = f"bytes {start}-{end}/{size}"
        if mime == "application/pdf":
            headers["Content-Disposition"] = "inline; filename*=UTF-8''" + quote(path.name)
        self._headers(code, mime, end - start + 1, headers)
        if self.command != "HEAD":
            with path.open("rb") as f:
                f.seek(start)
                remaining = end - start + 1
                while remaining:
                    chunk = f.read(min(65536, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        try:
            self._guard()
            path = unquote(urlsplit(self.path).path)
            if path == "/api/config":
                self._json(200, {**metadata(self.server.runtime), "csrf_token": self.server.csrf})
            elif path == "/api/conversations":
                self._json(200, {"conversations": self.server.runtime.list()})
            elif re.fullmatch(r"/api/conversations/[a-f0-9]{32}", path):
                self._json(200, self.server.runtime.get(path.split("/")[3]))
            elif re.fullmatch(r"/api/conversations/[a-f0-9]{32}/turns/[A-Za-z0-9_-]{8,80}", path):
                parts = path.split("/")
                self._json(200, self.server.runtime.job(parts[3], parts[5]))
            elif path == "/api/source.pdf":
                source = ROOT / load(ROOT / "evaluation/source-path-migration.json")["new_path"]
                self._file(source, "application/pdf")
            elif path in {"/", "/index.html"}:
                self._file(self.server.static_dir / "index.html", "text/html; charset=utf-8")
            elif path.startswith("/assets/"):
                target = (self.server.static_dir / path.lstrip("/")).resolve()
                if not target.is_relative_to(self.server.static_dir):
                    raise APIError(404, "NOT_FOUND", "资源不存在。")
                mime = {".js": "text/javascript; charset=utf-8", ".mjs": "text/javascript; charset=utf-8",
                        ".css": "text/css; charset=utf-8", ".svg": "image/svg+xml"}.get(target.suffix.lower())
                self._file(target, mime or mimetypes.guess_type(target.name)[0] or "application/octet-stream")
            else:
                raise APIError(404, "NOT_FOUND", "资源不存在。")
        except APIError as ex:
            self._json(ex.status, {"error": {"code": ex.code, "message": ex.message}})
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as ex:
            print("Web request failed:", type(ex).__name__, flush=True)
            self._json(500, {"error": {"code": "SERVER_ERROR", "message": "本地服务异常，请查看服务日志。"}})

    def do_POST(self):
        try:
            self._guard(write=True)
            data = self._body()
            path = urlsplit(self.path).path
            if path == "/api/conversations":
                self._json(201, self.server.runtime.create())
            elif re.fullmatch(r"/api/conversations/[a-f0-9]{32}/turns", path):
                if set(data) != {"question", "request_id"}:
                    raise APIError(400, "INVALID_FIELDS", "只接收问题与请求标识；历史由服务端管理。")
                job = self.server.runtime.start(path.split("/")[3], data["question"], data["request_id"])
                self._json(202 if job["state"] == "running" else 200, job)
            elif re.fullmatch(r"/api/conversations/[a-f0-9]{32}/delete", path):
                self.server.runtime.delete(path.split("/")[3])
                self._json(200, {"deleted": True})
            else:
                raise APIError(404, "NOT_FOUND", "资源不存在。")
        except APIError as ex:
            self._json(ex.status, {"error": {"code": ex.code, "message": ex.message}})
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as ex:
            print("Web POST failed:", type(ex).__name__, flush=True)
            self._json(500, {"error": {"code": "SERVER_ERROR", "message": "本地服务异常，请查看服务日志。"}})


def main():
    parser = argparse.ArgumentParser(description="Serve Vue UI and the real policy Agent on localhost.")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--dev-origin", choices=["http://127.0.0.1:5173", "http://localhost:5173"])
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    from .retrieval import Retriever
    try:
        retriever = Retriever()
    except Exception as ex:
        raise SystemExit("知识库未就绪，请先运行 python -m policy_agent.cli build-index。错误类型：" + type(ex).__name__) from None
    runtime = WebRuntime(retriever)
    try:
        server = WebServer(("127.0.0.1", args.port), runtime, dev_origin=args.dev_origin)
    except OSError:
        runtime.close()
        raise SystemExit("端口被占用或被系统保留，请使用 --port 指定其他可用端口。") from None
    print(f"Policy Agent Web: http://127.0.0.1:{args.port}", flush=True)
    print("Real DeepSeek configured:", runtime.configured, "| no mock fallback", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        runtime.close()


if __name__ == "__main__":
    main()
