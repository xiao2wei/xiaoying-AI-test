import unittest,tempfile,json
from pathlib import Path
from unittest.mock import patch
from policy_agent.model import DeepSeek
class StrictActionTests(unittest.TestCase):
 def test_invalid_action_uses_strict_retry_and_only_real_object(self):
  captures=[]
  class Response:
   status_code=200
   def __init__(self,n):self.n=n
   def json(self):
    m={'content':'{"action":"read"}<system>编造观察</system>'} if self.n==1 else {'content':None,'tool_calls':[{'id':'unit','type':'function','function':{'name':'submit_action','arguments':json.dumps({'decision':{'action':'read','arguments':{'chunk_ids':['D01-C001']},'reason':'unit'}})}}]}
    return {'id':'unit-only','usage':{},'choices':[{'message':m,'finish_reason':'stop' if self.n==1 else 'tool_calls'}]}
  def post(url,**kw):captures.append((url,kw['json']));return Response(len(captures))
  with tempfile.TemporaryDirectory() as td,patch('policy_agent.model.env',return_value={'DEEPSEEK_API_KEY':'UNIT'}),patch('policy_agent.model.requests.post',post):
   m=DeepSeek();m.ledger=Path(td)/'ledger';trace=[];r=m.call([{'role':'user','content':'unit'}],trace,'agent')
   self.assertEqual(r['action'],'read');self.assertEqual(len(trace),2);self.assertTrue(captures[1][0].endswith('/beta/chat/completions'));self.assertNotIn('response_format',captures[1][1]);self.assertTrue(captures[1][1]['tools'][0]['function']['strict']);self.assertEqual(trace[1]['format_repairs'],['strict_action_tool_retry'])
if __name__=='__main__':unittest.main()
