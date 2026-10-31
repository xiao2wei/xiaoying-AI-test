import unittest,sys
from policy_agent.common import ROOT
sys.path.insert(0,str(ROOT/'scripts'))
from finalize_review import review_coverage
class ReviewCoverageTests(unittest.TestCase):
 def test_old_failed_group_still_requires_actual_review_after_correction(self):
  groups=[{'id':'X','category':'normal','turns':[{}]}];old={'X':{'pass':False}}
  new={'X':{'pass':True,'turns':[{'human_review':None}]}}
  self.assertFalse(review_coverage(groups,old,new)['complete'])
  new['X']['turns'][0]['human_review']={k:'UNIT_FIXTURE' for k in ['reviewer','confirmed_at','confirmation_source','decision','reason','source_score_sha256']}
  self.assertTrue(review_coverage(groups,old,new)['complete'])
