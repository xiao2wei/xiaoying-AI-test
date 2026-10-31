"""Deterministic content-policy guards; not model-performance samples."""
import unittest
from policy_agent.content_scoring import classify_turn,group_outcome,summarize
class ContentPolicyTests(unittest.TestCase):
 def test_verified_content_can_have_incomplete_citations(self):
  a={'output':{'status':'answered'}}
  r={'verdict':'correct','citation_issue':True,'reason':'Fixture: PDF supports the fact','evidence':[{'chunk_id':'fixture'}]}
  self.assertEqual(classify_turn(a,{'pass':False},r)['outcome'],'correct_with_citation_note')
 def test_no_evidence_cannot_automatically_become_correct(self):
  with self.assertRaises(ValueError):classify_turn({'output':{'status':'answered'}},{'pass':False},{'verdict':'correct','reason':'Unverified','evidence':[]})
 def test_unreviewed_failure_remains_unverified(self):
  self.assertEqual(classify_turn({'output':{'status':'answered'}},{'pass':False})['outcome'],'unverified')
 def test_wrong_turn_fails_whole_conversation(self):
  self.assertEqual(group_outcome([{'outcome':'correct'},{'outcome':'incorrect'}]),'incorrect')
 def test_incomplete_is_not_error_or_correct_completion(self):
  rows=[{'outcome':'correct','turns':[{'citation_issue':False}]},{'outcome':'incomplete','turns':[{'citation_issue':False}]}]
  r=summarize(rows);self.assertEqual(r['incorrect_answer_groups'],0);self.assertEqual(r['incomplete_groups'],1);self.assertEqual(r['correct_handling_rate'],.5)
 def test_expected_stop_is_labeled_as_handling(self):
  r=classify_turn({'output':{'status':'limit_reached'}},{'pass':True});self.assertEqual(r['outcome'],'correct_handling')
 def test_empty_sample_is_not_one_hundred_percent(self):
  self.assertIsNone(summarize([])['correct_handling_rate'])
