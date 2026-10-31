import unittest
from policy_agent.metrics import coverage,nearest_rank,ratio,aggregate
class MetricTests(unittest.TestCase):
 def fixture(self):
  t={'search_evaluable':True,'read_evaluable':True,'evidence_units':[['a'],['b']],'answerable':True,'required_points':['p','q']}
  n={'search_evaluable':False,'read_evaluable':False,'evidence_units':[],'answerable':False,'required_points':['refuse']}
  groups=[{'id':'A','category':'normal','turns':[t]},{'id':'B','category':'insufficient','turns':[n]}]
  runs=[{'id':'A','turns':[{'first_hits':['a'],'read_ids':['a','b'],'output':{'status':'answered'}}],'seconds':10,'model_calls':3,'tool_calls':2}, {'id':'B','turns':[{'output':{'status':'insufficient_evidence'}}],'seconds':20,'model_calls':5,'tool_calls':4}]
  j={'answer_correct':False,'points':[{'met':True},{'met':False}],'facts':[{'cited':True,'citation_supported':True,'supported_by_read':True},{'cited':True,'citation_supported':False,'supported_by_read':False}]}
  scores=[{'id':'A','turns':[{'pass':False,'judge':j,'critical_errors':['unsupported'],'program_errors':[]}]},{'id':'B','turns':[{'pass':True,'judge':{'answer_correct':False,'points':[{'met':True}],'facts':[]},'critical_errors':[],'program_errors':[]}]}]
  return groups,runs,scores
 def test_hand_computable_denominators(self):
  r=aggregate(*self.fixture(),program={'passed':4,'run':4});m=r['metrics']
  for mid,v in [('M01',.5),('M02',1),('M03',.5),('M04',0),('M05',.5),('M06',.5),('M07',1),('M08',.5),('M10',1),('M14',1),('M15',1),('M17',20),('M18',4),('M19',3)]:self.assertEqual(m[mid]['value'],v,mid)
  self.assertEqual(m['M01']['denominator'],1);self.assertEqual(m['M03']['denominator'],2);self.assertEqual(m['M06']['denominator'],2)
 def test_na_not_perfect(self):
  x=ratio('empty',0,0,1);self.assertIsNone(x['value']);self.assertIsNone(x['passed'])
  self.assertIsNone(aggregate(*self.fixture())['metrics']['M09']['value'])
 def test_nearest_rank_40(self):self.assertEqual(nearest_rank(list(range(1,41))),38)
 def test_duplicate_hits_no_double_count(self):self.assertEqual(coverage([['a','aa'],['b']],['a','a','aa']),.5)
 def test_missing_failure_remains_denominator(self):
  g,r,s=self.fixture();v=aggregate(g,r[:1],s[:1]);self.assertEqual(v['metrics']['M03']['denominator'],2);self.assertEqual(v['metrics']['M03']['value'],0);self.assertTrue(v['unresolved']);self.assertFalse(v['metrics']['M17']['passed'])
 def test_stability_all_30_required(self):
  from policy_agent.common import load,ROOT
  ids=load(ROOT/'evaluation/manifest.json')['stability_ids']
  rows=[{'id':id,'repeat':rep,'pass':i*3+rep<=27,'critical_errors':[]} for i,id in enumerate(ids) for rep in [1,2,3]];v=aggregate(*self.fixture(),stability=rows);self.assertTrue(v['metrics']['M16']['passed'])
  v=aggregate(*self.fixture(),stability=rows[:-1]);self.assertFalse(v['metrics']['M16']['passed'])
  rows[-1]=rows[0];v=aggregate(*self.fixture(),stability=rows);self.assertFalse(v['metrics']['M16']['passed'])
 def test_program_failure_cannot_average_away(self):
  v=aggregate(*self.fixture(),program={'passed':3,'run':4});self.assertFalse(v['metrics']['M14']['passed']);self.assertEqual(v['metrics']['M14']['value'],5/6)
if __name__=='__main__':unittest.main()
