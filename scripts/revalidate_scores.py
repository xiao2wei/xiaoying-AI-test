"""Replay saved raw real judgments through deterministic checks; zero model calls."""
import argparse,json
from policy_agent.common import ROOT,load,save,sha
from policy_agent.evaluation import checked_judgement
from policy_agent.metrics import report
p=argparse.ArgumentParser();p.add_argument('--dataset',required=True);p.add_argument('--runs',required=True);p.add_argument('--scores',required=True);p.add_argument('--out',required=True);p.add_argument('--program',required=True);a=p.parse_args()
dataset=ROOT/a.dataset;runs=ROOT/a.runs;src=ROOT/a.scores;dst=ROOT/a.out
if dst.exists():raise ValueError('禁止覆盖原评分')
rows=[]
for g in load(dataset):
 old=load(src/(g['id']+'.json'));actual=load(runs/(g['id']+'.json'));new=[]
 for gold,result,original in zip(g['turns'],actual['turns'],old['turns']):
  responses=[e for e in original['judge_trace'] if e.get('kind')=='model' and e.get('content')]
  if not responses:new.append(original);continue
  try:item=checked_judgement(json.loads(responses[-1]['content']),gold,result,original['judge_trace'])
  except (ValueError,KeyError,TypeError) as e:item={**original,'pass':False,'judge_error':type(e).__name__+':'+str(e)}
  item.update(revalidated_from=str(src/(g['id']+'.json')),new_judge_requests=0);new.append(item)
 row={**old,'turns':new,'pass':all(t['pass'] for t in new)};save(dst/(g['id']+'.json'),row);rows.append(row)
save(dst/'manifest.json',{**load(src/'manifest.json'),'revalidated_from':str(src),'new_model_calls':0,'checker_sha256':sha(ROOT/'src/policy_agent/evaluation.py')})
save(dst/'score-summary.json',{'groups':len(rows),'passed':sum(r['pass'] for r in rows),'unresolved_judges':sum(bool(t.get('judge_error')) for r in rows for t in r['turns']),'new_model_calls':0})
report(dataset,runs,dst,dst/'report',ROOT/a.program)
print('REVALIDATED',sum(r['pass'] for r in rows),'/',len(rows),flush=True)
