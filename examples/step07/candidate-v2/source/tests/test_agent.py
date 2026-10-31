"""Deterministic boundary tests. Scripted clients here are NOT model performance evidence."""
import unittest
from policy_agent.agent import agent
from policy_agent.retrieval import Corpus
from policy_agent.model import ModelError
class ScriptedClient:
 def __init__(self,actions):self.actions=iter(actions)
 def call(self,messages,trace,purpose,**kwargs):return next(self.actions)
class AgentBoundaryTests(unittest.TestCase):
 def test_model_round_limit(self):
  r=agent('边界测试',Corpus(),max_rounds=2,model=ScriptedClient([{'action':'bad'},{'action':'bad'}]))
  self.assertEqual(r['output']['status'],'limit_reached');self.assertEqual(r['tool_calls'],0)
 def test_batch_cannot_bypass_tool_limit(self):
  r=agent('边界测试',Corpus(),max_tools=1,model=ScriptedClient([{'action':'read','arguments':{'chunk_ids':['D03-C008','D03-C013']}}]))
  self.assertEqual(r['output']['status'],'limit_reached');self.assertEqual(r['tool_calls'],1);self.assertEqual(r['read_ids'],['D03-C008'])
 def test_invalid_parameters_counted(self):
  r=agent('边界测试',Corpus(),max_rounds=1,model=ScriptedClient([{'action':'read','arguments':{'chunk_ids':[]}}]))
  self.assertEqual(r['tool_calls'],1);self.assertEqual(r['trace'][1]['result']['error']['code'],'INVALID_CHUNK_ID')
 def test_false_citation_not_exposed(self):
  fake={'status':'answered','claims':[{'text':'编造内容','citations':[{'chunk_id':'D03-C008','quote':'编造内容'}]}],'gaps':[]}
  r=agent('边界测试',Corpus(),max_rounds=1,model=ScriptedClient([{'action':'finish','result':fake}]))
  self.assertEqual(r['output']['status'],'limit_reached');self.assertFalse(r['output']['claims']);self.assertTrue(r['validation_errors'])
 def test_model_exception_not_success(self):
  class Broken:
   def call(self,*a,**kwargs):raise ModelError('TEST_ONLY_ERROR')
  r=agent('边界测试',Corpus(),model=Broken());self.assertEqual(r['output']['status'],'model_error')
if __name__=='__main__':unittest.main()
