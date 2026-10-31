import unittest,tempfile,sys,json
from pathlib import Path
from policy_agent.common import ROOT,save
sys.path.insert(0,str(ROOT/'scripts'))
from format_regression import audit
class RegressionAuditTests(unittest.TestCase):
 def test_all_malformed_groups_and_all_three_repetitions_included(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);runs=p/'runs';runs.mkdir();groups=[]
   for rep in [1,2,3]:
    rid=f'R{rep}';groups.append({'id':rid,'base_id':'BASE'})
    content='{"action":"search"}}' if rep==2 else '{"action":"search"}'
    save(runs/(rid+'.json'),{'turns':[{'trace':[{'kind':'model','purpose':'agent','content':content,'finish_reason':'stop'}]}]})
   save(p/'data.json',groups);result=audit(p/'data.json',runs)
   self.assertEqual(result['affected'],['R1','R2','R3']);self.assertEqual(result['valid_changed'],0);self.assertEqual(result['valid_unchanged'],2)
 def test_rejected_nonjson_retry_still_counts_as_affected(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);runs=p/'runs';runs.mkdir();save(p/'data.json',[{'id':'A'}]);save(runs/'A.json',{'turns':[{'trace':[{'kind':'model','purpose':'agent','content':'{} fabricated observation','finish_reason':'stop'}]}]})
   result=audit(p/'data.json',runs);self.assertEqual(result['affected'],['A']);self.assertEqual(len(result['still_invalid']),1)
