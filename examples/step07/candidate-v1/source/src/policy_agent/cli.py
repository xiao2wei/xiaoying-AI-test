import argparse, json, time, concurrent.futures
from pathlib import Path
from .common import ROOT,load,save,sha,now
from .retrieval import Retriever
from .runtime import baseline

def run_group(group,mode,retriever):
 from .runtime import baseline
 if mode=='agent':
  from .agent import agent
  runner=agent
 else:runner=baseline
 history=[];results=[];start=time.perf_counter();total_tools=0;total_models=0
 for turn in group['turns']:
  if group['mode']!='conversation':history=[]
  remaining=max(0,10-total_tools) if mode=='agent' else 10
  max_tools=min(remaining,(group.get('fault') or {}).get('max_tools',10))
  r=runner(turn['question'],retriever,history,fault=group.get('fault'),max_tools=max_tools,max_rounds=max(0,12-total_models) if mode=='agent' else 12)
  results.append(r);total_tools+=r['tool_calls'];total_models+=r['model_calls']
  history=history+[{'role':'user','content':turn['question']},{'role':'assistant','content':json.dumps(r['output'],ensure_ascii=False)}]
 return {'id':group['id'],'category':group['category'],'mode':mode,'turns':results,'seconds':round(time.perf_counter()-start,4),'model_calls':total_models,'tool_calls':total_tools,'created_at':now()}
def batch(dataset,outdir,mode,workers=2,ids=None):
 groups=load(dataset);groups=[g for g in groups if not ids or g['id'] in ids];outdir=Path(outdir)
 if outdir.exists() and list(outdir.glob('*.json')):raise ValueError('输出目录已有结果，请使用新目录，禁止覆盖历史')
 outdir.mkdir(parents=True,exist_ok=True);r=Retriever();r.search('预热制度检索')
 save(outdir/'run-manifest.json',{'dataset_sha256':sha(dataset),'mode':mode,'ids':[g['id'] for g in groups],'created_at':now(),'workers':workers,'index':load(ROOT/'data/cache/index/manifest.json')})
 def one(g):
  started=time.perf_counter()
  try:result=run_group(g,mode,r)
  except Exception as e:result={'id':g['id'],'category':g['category'],'mode':mode,'turns':[],'error':type(e).__name__+':'+str(e),'seconds':round(time.perf_counter()-started,4),'model_calls':0,'tool_calls':0,'unknown_call_counts':True}
  save(outdir/(g['id']+'.json'),result);print(g['id'],[t['output']['status'] for t in result['turns']],flush=True);return result
 with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:results=list(pool.map(one,groups))
 save(outdir/'batch-summary.json',{'count':len(results),'ids':[x['id'] for x in results],'failures':[x['id'] for x in results if x.get('error')],'model_calls':sum(x['model_calls'] for x in results),'tool_calls':sum(x['tool_calls'] for x in results)})
def main():
 p=argparse.ArgumentParser();s=p.add_subparsers(dest='command',required=True);s.add_parser('build-index')
 q=s.add_parser('ask');q.add_argument('question');q.add_argument('--mode',choices=['baseline','agent'],default='agent');q.add_argument('--output')
 b=s.add_parser('batch');b.add_argument('--dataset',default=str(ROOT/'evaluation/dev.json'));b.add_argument('--out',required=True);b.add_argument('--mode',choices=['baseline','agent'],default='agent');b.add_argument('--workers',type=int,default=2);b.add_argument('--ids',nargs='*')
 a=p.parse_args()
 if a.command=='build-index':r=Retriever(build=True);print(json.dumps(load(r.dir/'manifest.json'),ensure_ascii=False))
 elif a.command=='batch':batch(a.dataset,a.out,a.mode,a.workers,a.ids)
 else:
  r=Retriever();g={'id':'interactive','category':'interactive','mode':'single','turns':[{'question':a.question}]};result=run_group(g,a.mode,r)
  if a.output:save(a.output,result)
  print(json.dumps(result['turns'][0]['output'],ensure_ascii=False,indent=2))
if __name__=='__main__':main()
