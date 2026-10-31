import unittest,copy
from policy_agent.retrieval import Corpus,Retriever,tokens
from policy_agent.validation import validate,normal
from policy_agent.tools import ToolSession
class RuntimeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.r=Retriever()
 def test_hybrid_search_and_read(self):
  r=self.r.search('人才科研建设专项经费项目最长执行期限');self.assertTrue(r['ok']);self.assertEqual(len(r['hits']),5)
  self.assertIn('D03-C008',[h['chunk_id'] for h in r['hits']]);self.assertEqual(self.r.read('D03-C008')['chunk']['pdf_pages'],[13])
  self.assertIn('科研',tokens('科研经费'));self.assertFalse(self.r.read('BAD')['ok']);self.assertFalse(self.r.search('')['ok'])
 def test_provenance_rejects_unread_and_fake_quote(self):
  c=self.r.by_id['D03-C008'];read={c['chunk_id']:c};out={'status':'answered','claims':[{'text':'最长一般4年','citations':[{'chunk_id':c['chunk_id'],'quote':'项目执行期限最长一般不得超过4年。'}]}],'gaps':[]}
  self.assertEqual(validate(out,read),[]);self.assertTrue(validate(out,{}))
  out['claims'][0]['citations'][0]['quote']='最长99年';self.assertTrue(validate(out,read));self.assertEqual(normal('a b\nc'),'abc')
 def test_once_failure_and_budget_counts_attempts(self):
  trace=[];s=ToolSession(self.r,trace,{'tool':'read','mode':'once','code':'TEMPORARY_UNAVAILABLE'},2)
  self.assertFalse(s.execute('read',{'chunk_id':'D03-C008'})['ok']);self.assertTrue(s.execute('read',{'chunk_id':'D03-C008'})['ok'])
  self.assertEqual(s.execute('search',{'query':'经费'})['error']['code'],'LIMIT_REACHED');self.assertEqual(s.count,2);self.assertEqual(len(trace),2)
 def test_persistent_error_and_bad_arguments(self):
  s=ToolSession(self.r,[],{'tool':'search','mode':'always','code':'PERSISTENT_UNAVAILABLE'})
  for _ in range(2):self.assertFalse(s.execute('search',{'query':'经费'})['ok'])
  self.assertFalse(s.execute('read',{'chunk_id':'NOPE'})['ok']);self.assertEqual(s.count,3)
if __name__=='__main__':unittest.main()
