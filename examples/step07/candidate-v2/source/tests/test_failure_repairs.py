"""Boundary fixtures only; never reported as real API performance."""
import unittest,tempfile,json
from pathlib import Path
from unittest.mock import patch
from policy_agent.model import DeepSeek
from policy_agent.agent import agent
from policy_agent.retrieval import Corpus
from test_agent import ScriptedClient
class FailureRepairTests(unittest.TestCase):
 def test_exact_failed_tool_budget_reports_limit(self):
  actions=[{'action':'search','arguments':{'query':'示例'}}]*2
  r=agent('工具边界',Corpus(),max_tools=2,fault={'tool':'search','mode':'always','code':'TEMPORARY_UNAVAILABLE'},model=ScriptedClient(actions))
  self.assertEqual(r['output']['status'],'limit_reached');self.assertEqual(r['tool_calls'],2)
 def test_invalid_multi_json_is_returned_for_model_correction(self):
  class Response:
   status_code=200
   def __init__(self,s):self.s=s
   def json(self):return {'id':'unit-test-only','model':'fixture','usage':{},'choices':[{'message':{'content':self.s},'finish_reason':'stop'}]}
  captures=[]
  def fake_post(*args,**kwargs):
   captures.append(json.loads(json.dumps(kwargs['json'])))
   return Response('{}\n{}' if len(captures)==1 else '{"action":"read"}')
  with tempfile.TemporaryDirectory() as td,patch('policy_agent.model.env',return_value={'DEEPSEEK_API_KEY':'UNIT_TEST_NOT_A_REAL_KEY'}):
   m=DeepSeek();m.key='UNIT_TEST_NOT_A_REAL_KEY';m.ledger=Path(td)/'unit.jsonl';trace=[]
   with patch('policy_agent.model.requests.post',fake_post):r=m.call([{'role':'user','content':'fixture'}],trace)
   self.assertEqual(r['action'],'read');self.assertEqual(len(trace),2);self.assertIn('一个完整JSON对象',captures[1]['messages'][-1]['content']);self.assertNotEqual(trace[0]['prompt_sha256'],trace[1]['prompt_sha256'])
if __name__=='__main__':unittest.main()
