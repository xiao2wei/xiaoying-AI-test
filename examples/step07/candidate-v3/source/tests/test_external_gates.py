"""Deterministic error-path fixtures, not Agent performance."""
import unittest,tempfile,json
from pathlib import Path
from unittest.mock import patch
from policy_agent.model import DeepSeek,ModelError,SERVICE_FAILURES
from policy_agent.evaluation import calibrate
from policy_agent.agent import agent
from policy_agent.retrieval import Corpus
from test_agent import ScriptedClient
class ExternalGateTests(unittest.TestCase):
 def test_insufficient_balance_stops_further_account_requests(self):
  class Response:status_code=402
  with tempfile.TemporaryDirectory() as td,patch('policy_agent.model.env',return_value={'DEEPSEEK_API_KEY':'UNIT_TEST_NOT_A_REAL_KEY'}),patch.dict(SERVICE_FAILURES,{},clear=True),patch('policy_agent.model.requests.post',return_value=Response()) as post:
   m=DeepSeek();m.key='UNIT_TEST_NOT_A_REAL_KEY';m.ledger=Path(td)/'usage.jsonl';t=[]
   with self.assertRaises(ModelError):m.call([],t)
   with self.assertRaises(ModelError):m.call([],t)
   self.assertEqual(post.call_count,1);self.assertEqual(t[-1]['kind'],'service_block');self.assertFalse(t[-1]['request_sent'])
 def test_failed_judge_is_not_a_correct_negative_label(self):
  with tempfile.TemporaryDirectory() as td:
   r=Path(td);(r/'evaluation').mkdir();(r/'data/processed').mkdir(parents=True)
   rows=[{'id':str(i),'question':str(i),'expected':'insufficient_evidence','points':[],'evidence':[],'read_ids':[],'answer':{'status':'insufficient_evidence','claims':[],'gaps':['fixture']},'proposed_pass':i<6,'human_label':i<6,'fixture_type':'unit_only'} for i in range(12)]
   (r/'evaluation/calibration.json').write_text(json.dumps(rows),encoding='utf-8');(r/'data/processed/chunks.json').write_text('[]')
   def fixture(gold,*args):
    i=int(gold['question']);return {'pass':i<6,'judge_error':'HTTP_402' if i==11 else None}
   with patch('policy_agent.evaluation.ROOT',r),patch('policy_agent.evaluation.judge_turn',fixture):result=calibrate(r/'out')
   self.assertEqual(result['human_agreement'],11);self.assertEqual(result['judge_errors'],['11']);self.assertFalse(result['calibration_gate_passed'])
 def test_final_review_cannot_bypass_round_budget(self):
  d={'action':'finish','result':{'status':'insufficient_evidence','claims':[],'gaps':['请提供对应制度原文。']}}
  result=agent('边界',Corpus(),max_rounds=1,model=ScriptedClient([d]))
  self.assertEqual(result['output']['status'],'limit_reached')
if __name__=='__main__':unittest.main()
