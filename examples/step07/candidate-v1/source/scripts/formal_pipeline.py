"""Real formal runs. Every group and repetition is preserved; no best-of selection."""
import argparse,copy,json,concurrent.futures
from pathlib import Path
from policy_agent.common import ROOT,load,save,sha,now
from policy_agent.cli import batch
from policy_agent.evaluation import score
from policy_agent.metrics import report
p=argparse.ArgumentParser();p.add_argument('--version',required=True);p.add_argument('--phase',choices=['run','score','report'],required=True);a=p.parse_args()
base=ROOT/'examples/step08'/a.version
formal=ROOT/'evaluation/formal.json';data=load(formal);ids=load(ROOT/'evaluation/manifest.json')['stability_ids'];subset=[]
for g in data:
 if g['id'] in ids:
  for rep in [1,2,3]:
   x=copy.deepcopy(g);x.update(base_id=g['id'],repeat=rep,id=f"STAB-{g['id']}-R{rep}");subset.append(x)
stable_data=base/'stability-dataset.json'
if a.phase=='run':
 if base.exists():raise ValueError('版本目录已存在；不覆盖旧运行')
 save(stable_data,subset)
 save(base/'protocol.json',{'version':a.version,'created_at':now(),'formal_sha256':sha(formal),'stability_ids':ids,'repetitions':3,'no_best_of_selection':True,'phase':'formal' if a.version=='v1' else 'regression_after_test_exposure'})
 def one(mode):batch(formal,base/(mode+'-runs'),mode,workers=4)
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:list(ex.map(one,['baseline','agent']))
 batch(stable_data,base/'stability-runs','agent',workers=4)
 save(base/'runs-completed.json',{'formal_per_mode':40,'stability':30})
elif a.phase=='score':
 jobs=[('baseline',formal),('agent',formal),('stability',stable_data)]
 def one(item):name,dataset=item;score(dataset,base/(name+'-runs'),base/(name+'-scores'),workers=6)
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:list(ex.map(one,jobs))
else:
 observations=[]
 for g in load(stable_data):
  s=load(base/'stability-scores'/(g['id']+'.json'))
  gap_scores=[t.get('judge',{}).get('actionable_gap',{}).get('passed',False) if t.get('judge') else False for gt,t in zip(g['turns'],s['turns']) if gt['expected_status'] in ['needs_confirmation','insufficient_evidence']]
  observations.append({'id':g['base_id'],'repeat':g['repeat'],'pass':s['pass'],'critical_errors':[e for t in s['turns'] for e in t.get('critical_errors',[])],'judge_errors':[t['judge_error'] for t in s['turns'] if t.get('judge_error')],'actionable_applicable':bool(gap_scores),'actionable_pass':all(gap_scores) if gap_scores else None})
 save(base/'stability-observations.json',observations)
 for mode in ['baseline','agent']:
  report(formal,base/(mode+'-runs'),base/(mode+'-scores'),base/(mode+'-report'),ROOT/'examples/step07/program-tests.json',base/'stability-observations.json' if mode=='agent' else None)
 print('REPORT_COMPLETE',flush=True)
