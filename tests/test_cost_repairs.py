import unittest,tempfile
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from policy_agent.model import DeepSeek,ModelError
from policy_agent.validation import validate
from policy_agent import evaluation_cache as cache
class CostRepairTests(unittest.TestCase):
 def test_truncation_does_not_repeat_same_paid_request(self):
  class Response:
   status_code=200
   def json(self):return {'choices':[{'message':{'content':''},'finish_reason':'length'}],'usage':{}}
  with tempfile.TemporaryDirectory() as td,patch('policy_agent.model.env',return_value={'DEEPSEEK_API_KEY':'UNIT_ONLY'}),patch('policy_agent.model.requests.post',return_value=Response()) as post:
   model=DeepSeek(thinking='enabled',reasoning_effort='low');model.ledger=Path(td)/'ledger';trace=[]
   with self.assertRaises(ModelError):model.call([{'role':'user','content':'unit'}],trace)
   self.assertEqual(post.call_count,1);self.assertEqual(trace[0]['error'],'OUTPUT_TOKEN_LIMIT_REACHED');self.assertEqual(post.call_args.kwargs['json']['reasoning_effort'],'low')
 def test_reasoning_effort_changes_cache_identity(self):
  self.assertNotEqual(cache.cache_path('a','model','enabled','high'),cache.cache_path('a','model','enabled','low'))
 def test_document_number_requires_quoted_number(self):
  c={'chunk_id':'X','doc_id':'D','title':'标题','article':'第一条','pdf_pages':[1],'printed_pages':[1],'version_date':None,'text':'文件校发〔2023〕10号。第一条：每月25日。'}
  out={'status':'answered','claims':[{'text':'依据校发〔2023〕10号，每月25日。','citations':[{'chunk_id':'X','quote':'第一条：每月25日。'}]}],'gaps':[]}
  self.assertTrue(any('document_number' in x for x in validate(out,{'X':c})))
  out['claims'][0]['citations'][0]['quote']=c['text'];self.assertEqual(validate(out,{'X':c}),[])
