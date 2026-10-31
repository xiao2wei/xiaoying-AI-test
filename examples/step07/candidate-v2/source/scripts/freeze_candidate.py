"""Freeze a local candidate only after all available development/calibration gates pass."""
import argparse,shutil
from pathlib import Path
from policy_agent.common import ROOT,load,save,sha,env,now
p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--dev-report',required=True);p.add_argument('--calibration-report',required=True);p.add_argument('--program-report',required=True);a=p.parse_args()
out=ROOT/'examples/step07'/a.name
if out.exists():raise ValueError('Cannot overwrite a frozen candidate')
dev=load(ROOT/a.dev_report);cal=load(ROOT/a.calibration_report);tests=load(ROOT/a.program_report)
if not (dev['all_applicable_numeric_targets_passed'] and dev['metrics']['M03']['numerator']==12):raise ValueError('开发集尚未12/12且全部适用指标达标，禁止冻结')
if not (cal['calibration_gate_passed'] and cal['human_labels_complete']):raise ValueError('评分校准或真实人工标签尚未完成，禁止冻结')
if not (tests['run']==tests['passed'] and tests['run']>0):raise ValueError('程序检查未全部通过，禁止冻结')
files=sorted([p for d in ['src','tests','scripts'] for p in (ROOT/d).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix in ['.py','.txt']]+[ROOT/'pyproject.toml',ROOT/'requirements.txt'])
manifest={'name':a.name,'created_at':now(),'git_commit':None,'git_note':'用户暂缓GitHub交付；以本地SHA256冻结','source_files':{},'data_files':{},'gate_reports':{k:{'path':v,'sha256':sha(ROOT/v)} for k,v in [('development',a.dev_report),('calibration',a.calibration_report),('program',a.program_report)]},'model_config':{'answer_model':env().get('DEEPSEEK_MODEL','deepseek-flash'),'decision_thinking':'disabled','final_review_thinking':'enabled','judge_model':env().get('DEEPSEEK_JUDGE_MODEL','deepseek-v4-pro'),'judge_thinking':'enabled','judge_reasoning_effort':'low','max_rounds_per_group':12,'max_tools_per_group':10,'judge_parallel_limit':4}}
for f in files:
 rel=f.relative_to(ROOT).as_posix();dest=out/'source'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dest);manifest['source_files'][rel]=sha(f)
for rel in ['data/source/personnel-policies.pdf','data/processed/chunks.json','data/processed/documents.json','data/processed/tables.json','data/cache/index/manifest.json','data/cache/index/vectors.npy','evaluation/dev.json','evaluation/formal.json','evaluation/manifest.json','evaluation/calibration.json']:
 manifest['data_files'][rel]=sha(ROOT/rel)
save(out/'manifest.json',manifest);print('FROZEN',a.name,len(files),flush=True)
