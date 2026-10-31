"""Run the user's approved format-only regression protocol, never best-of selection."""
import argparse,shutil,concurrent.futures
from policy_agent.common import ROOT,load,save,sha,now
from format_regression import audit,execute
p=argparse.ArgumentParser();p.add_argument('--version',required=True);p.add_argument('--source',default='v2');p.add_argument('--candidate',required=True);a=p.parse_args()
b=ROOT/'examples/step08'/a.version;old=ROOT/'examples/step08'/a.source
if b.exists():raise ValueError('新版本目录已存在')
candidate=load(ROOT/'examples/step07'/a.candidate/'manifest.json')
for rel,h in {**candidate['source_files'],**candidate['data_files']}.items():
 if sha(ROOT/rel)!=h:raise ValueError('冻结文件变化:'+rel)
# Prompt/data equality is mandatory; an interface-retry-only change cannot authorize a business change.
previous=load(ROOT/'examples/step07'/load(old/'protocol.json')['candidate']/'manifest.json')
for rel,h in previous['source_files'].items():
 if '/prompts/' in rel and candidate['source_files'].get(rel)!=h:raise ValueError('提示词变化，不允许选择性复用')
if candidate['data_files']!=previous['data_files']:raise ValueError('知识、题库或索引变化，不允许选择性复用')
allowed={'src/policy_agent/model.py'}
for rel,h in previous['source_files'].items():
 if rel.startswith('src/') and '/prompts/' not in rel and candidate['source_files'].get(rel)!=h and rel not in allowed:raise ValueError('未经审计的业务源文件变化:'+rel)
permitted_new={'src/policy_agent/json_format.py','src/policy_agent/action_schema.py','src/policy_agent/cost.py'}
for rel in candidate['source_files']:
 if rel.startswith('src/') and rel not in previous['source_files'] and rel not in permitted_new:raise ValueError('未经审计的新增业务模块:'+rel)
if candidate['model_config']!=previous['model_config']:raise ValueError('模型或调用配置变化，禁止选择性复用')
b.mkdir(parents=True);shutil.copy2(old/'stability-dataset.json',b/'stability-dataset.json')
save(b/'protocol.json',{'version':a.version,'source':a.source,'candidate':a.candidate,'created_at':now(),'phase':'exposed_test_regression_with_hash_reuse','approval':'examples/external-status/reuse-approval-20261031.json','candidate_manifest_sha256':sha(ROOT/'examples/step07'/a.candidate/'manifest.json'),'formal_sha256':sha(ROOT/'evaluation/formal.json'),'repetitions':3,'no_best_of_selection':True,'limitations':'未受影响组保留原运行时间与真实输出，不能宣称全量新运行'})
jobs=[]
for name in ['agent','stability','baseline']:
 dataset=b/'stability-dataset.json' if name=='stability' else ROOT/'evaluation/formal.json'
 plan=audit(dataset,old/(name+'-runs'));save(b/(name+'-audit.json'),plan)
 print(name,'FRESH',plan['affected'],flush=True);jobs.append((name,dataset))
def one(item):
 name,dataset=item;old_scores=old/(name+'-scores')
 execute(dataset,old/(name+'-runs'),old_scores if old_scores.exists() else None,b/(name+'-regression'),'baseline' if name=='baseline' else 'agent')
 shutil.copytree(b/(name+'-regression')/'runs',b/(name+'-runs'));shutil.copytree(b/(name+'-regression')/'scores',b/(name+'-scores'))
 print(name,'COMPLETE',flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(one,jobs))
save(b/'runs-completed.json',{'formal_per_mode':40,'stability':30,'source_reuse':True})
