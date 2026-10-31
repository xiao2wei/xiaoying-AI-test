import re, time, numpy as np
from fastembed import TextEmbedding
from rank_bm25 import BM25Okapi
from .common import ROOT, load, save, sha
MODEL='BAAI/bge-small-zh-v1.5'
def tokens(s):
 s=re.sub(r'\s+','',s.lower());return re.findall(r'[a-z0-9]+',s)+[s[i:i+2] for i in range(len(s)-1) if re.search(r'[\u4e00-\u9fff]',s[i:i+2])]
class Corpus:
 def __init__(self):
  self.chunks=load(ROOT/'data/processed/chunks.json');self.by_id={c['chunk_id']:c for c in self.chunks}
  self.tables={t['table_id']:t for t in load(ROOT/'data/processed/tables.json')}
 def read(self,cid):
  if cid not in self.by_id:return {'ok':False,'error':{'code':'INVALID_CHUNK_ID','retryable':False,'message':'片段ID不存在'}}
  c=self.by_id[cid]
  return {'ok':True,'chunk':c,'tables':[self.tables[x] for x in c['table_ids']]}
class Retriever(Corpus):
 def __init__(self,build=False):
  super().__init__();self.dir=ROOT/'data/cache/index';self.dir.mkdir(parents=True,exist_ok=True)
  self.model=TextEmbedding(model_name=MODEL,cache_dir=str(ROOT/'data/cache/models'),threads=4)
  self.windows=[]
  for i,c in enumerate(self.chunks):
   body=c['text'];title=c['title']+' '+c['article']+' '
   for start in range(0,len(body),260):self.windows.append({'chunk_index':i,'text':title+body[start:start+330]})
  self.lexical=BM25Okapi([tokens(w['text']) for w in self.windows])
  self.fingerprint=sha(ROOT/'data/processed/chunks.json')
  if build:self.build()
  else:
   m=load(self.dir/'manifest.json')
   if m['corpus_sha256']!=self.fingerprint or m['model']!=MODEL:raise ValueError('索引过期，请重新build-index')
   self.vectors=np.load(self.dir/'vectors.npy')
   if len(self.vectors)!=len(self.windows):raise ValueError('索引窗口数量不一致')
 def build(self):
  t=time.perf_counter();self.vectors=np.asarray(list(self.model.passage_embed([w['text'] for w in self.windows],batch_size=32)))
  self.vectors/=np.maximum(np.linalg.norm(self.vectors,axis=1,keepdims=True),1e-12)
  np.save(self.dir/'vectors.npy',self.vectors)
  save(self.dir/'manifest.json',dict(corpus_sha256=self.fingerprint,model=MODEL,window_count=len(self.windows),chunk_count=len(self.chunks),dimensions=int(self.vectors.shape[1]),seconds=time.perf_counter()-t,config={'window_chars':330,'stride':260,'fusion':'RRF20 lexical+dense','top_k':5}))
 def search(self,query,k=5,doc_ids=None):
  if not isinstance(query,str) or not query.strip() or len(query)>2000:return {'ok':False,'error':{'code':'INVALID_QUERY','retryable':False,'message':'query应为1至2000字的非空字符串'}}
  if k!=5:return {'ok':False,'error':{'code':'INVALID_K','retryable':False,'message':'本实验固定top_k=5'}}
  if doc_ids and (not isinstance(doc_ids,list) or any(x not in {c['doc_id'] for c in self.chunks} for x in doc_ids)):return {'ok':False,'error':{'code':'INVALID_DOC_ID','retryable':False,'message':'文档过滤ID无效'}}
  vec=np.asarray(next(self.model.query_embed(query)));vec/=max(np.linalg.norm(vec),1e-12)
  sem=self.vectors@vec;lex=self.lexical.get_scores(tokens(query))
  scores=np.zeros(len(self.chunks));best={};ls=np.full(len(self.chunks),-1e9);ds=ls.copy()
  for j,w in enumerate(self.windows):
   i=w['chunk_index'];ls[i]=max(ls[i],lex[j]);ds[i]=max(ds[i],sem[j])
   if i not in best or sem[j]>sem[best[i]]:best[i]=j
  for arr in [ls,ds]:
   for rank,i in enumerate(np.argsort(-arr)):scores[i]+=1/(20+rank+1)
  inds=[int(i) for i in np.argsort(-scores) if not doc_ids or self.chunks[i]['doc_id'] in doc_ids][:k]
  hits=[]
  for i in inds:
   c=self.chunks[i];h={f:c[f] for f in ['chunk_id','doc_id','title','article','version_date','pdf_pages','printed_pages']}
   h.update(score=round(float(scores[i]),6),semantic_score=round(float(ds[i]),6),lexical_score=round(float(ls[i]),4),excerpt=self.windows[best[i]]['text'],related_table_chunks=c['related_table_chunks'])
   hits.append(h)
  return {'ok':True,'query':query,'hits':hits,'note':'候选摘要不是已读取原文。须read后引用；日期不自动确定优先关系。低相关候选不能证明有答案。'}
