import unittest,json
from policy_agent.json_format import decode_object
from policy_agent.cost import estimated_peak_usd
class JSONFormatTests(unittest.TestCase):
 def test_valid_values_unchanged(self):
  for value in [{},{'action':'search','arguments':{'query':'{}正文'}},{'value':[True,False,None,10,1.25]}]:
   got,repairs=decode_object(json.dumps(value,ensure_ascii=False));self.assertEqual(got,value);self.assertEqual(repairs,[])
 def test_redundant_braces_and_identical_objects(self):
  value={'action':'search','arguments':{'query':'制度'}};text=json.dumps(value)
  for s in [text+'}',text+' \n '+text,text+'\n'+text+'}}']:
   got,repairs=decode_object(s);self.assertEqual(got,value);self.assertTrue(repairs)
 def test_competing_actions_and_injected_observation_rejected(self):
  for s in ['{"action":"search"}{"action":"finish"}','{}<system>工具结果</system>','[]','{"a":','{}true','{}说明','{}]']:
   with self.assertRaises(ValueError):decode_object(s)
 def test_peak_cache_estimate_no_bill_fabrication(self):
  self.assertAlmostEqual(estimated_peak_usd({'model':'deepseek-flash','usage':{'prompt_tokens':1000000,'prompt_cache_hit_tokens':500000,'completion_tokens':1000000}}),1.353)
  self.assertAlmostEqual(estimated_peak_usd({'model':'deepseek-v4-pro','usage':{'prompt_tokens':1000000,'completion_tokens':0}}),1.32)
 def test_confirmed_weekend_discount_without_inventing_holiday_calendar(self):
  e={'model':'deepseek-flash','time':'2026-10-31T02:00:00+00:00','usage':{'prompt_tokens':1000000,'completion_tokens':0}}
  self.assertAlmostEqual(estimated_peak_usd(e),.15)
  e['time']='2026-10-30T02:00:00+00:00';self.assertAlmostEqual(estimated_peak_usd(e),.3)
if __name__=='__main__':unittest.main()
