"""Real formal runs. Every group and repetition is preserved; no best-of selection."""
import argparse,copy,json,concurrent.futures
from pathlib import Path
from policy_agent.common import ROOT,load,save,sha,now
from policy_agent.cli import batch
from policy_agent.evaluation import score
from policy_agent.metrics import report
p=argparse.ArgumentParser();p.add_argument('--version',required=True);p.add_argument('--phase',choices=['run','score','score-agent','score-baseline','report','report-agent'],required=True);p.add_argument('--candidate',default='candidate-v2');a=p.parse_args()
base=ROOT/'examples/step08'/a.version
formal=ROOT/'evaluation/formal.json';data=load(formal);ids=load(ROOT/'evaluation/manifest.json')['stability_ids'];subset=[]
for g in data:
 if g['id'] in ids:
  for rep in [1,2,3]:
   x=copy.deepcopy(g);x.update(base_id=g['id'],repeat=rep,id=f"STAB-{g['id']}-R{rep}");subset.append(x)
stable_data=base/'stability-dataset.json'
if a.phase=='run':
 if base.exists():raise ValueError('版本目录已存在；不覆盖旧运行')
 candidate=load(ROOT/'examples/step07'/a.candidate/'manifest.json')
 for rel,h in {**candidate['source_files'],**candidate['data_files']}.items():
  if sha(ROOT/rel)!=h:raise ValueError('冻结后文件变化:'+rel)
 save(stable_data,subset)
 save(base/'protocol.json',{'version':a.version,'candidate':a.candidate,'candidate_manifest_sha256':sha(ROOT/'examples/step07'/a.candidate/'manifest.json'),'created_at':now(),'formal_sha256':sha(formal),'stability_ids':ids,'repetitions':3,'no_best_of_selection':True,'phase':'formal' if a.version=='v1' else 'regression_after_test_exposure'})
 def one(mode):batch(formal,base/(mode+'-runs'),mode,workers=4)
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:list(ex.map(one,['baseline','agent']))
 batch(stable_data,base/'stability-runs','agent',workers=4)
 save(base/'runs-completed.json',{'formal_per_mode':40,'stability':30})
elif a.phase in ['score','score-agent','score-baseline']:
 jobs=[('baseline',formal),('agent',formal),('stability',stable_data)]
 if a.phase=='score-agent':jobs=[j for j in jobs if j[0]!='baseline']
 if a.phase=='score-baseline':jobs=[j for j in jobs if j[0]=='baseline']
 def one(item):name,dataset=item;score(dataset,base/(name+'-runs'),base/(name+'-scores'),workers=6)
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:list(ex.map(one,jobs))
else:
 observations=[]
 for g in load(stable_data):
  s=load(base/'stability-scores'/(g['id']+'.json'))
  gap_scores=[t.get('judge',{}).get('actionable_gap',{}).get('passed',False) if t.get('judge') else False for gt,t in zip(g['turns'],s['turns']) if gt['expected_status'] in ['needs_confirmation','insufficient_evidence']]
  observations.append({'id':g['base_id'],'repeat':g['repeat'],'pass':s['pass'],'critical_errors':[e for t in s['turns'] for e in t.get('critical_errors',[])],'judge_errors':[t['judge_error'] for t in s['turns'] if t.get('judge_error')],'actionable_applicable':bool(gap_scores),'actionable_pass':all(gap_scores) if gap_scores else None})
 save(base/'stability-observations.json',observations)
 candidate_name=load(base/'protocol.json').get('candidate','candidate-v1')
 candidate=load(ROOT/'examples/step07'/candidate_name/'manifest.json')
 program=ROOT/candidate['gate_reports']['program']['path'] if 'gate_reports' in candidate else ROOT/'examples/step07/program-tests.json'
 for mode in (['agent'] if a.phase=='report-agent' else ['baseline','agent']):
  report(formal,base/(mode+'-runs'),base/(mode+'-scores'),base/(mode+'-report'),program,base/'stability-observations.json' if mode=='agent' else None)
 print('REPORT_COMPLETE',flush=True)
