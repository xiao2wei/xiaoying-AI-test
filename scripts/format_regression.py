"""Authorized deterministic-format regression: audit every real response, rerun all affected groups."""
import argparse,json,copy,shutil,concurrent.futures
from pathlib import Path
from policy_agent.common import ROOT,load,save,sha,now
from policy_agent.json_format import decode_object
from policy_agent.cli import batch
from policy_agent.evaluation import score

def audit(dataset,runs):
 report={'dataset_sha256':sha(dataset),'runs':str(runs),'valid_unchanged':0,'valid_changed':0,'affected':[],'recovered':[],'still_invalid':[],'source_hashes':{}}
 for g in load(dataset):
  p=Path(runs)/(g['id']+'.json');row=load(p);report['source_hashes'][g['id']]=sha(p)
  for i,t in enumerate(row['turns']):
   for n,e in enumerate(t['trace']):
    if e.get('kind')!='model':continue
    if e.get('finish_reason')=='length' and e.get('purpose') in ['agent','agent_review']:
     if g['id'] not in report['affected']:report['affected'].append(g['id'])
    if not e.get('content'):continue
    text=e['content'];old=None;valid=False
    try:old=json.loads(text);valid=isinstance(old,dict)
    except ValueError:pass
    try:new,repairs=decode_object(text)
    except ValueError:
     if valid:raise ValueError('原合法响应被拒绝')
     report['still_invalid'].append({'id':g['id'],'turn':i,'trace_index':n})
     if e.get('purpose') in ['agent','agent_review'] and g['id'] not in report['affected']:report['affected'].append(g['id'])
     continue
    if valid:
     report['valid_unchanged' if old==new else 'valid_changed']+=1
    else:
     report['recovered'].append({'id':g['id'],'turn':i,'trace_index':n,'response_id':e.get('response_id'),'repairs':repairs})
     if g['id'] not in report['affected']:report['affected'].append(g['id'])
 if report['valid_changed']:raise ValueError('合法响应发生变化，禁止选择性复用')
 if any(g.get('base_id') for g in load(dataset)):
  affected_bases={g['base_id'] for g in load(dataset) if g['id'] in report['affected']}
  report['affected']=[g['id'] for g in load(dataset) if g['base_id'] in affected_bases]
 return report

def execute(dataset,source_runs,source_scores,dest,mode):
 dest=Path(dest)
 if dest.exists():raise ValueError('不覆盖旧回归')
 dest.mkdir(parents=True);plan=audit(dataset,source_runs);save(dest/'audit.json',plan)
 if plan['affected']:batch(dataset,dest/'fresh-runs',mode,workers=3,ids=plan['affected'])
 run_dir=dest/'runs';run_dir.mkdir();provenance=[]
 for g in load(dataset):
  rid=g['id'];fresh=rid in plan['affected'];origin=(dest/'fresh-runs' if fresh else Path(source_runs))/(rid+'.json')
  if not fresh and sha(origin)!=plan['source_hashes'][rid]:raise ValueError('审计后原记录变化')
  shutil.copy2(origin,run_dir/(rid+'.json'))
  provenance.append({'id':rid,'origin':'fresh_real_api' if fresh else 'reused_real_record','source':str(origin),'sha256':sha(origin)})
 save(run_dir/'reuse-manifest.json',{'created_at':now(),'approval':'examples/external-status/reuse-approval-20261031.json','all_groups':len(provenance),'fresh_groups':len(plan['affected']),'records':provenance,'no_best_of_selection':True,'timing':'复用记录保留原真实耗时，新增记录使用新真实耗时；不是同一时段完整新测'})
 score_dir=dest/'scores';score_dir.mkdir()
 if source_scores:
  for g in load(dataset):
   if g['id'] not in plan['affected']:
    p=Path(source_scores)/(g['id']+'.json');row=load(p)
    if row.get('run_sha256')!=sha(run_dir/(g['id']+'.json')):raise ValueError('旧评分与复用记录哈希不一致')
    shutil.copy2(p,score_dir/p.name)
  if plan['affected']:
   subset=dest/'affected-dataset.json';save(subset,[g for g in load(dataset) if g['id'] in plan['affected']]);score(subset,run_dir,dest/'fresh-scores',workers=3)
   for rid in plan['affected']:shutil.copy2(dest/'fresh-scores'/(rid+'.json'),score_dir/(rid+'.json'))
 else:
  score(dataset,run_dir,score_dir,workers=3)
 rows=[load(score_dir/(g['id']+'.json')) for g in load(dataset)]
 save(score_dir/'score-summary.json',{'groups':len(rows),'passed':sum(x['pass'] for x in rows),'unresolved_judges':sum(bool(t.get('judge_error')) for x in rows for t in x['turns']),'reused_scores':len(rows)-len(plan['affected']) if source_scores else 0})
 return plan

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--dataset',required=True);p.add_argument('--runs',required=True);p.add_argument('--scores');p.add_argument('--out',required=True);p.add_argument('--mode',default='agent');p.add_argument('--audit-only',action='store_true');a=p.parse_args()
 if a.audit_only:save(a.out,audit(a.dataset,a.runs))
 else:execute(a.dataset,a.runs,a.scores,a.out,a.mode)
