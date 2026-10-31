"""Reapply corrected deterministic checks to ALL saved real judge responses; no new AI calls."""
import json
from pathlib import Path
from policy_agent.common import ROOT,load,save,sha
from policy_agent.evaluation import checked_judgement
from policy_agent.metrics import report
G=load(ROOT/'evaluation/dev.json')
for name,runs in [('agent','examples/step05/agent-dev-v2'),('baseline','examples/step04/baseline-dev-v1')]:
 src=ROOT/f'examples/step06/{name}-scores-v5';dst=ROOT/f'examples/step06/{name}-scores-v6'
 if dst.exists():raise ValueError('不得覆盖')
 for g in G:
  old=load(src/(g['id']+'.json'));actual=load(ROOT/runs/(g['id']+'.json'));new=[]
  for i,(gold,original) in enumerate(zip(g['turns'],old['turns'])):
   contents=[e['content'] for e in original['judge_trace'] if e.get('content')]
   if not contents:new.append(original);continue
   try:j=checked_judgement(json.loads(contents[-1]),gold,actual['turns'][i],original['judge_trace'])
   except (ValueError,KeyError,TypeError) as e:j={**original,'pass':False,'judge_error':type(e).__name__+':'+str(e)}
   j['revalidated_from']=str(src/(g['id']+'.json'));new.append(j)
  row={**old,'turns':new,'pass':all(t['pass'] for t in new),'revalidation':'只修正连续跨claim原句定位的程序检查；实际AI判断内容与调用ID不变'}
  save(dst/(g['id']+'.json'),row)
 save(dst/'manifest.json',{**load(src/'manifest.json'),'revalidated_from':str(src),'new_model_calls':0,'checker_sha256':sha(ROOT/'src/policy_agent/evaluation.py')})
 report(ROOT/'evaluation/dev.json',ROOT/runs,dst,ROOT/f'examples/step06/{name}-report-v6',ROOT/'examples/step06/program-tests.json')
 print(name,'complete')
