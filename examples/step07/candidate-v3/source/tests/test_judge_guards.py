import unittest
from policy_agent.evaluation import validate_fact_spans
class JudgeGuardTests(unittest.TestCase):
 def test_omitted_gold_not_a_spoken_fact(self):
  with self.assertRaises(ValueError):validate_fact_spans({'facts':[{'answer_span':'报销必须符合预算'}]},{'claims':[{'text':'5000元由项目负责人签字'}],'gaps':[]})
 def test_spoken_facts_only(self):
  validate_fact_spans({'facts':[{'answer_span':'5000元由项目负责人签字'}]},{'claims':[{'text':'5000元由项目负责人签字。'}],'gaps':[]})
 def test_no_silent_empty_judgement(self):
  with self.assertRaises(ValueError):validate_fact_spans({'facts':[]},{'claims':[{'text':'费用99万元'}],'gaps':[]})
 def test_refusal_can_have_no_facts(self):validate_fact_spans({'facts':[]},{'claims':[],'gaps':['资料不足，请提供文件']})
class CrossClaimSpanTests(unittest.TestCase):
 def fixture(self):
  from policy_agent.retrieval import Corpus
  c=Corpus().by_id['D03-C008'];a='项目执行期限最长一般不得超过4年。';b='项目执行期满后，结余经费由学校统筹管理。'
  out={'status':'answered','claims':[{'text':s,'citations':[{'chunk_id':'D03-C008','quote':s}]} for s in [a,b]],'gaps':[]}
  result={'output':out,'trace':[{'kind':'tool','name':'read','result':{'ok':True,'chunk':c}}]}
  j={'points':[{'index':0,'met':True,'answer_span':a+'\n'+b,'reason':'两条均明确表达'}],'status_ok':True,'decision_ok':True,'answer_correct':True,'facts':[{'text':s,'answer_span':s,'cited':True,'citation_supported':True,'supported_by_read':True} for s in [a,b]],'serious_errors':[]}
  return j,{'required_points':['期限与结余'],'expected_status':'answered'},result
 def test_adjacent_claim_span_is_valid(self):
  from policy_agent.evaluation import checked_judgement
  j,g,r=self.fixture();self.assertTrue(checked_judgement(j,g,r,[])['pass'])
 def test_unspoken_point_still_rejected(self):
  from policy_agent.evaluation import checked_judgement
  j,g,r=self.fixture();j['points'][0]['answer_span']='实际答案没说过这句话'
  with self.assertRaises(ValueError):checked_judgement(j,g,r,[])
if __name__=='__main__':unittest.main()

