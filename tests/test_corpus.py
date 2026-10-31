from pathlib import Path
import json,unittest,hashlib,re
R=Path(__file__).resolve().parents[1]
P=R/'data/processed'
def load(n):return json.loads((P/n).read_text(encoding='utf8'))
class CorpusTests(unittest.TestCase):
 def test_source_and_page_accounting(self):
  m=load('manifest.json');self.assertEqual(m['sha256'],hashlib.sha256((R/m['source']).read_bytes()).hexdigest());p=load('pages.json');self.assertEqual([x['pdf_page'] for x in p],list(range(1,230)));self.assertEqual([x['pdf_page'] for x in p if not x['text'].strip()],[1]);self.assertTrue(all(x['text'].strip() for x in p[5:]))
 def test_document_ranges_and_chunk_provenance(self):
  ds=load('documents.json');cs=load('chunks.json');self.assertEqual(len(ds),29);self.assertEqual(len({x['chunk_id'] for x in cs}),len(cs));seen=[]
  for d in ds:
   seen.extend(range(d['pdf_pages'][0],d['pdf_pages'][1]+1))
   for c in [x for x in cs if x['doc_id']==d['doc_id']]:
    self.assertTrue(c['text'].strip());self.assertTrue(all(d['pdf_pages'][0]<=p<=d['pdf_pages'][1] for p in c['pdf_pages']));self.assertEqual(c['printed_pages'],[p-5 for p in c['pdf_pages']])
  self.assertEqual(seen,list(range(6,230)))
 def test_dates_are_per_document(self):
  ds={d['doc_id']:d for d in load('documents.json')};self.assertEqual(ds['D19']['version_date'],'2020-10-19');self.assertEqual(ds['D20']['version_date'],'2023-12-27');self.assertIsNone(ds['D11']['version_date'])
 def test_comparison_symbols_and_table_relationships(self):
  ts={t['table_id']:t for t in load('tables.json')};self.assertEqual(ts['P007-T01']['rows'][1],['1','≤4','10','工科5，其他学科3']);r=ts['P173-T01']['rows'];self.assertEqual(r[1][0],'＞5日，≤30日');self.assertIn('奖励绩效按请假实际天数扣发',r[1][1]);self.assertIn('不参加当年年度考核',r[3][1]);self.assertTrue(all(t['unassigned_cell_chars']==0 for t in ts.values()))
 def test_no_detached_symbols_or_header_pollution(self):
  cs=load('chunks.json');self.assertTrue(all('辽宁科技大学制度汇编' not in c['text'] for c in cs));self.assertFalse(any(re.search(r'(?m)^[≤≥]+$',c['text']) for c in cs));self.assertLessEqual(max(len(c['text']) for c in cs),2500)
if __name__=='__main__':unittest.main(verbosity=2)
