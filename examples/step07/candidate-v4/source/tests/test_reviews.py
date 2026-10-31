import unittest,tempfile
from pathlib import Path
from policy_agent.reviews import review_metadata,apply_review
from policy_agent.common import save,load,sha
class ReviewTests(unittest.TestCase):
 def test_missing_human_identity_rejected(self):
  with self.assertRaises(ValueError):review_metadata({'reviewer':None,'items':[{}]})
 def test_review_preserves_original_and_requires_hash(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);scores=p/'scores';runs=p/'runs';scores.mkdir();runs.mkdir()
   raw={'id':'X','pass':True,'turns':[{'pass':True,'judge':{'points':[]},'human_review':None}]}
   save(scores/'X.json',raw);save(runs/'X.json',{'turns':[{'output':{'claims':[],'gaps':[]}}]});save(p/'data.json',[{'id':'X','turns':[{}]}])
   h=sha(scores/'X.json');review={'reviewer':'UNIT_TEST_FIXTURE_NOT_REAL_PERSON','confirmed_at':'test-only','confirmation_source':'deterministic_unit_fixture','items':[{'id':'X','turn':0,'score_sha256':h,'decision':'agree','reason':'test-only'}]};save(p/'review.json',review)
   apply_review(p/'review.json',p/'data.json',runs,scores,p/'reviewed')
   self.assertEqual(sha(scores/'X.json'),h);self.assertIsNone(load(scores/'X.json')['turns'][0]['human_review']);self.assertIsNotNone(load(p/'reviewed/X.json')['turns'][0]['human_review'])
   review['items'][0]['score_sha256']='changed';save(p/'review.json',review)
   with self.assertRaises(ValueError):apply_review(p/'review.json',p/'data.json',runs,scores,p/'invalid')
   self.assertFalse((p/'invalid').exists())
 def test_human_correction_cannot_bypass_specific_gap_requirement(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);scores=p/'scores';runs=p/'runs';scores.mkdir();runs.mkdir()
   save(scores/'X.json',{'id':'X','pass':False,'turns':[{'pass':False,'judge':None,'judge_trace':[],'program_errors':[],'human_review':None}]})
   save(runs/'X.json',{'turns':[{'output':{'status':'insufficient_evidence','claims':[],'gaps':['请自行查资料。']},'trace':[]}]})
   save(p/'data.json',[{'id':'X','turns':[{'expected_status':'insufficient_evidence','required_points':[]}]}])
   replacement={'points':[],'facts':[],'status_ok':True,'decision_ok':True,'answer_correct':True,'serious_errors':[],'actionable_gap':{'passed':False,'requested_items':[],'reason':'缺口不具体'}}
   review={'reviewer':'UNIT_FIXTURE','confirmed_at':'test','confirmation_source':'test','items':[{'id':'X','turn':0,'score_sha256':sha(scores/'X.json'),'decision':'correct','reason':'unit-only','replacement_judge':replacement}]};save(p/'review.json',review)
   apply_review(p/'review.json',p/'data.json',runs,scores,p/'reviewed')
   self.assertFalse(load(p/'reviewed/X.json')['pass'])
if __name__=='__main__':unittest.main()
