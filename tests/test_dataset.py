import json, unittest
from pathlib import Path
from collections import Counter
R=Path(__file__).resolve().parents[1]
def load(p): return json.loads((R/p).read_text(encoding='utf-8'))
class DatasetTests(unittest.TestCase):
 def setUp(self):
  self.dev=load('evaluation/dev.json');self.formal=load('evaluation/formal.json');self.chunks={c['chunk_id']:c for c in load('data/processed/chunks.json')}
 def test_sizes_and_coverage(self):
  self.assertEqual(len(self.dev),12);self.assertEqual(len(self.formal),40)
  self.assertEqual(Counter(g['category'] for g in self.formal),dict(normal=12,conflict=6,insufficient=6,paraphrase=6,context=5,tool_failure=5))
  self.assertEqual(len(set(g['category'] for g in self.dev)),6)
 def test_sources_and_fields(self):
  for g in self.dev+self.formal:
   self.assertTrue(g['turns']);self.assertFalse(g['review']['unresolved_label_disputes'])
   for t in g['turns']:
    for f in ['question','expected_status','required_points','allowed_actions','forbidden','criteria']:self.assertTrue(t[f],(g['id'],f))
    for e in t['evidence']:
     c=self.chunks[e['chunk_id']]
     for f in ['doc_id','text','pdf_pages','printed_pages','version_date']:self.assertEqual(e[f],c[f])
    for u in t['evidence_units']:self.assertTrue(u);self.assertTrue(all(cid in self.chunks for cid in u))
 def test_split_and_no_answer_index(self):
  self.assertFalse({g['family'] for g in self.dev}&{g['family'] for g in self.formal})
  dq={t['question'] for g in self.dev for t in g['turns']};fq={t['question'] for g in self.formal for t in g['turns']}
  self.assertFalse(dq&fq)
  self.assertTrue(all('question' not in c and 'required_points' not in c for c in self.chunks.values()))
 def test_variants_history_faults_conflicts(self):
  for g in self.dev+self.formal:
   if g['category'] in ['paraphrase','context']:self.assertGreaterEqual(len(g['turns']),2)
   if g['category']=='tool_failure':self.assertIn(g['fault']['mode'],['once','always'])
  self.assertEqual({g['conflict_type'] for g in self.formal if g['category']=='conflict'},{'scope_unknown','priority_unknown','explicit_resolution'})
 def test_manifest_hash_and_frozen_stability(self):
  import hashlib
  m=load('evaluation/manifest.json')
  for split in ['dev','formal']:self.assertEqual(m['files'][split],hashlib.sha256((R/f'evaluation/{split}.json').read_bytes()).hexdigest())
  self.assertEqual(len(set(m['stability_ids'])),10)
if __name__=='__main__':unittest.main()
