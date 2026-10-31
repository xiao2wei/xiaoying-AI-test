"""Sequential development gates; no paid downstream run after a failed prerequisite."""
import argparse,shutil
from policy_agent.common import ROOT,load,save,sha,now
from policy_agent.evaluation import calibrate,score
from policy_agent.cli import batch
from policy_agent.metrics import report
p=argparse.ArgumentParser();p.add_argument('--version',required=True);p.add_argument('--program',required=True);p.add_argument('--probe-id');a=p.parse_args()
b=ROOT/'examples/step07';v=a.version
cal=calibrate(b/('calibration-'+v),workers=4)
if not cal['calibration_gate_passed']:raise SystemExit('CALIBRATION_GATE_FAILED:后续真实请求未启动')
if a.probe_id:
 data=load(ROOT/'evaluation/dev.json');probe=[g for g in data if g['id']==a.probe_id]
 if len(probe)!=1:raise ValueError('probe id不唯一或不存在')
 pd=b/('probe-'+v+'.json');save(pd,probe)
 pr=b/('probe-'+v+'-runs');ps=b/('probe-'+v+'-scores')
 batch(pd,pr,'agent',workers=1)
 judged=score(pd,pr,ps,workers=1)
 if not all(x['pass'] for x in judged):raise SystemExit('PROBE_FAILED:其余开发请求未启动')
 rest=b/('rest-'+v+'-runs');batch(ROOT/'evaluation/dev.json',rest,'agent',workers=4,ids=[g['id'] for g in data if g['id']!=a.probe_id])
 target=b/('agent-dev-'+v)
 if target.exists():raise ValueError('禁止覆盖全量回归')
 target.mkdir()
 for g in data:shutil.copy2((pr if g['id']==a.probe_id else rest)/(g['id']+'.json'),target/(g['id']+'.json'))
 save(target/'run-manifest.json',{'dataset_sha256':sha(ROOT/'evaluation/dev.json'),'mode':'agent','ids':[g['id'] for g in data],'created_at':now(),'probe_first':a.probe_id,'each_group_executed_once':True,'source_directories':[str(pr),str(rest)]})
else:batch(ROOT/'evaluation/dev.json',b/('agent-dev-'+v),'agent',workers=4)
runs=[load(b/('agent-dev-'+v)/(g['id']+'.json')) for g in load(ROOT/'evaluation/dev.json')]
if any(t['output']['status']=='model_error' for r in runs for t in r['turns']):raise SystemExit('ANSWER_API_FAILED:后续评分未启动')
score(ROOT/'evaluation/dev.json',b/('agent-dev-'+v),b/('agent-dev-'+v+'-scores'),workers=4)
result=report(ROOT/'evaluation/dev.json',b/('agent-dev-'+v),b/('agent-dev-'+v+'-scores'),b/('agent-dev-'+v+'-report'),ROOT/a.program)
print('DEVELOPMENT_GATE_PASSED' if result['all_applicable_numeric_targets_passed'] else 'DEVELOPMENT_GATE_FAILED',flush=True)
