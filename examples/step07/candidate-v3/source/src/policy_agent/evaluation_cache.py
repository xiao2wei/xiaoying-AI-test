"""Reuse only exact-input, valid real judge responses; never cache Agent runs."""
import json,hashlib,threading
from pathlib import Path
from .common import ROOT,save,load,sha
LOCK=threading.Lock()
CACHE=ROOT/'data/cache/judge'
def prompt_hash(messages):return hashlib.sha256(json.dumps(messages,ensure_ascii=False).encode()).hexdigest()
def cache_path(prompt_sha,model,thinking,effort="high"):
 key=hashlib.sha256(json.dumps([prompt_sha,model,thinking,effort,10000,0,'json_object']).encode()).hexdigest()
 return CACHE/(key+'.json')
def get(messages,model):
 p=cache_path(prompt_hash(messages),model.model,model.thinking,getattr(model,'reasoning_effort','high'))
 if not p.exists():return None
 return load(p)
def put(messages,model,trace,source=None):
 entry=next((x for x in reversed(trace) if x.get('kind')=='model' and x.get('http_status')==200 and not x.get('error') and x.get('content')),None)
 if not entry:return
 try:raw=json.loads(entry['content'])
 except ValueError:return
 # A repaired request has different messages; never cache it under the initial prompt.
 if entry['prompt_sha256']!=prompt_hash(messages):return
 item={'raw_judgement':raw,'real_judge_trace':trace,'response_id':entry.get('response_id'),'source':source,'prompt_sha256':entry['prompt_sha256'],'model':model.model,'thinking':model.thinking,'max_tokens':10000,'reasoning_effort':getattr(model,'reasoning_effort','high')}
 with LOCK:save(cache_path(entry['prompt_sha256'],model.model,model.thinking,getattr(model,'reasoning_effort','high')),item)
def warm(paths):
 count=0
 for path in paths:
  obj=load(path)
  rows=obj.get('turns',[obj])
  for row in rows:
   if not row.get('judge') or row.get('judge_error'):continue
   trace=row.get('judge_trace',[])
   e=next((x for x in reversed(trace) if x.get('kind')=='model' and x.get('purpose')=='judge' and x.get('http_status')==200 and not x.get('error')),None)
   if not e or not e.get('content'):continue
   try:raw=json.loads(e['content'])
   except ValueError:continue
   item={'raw_judgement':raw,'real_judge_trace':trace,'response_id':e.get('response_id'),'source':{'path':str(path),'sha256':sha(path)},'prompt_sha256':e['prompt_sha256'],'model':e['model'],'thinking':e.get('thinking','disabled'),'max_tokens':10000,'reasoning_effort':e.get('reasoning_effort','high')}
   with LOCK:save(cache_path(e['prompt_sha256'],e['model'],e.get('thinking','disabled'),e.get('reasoning_effort','high')),item)
   count+=1
 return count
