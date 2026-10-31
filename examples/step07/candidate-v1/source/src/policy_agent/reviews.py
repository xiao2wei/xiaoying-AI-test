"""Append real human reviews without overwriting original AI judgments."""
import argparse,copy,json,shutil
from pathlib import Path
from .common import load,save,sha
from .evaluation import validate_fact_spans
from .validation import normal

def review_metadata(review):
 for f in ['reviewer','confirmed_at','confirmation_source']:
  if not isinstance(review.get(f),str) or not review[f].strip():raise ValueError('缺少真实人工复核信息：'+f)
 if not isinstance(review.get('items'),list) or not review['items']:raise ValueError('没有具体复核项')
 return {k:review[k] for k in ['reviewer','confirmed_at','confirmation_source']}
def apply_review(review_path,dataset,runs,scores,outdir):
 review=load(review_path);meta=review_metadata(review);groups={g['id']:g for g in load(dataset)};runs=Path(runs);scores=Path(scores);outdir=Path(outdir)
 if outdir.exists():raise ValueError('复核输出目录必须全新，禁止覆盖原始评分')
 changed={}
 for item in review['items']:
  rid=item['id'];idx=item['turn'];source=scores/(rid+'.json')
  if item.get('score_sha256')!=sha(source):raise ValueError('待复核评分文件已变化：'+rid)
  if not item.get('reason'):raise ValueError('必须记录核对理由')
  if rid not in changed:changed[rid]=load(source)
  record=changed[rid];sc=record['turns'][idx];gold=groups[rid]['turns'][idx];actual=load(runs/(rid+'.json'))['turns'][idx]
  if item['decision']=='correct':
   j=item['replacement_judge'];validate_fact_spans(j,actual['output'])
   if sorted(p['index'] for p in j['points'])!=list(range(len(gold['required_points']))):raise ValueError('修订要点不齐')
   for p in j['points']:
    if type(p['met']) is not bool:raise ValueError('修订标签不是布尔值')
   for f in j['facts']:
    if any(type(f.get(k)) is not bool for k in ['cited','citation_supported','supported_by_read']):raise ValueError('修订事实字段不完整')
   if any(type(j.get(k)) is not bool for k in ['status_ok','decision_ok','answer_correct']):raise ValueError('修订判断字段不完整')
   critical=list(j['serious_errors'])+sc.get('program_errors',[])
   if any(not f['supported_by_read'] or (f['cited'] and not f['citation_supported']) for f in j['facts']):critical.append('存在无依据结论或不支持引用')
   if actual['output']['status']!=gold['expected_status']:j['status_ok']=False
   sc['original_ai_judge']=copy.deepcopy(sc['judge']);sc['judge']=j;sc['judge_error']=None;sc['critical_errors']=critical
   sc['pass']=all(p['met'] for p in j['points']) and j['status_ok'] and j['decision_ok'] and not critical and all(f['cited'] for f in j['facts'])
  elif item['decision']!='agree':raise ValueError('decision只能是agree或correct')
  sc['human_review']={**meta,'decision':item['decision'],'reason':item['reason'],'source_score_sha256':item['score_sha256']}
  record['pass']=all(t['pass'] for t in record['turns'])
 # All validation happens before writing the new result set.
 shutil.copytree(scores,outdir)
 for rid,record in changed.items():save(outdir/(rid+'.json'),record)
 save(outdir/'human-review-log.json',review)
 return {'reviewed_groups':list(changed),'output':str(outdir),'original_scores_unchanged':True}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--review',required=True);p.add_argument('--dataset',required=True);p.add_argument('--runs',required=True);p.add_argument('--scores',required=True);p.add_argument('--out',required=True);a=p.parse_args();print(json.dumps(apply_review(a.review,a.dataset,a.runs,a.scores,a.out),ensure_ascii=False))
