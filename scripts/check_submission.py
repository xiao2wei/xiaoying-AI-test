"""Offline delivery checks, without generating answers or changing recorded scores."""
import argparse,json,re,subprocess
from pathlib import Path
from policy_agent.common import ROOT,load,save,sha

def check(out):
 r=ROOT;results=[]
 def record(name,ok,detail=None):results.append({'check':name,'passed':bool(ok),'detail':detail})
 required=['README.md','.env.example','requirements.txt','pyproject.toml','constraints-tested.txt','docs/01-requirements.md','docs/02-solution.md','docs/03-evaluation.md','docs/04-ai-usage.md','docs/05-retrospective.md','docs/SUBMISSION.md','scripts/demo_offline.py']
 record('required_files',all((r/p).is_file() for p in required),required)
 m=load(r/'examples/step07/candidate-v4/manifest.json');derived=[p for p in m['source_files'] if '.egg-info/' in p]
 controlled={p:h for p,h in m['source_files'].items() if p not in derived}|m['data_files']
 migration=load(r/'evaluation/source-path-migration.json')
 renamed={migration['old_path']:migration['new_path']}
 adjusted={x['path']:x for x in migration['modified_scripts']}
 changed=[]
 for p,h in controlled.items():
  current=r/renamed.get(p,p)
  if not current.is_file():changed.append(p);continue
  if p in adjusted:
   import hashlib
   restored=current.read_bytes().replace(migration['new_path'].encode('utf-8'),migration['old_path'].encode('utf-8'))
   valid=hashlib.sha256(restored).hexdigest()==h and sha(current)==adjusted[p]['after_sha256']
  else:valid=sha(current)==h
  if not valid:changed.append(p)
 record('frozen_controlled_files',not changed,{'checked':len(controlled),'changed':changed,'source_path_migration':migration,'excluded_generated_packaging_metadata':derived,'reason':'PDF字节不变；仅允许已记录的PDF路径迁移，两个脚本逆替换后须恢复原冻结哈希；egg-info为安装生成文件。'})
 ex=load(r/'examples/submission/manifest.json');record('six_acceptance_categories',len(ex)==6 and len({x['category'] for x in ex})==6)
 for x in ex:
  raw=load(r/x['run_source']);sc=load(r/x['score_source'])
  record('real_example_'+x['id'],sha(r/x['run_source'])==x['run_sha256']==sha(r/'examples/submission'/(x['id']+'.json')) and sc['pass'] and all(t['real_model'] for t in raw['turns']))
 complete=load(r/'examples/step08/v4/score-completion-r1/completion-summary.json')
 record('all_actual_scores_present',sum(v['valid_turns'] for v in complete['modes'].values())==138 and not any(v['unresolved'] for v in complete['modes'].values()))
 review=load(r/'examples/step08/v4/human-reviewed-r1/completion.json');coverage=load(r/'examples/step08/v4/human-reviewed-r1/human-review-coverage.json')
 record('actual_user_confirmation',review['human_review_complete'] and review['raw_scores_unchanged'] and sum(v['reviewed_turns'] for v in coverage.values())==56 and all(v['complete'] for v in coverage.values()))
 record('metric_acceptance_keeps_failures',review['metric_acceptance_complete'] and not review['formal_numeric_targets_passed'] and review['original_metric_gates_passed']==14)
 repro=load(r/'examples/submission/reproduction/summary.json');tests=load(r/'examples/submission/reproduction/program-tests.json')
 record('clean_environment_reproduction',repro['passed'] and repro['clean_virtual_environment'] and not repro['source_env_copied'] and repro['vector_index_rebuilt'] and tests['run']==61 and tests['passed']==61,repro['steps'])
 offline=load(r/'examples/submission/offline-mock/summary.json');record('offline_mock_separated',offline['mode']=='OFFLINE_MOCK' and offline['real_api_requests']==0 and not offline['model_quality_evidence'] and len(offline['cases'])==3)
 perturb=load(r/'examples/submission/evidence-change/summary.json');record('real_document_view_change',perturb['passed'] and perturb['not_in_formal_40_or_stability_30'],perturb['checks'])
 record('personal_time_honest',load(r/'examples/submission/time-record.json')['personal_time']=='未计时')
 files=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=r).decode().split('\0');files=[p for p in files if p and (r/p).is_file()]
 forbidden=[p for p in files if p=='.env' or p.startswith(('data/cache/','work/','.venv/')) or p in ['examples/external-status/deepseek-20261031.json','examples/external-status/tls-check-20261031.json']]
 record('private_and_generated_files_excluded',not forbidden,forbidden)
 secret=[];reasoning=[];large=[]
 for p in files:
  f=r/p
  if f.stat().st_size>=100_000_000:large.append(p)
  if f.suffix.lower() in ['.py','.json','.jsonl','.md','.txt','.log','.toml'] or f.name in ['.env.example','.gitignore']:
   txt=f.read_text(encoding='utf-8',errors='replace')
   if re.search(r'(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)',txt):secret.append(p)
   if re.search(r'"reasoning_content"\s*:\s*"[^"\n]{20}',txt):reasoning.append(p)
 record('no_detected_live_secrets',not secret,secret);record('no_internal_reasoning_body',not reasoning,reasoning);record('file_size_limits',not large,large)
 report={'passed':all(x['passed'] for x in results),'checks':results,'candidate_file_count':len(files),'candidate_size_bytes':sum((r/p).stat().st_size for p in files),'new_model_requests':0,'note':'程序交付检查不证明全部模型答案正确；人工确认和已知质量失败单独保留。'}
 save(out,report);print(json.dumps({'passed':report['passed'],'checks':len(results),'failed':[x['check'] for x in results if not x['passed']],'candidate_file_count':len(files)},ensure_ascii=False))
 if not report['passed']:raise SystemExit(1)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();check(a.out)
