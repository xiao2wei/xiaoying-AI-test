from pathlib import Path
import json,re,hashlib
from urllib.parse import unquote
R=Path(__file__).resolve().parents[1];B=R/'examples/step08/v4'
files={'agent':'docs/LATEST-TEST-RESULTS.md','baseline':'docs/reports/v4-baseline-qa.md','stability':'docs/reports/v4-stability-qa.md'}
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
checks={};missing_links=[]
for mode,rel in files.items():
 text=(R/rel).read_text(encoding='utf-8');groups=read(B/'stability-dataset.json') if mode=='stability' else read(R/'evaluation/formal.json')
 pairs=re.findall(r'\*\*问：\*\*\n\n(.*?)\n\n\*\*实际回答：\*\*\n\n(.*?)\n\n任务状态：',text,re.S)
 actual=[t for g in groups for t in read(B/(mode+'-runs')/(g['id']+'.json'))['turns']]
 assert len(pairs)==len(actual)
 for (q,a),t in zip(pairs,actual):
  restore=lambda s:'\n'.join(x[2:] if x.startswith('> ') else x for x in s.split('\n'))
  assert restore(q)==t['question']
  assert restore(a)==t['output']['answer']
 assert text.count('<details>')==text.count('</details>') and text.count('<details>')>=len(actual)
 checks[mode]={'pairs_verified':len(actual),'actual_questions_and_answers_exact':True,'collapsible_sections_balanced':True}
for rel in list(files.values())+['docs/FAILED-CASES.md','docs/SUBMISSION.md','README.md','examples/submission/README.md','docs/CONTENT-POLICY.md','data/README.md','docs/03-evaluation.md','docs/01-requirements.md']:
 text=(R/rel).read_text(encoding='utf-8')
 for link in re.findall(r'\]\(([^)]+)\)',text):
  if link.startswith(('http://','https://','#')):continue
  target=link.split('#')[0]
  if target and not (R/rel).parent.joinpath(unquote(target)).exists():missing_links.append([rel,link])
assert not missing_links,missing_links
manifest=read(R/'examples/submission/readable-report-audit.json')
for rel,h in manifest['source_sha256'].items():assert hashlib.sha256((R/rel).read_bytes()).hexdigest()==h
for mode,rel in files.items():
 rows=read(B/'content-policy-v1'/(mode+'-assessments.json'))
 dataset=read(B/'stability-dataset.json') if mode=='stability' else read(R/'evaluation/formal.json')
 assert len(rows)==len(dataset) and sum(len(g['turns']) for g in rows)==checks[mode]['pairs_verified']
 checks[mode]['content_assessment_groups']=len(rows)
 checks[mode]['output_sha256_verified']=hashlib.sha256((R/rel).read_bytes()).hexdigest()==manifest['counts'][mode]['sha256']
 assert checks[mode]['output_sha256_verified']
out={'passed':True,'checks':checks,'broken_local_links':missing_links,'source_files_unchanged':True,'new_model_requests':0,'qa_count':sum(x['pairs_verified'] for x in checks.values())}
(R/'examples/submission/readable-report-validation.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(out,ensure_ascii=False))
