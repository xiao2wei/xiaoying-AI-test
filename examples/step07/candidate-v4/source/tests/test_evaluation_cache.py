import unittest,tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from policy_agent import evaluation_cache as cache
from policy_agent.evaluation import judge_turn
class EvaluationCacheTests(unittest.TestCase):
 def test_only_exact_request_reuses_real_judgement(self):
  with tempfile.TemporaryDirectory() as td,patch.object(cache,'CACHE',Path(td)):
   messages=[{'role':'user','content':'fixture'}];model=SimpleNamespace(model='fixture',thinking='enabled')
   trace=[{'kind':'model','http_status':200,'prompt_sha256':cache.prompt_hash(messages),'content':'{"value":1}','response_id':'unit-only'}]
   cache.put(messages,model,trace);self.assertEqual(cache.get(messages,model)['raw_judgement']['value'],1)
   self.assertIsNone(cache.get([{'role':'user','content':'different'}],model));self.assertIsNone(cache.get(messages,SimpleNamespace(model='other',thinking='enabled')))
 def test_failed_response_cannot_be_cached(self):
  with tempfile.TemporaryDirectory() as td,patch.object(cache,'CACHE',Path(td)):
   messages=[];model=SimpleNamespace(model='fixture',thinking='enabled')
   cache.put(messages,model,[{'kind':'model','http_status':402,'error':'HTTP_402'}]);self.assertIsNone(cache.get(messages,model))
 def test_no_judge_request_when_answer_model_unavailable(self):
  with patch('policy_agent.evaluation.DeepSeek') as model:
   result=judge_turn({'expected_status':'answered'},{'output':{'status':'model_error','claims':[],'gaps':['HTTP_402']},'trace':[]})
   self.assertFalse(result['pass']);self.assertEqual(result['judge_trace'],[]);model.assert_not_called()
