import unittest
from policy_agent.evaluation import checked_judgement
from policy_agent.metrics import aggregate
class ActionableGapTests(unittest.TestCase):
 def record(self,passed):
  text='资料没有操作步骤，请提供VPN系统名称和官方操作指南。'
  out={'status':'insufficient_evidence','claims':[],'gaps':[text]}
  j={'points':[{'index':0,'met':True,'answer_span':text}],'status_ok':True,'decision_ok':True,'answer_correct':True,'facts':[],'serious_errors':[],'actionable_gap':{'passed':passed,'requested_items':['VPN系统名称','官方操作指南'] if passed else []}}
  gold={'expected_status':'insufficient_evidence','required_points':['说明缺口']};result={'output':out,'trace':[]}
  return j,gold,result
 def test_vague_gap_fails_task_even_if_other_checks_pass(self):
  j,g,r=self.record(False);self.assertFalse(checked_judgement(j,g,r,[])['pass'])
 def test_specific_gap_passes(self):
  j,g,r=self.record(True);self.assertTrue(checked_judgement(j,g,r,[])['pass'])
 def test_missing_metric_cannot_silently_pass(self):
  j,g,r=self.record(True);del j['actionable_gap']
  with self.assertRaises(ValueError):checked_judgement(j,g,r,[])
 def test_original_human_calibration_boundary_is_preserved(self):
  j,g,r=self.record(True);del j['actionable_gap'];g['skip_gap_metric']=True
  self.assertTrue(checked_judgement(j,g,r,[])['pass'])
if __name__=='__main__':unittest.main()
