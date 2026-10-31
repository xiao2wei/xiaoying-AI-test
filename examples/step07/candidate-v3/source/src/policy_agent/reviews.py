"""Append real human reviews without overwriting original AI judgments."""
import argparse,copy,json,shutil
from pathlib import Path
from .common import load,save,sha
from .evaluation import validate_fact_spans,checked_judgement
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
   j=item['replacement_judge'];original=copy.deepcopy(sc.get('judge'))
   checked=checked_judgement(j,gold,actual,sc.get('judge_trace',[]))
   sc.update(checked);sc['original_ai_judge']=original;sc['score_origin']='human_corrected'
  elif item['decision']!='agree':raise ValueError('decision只能是agree或correct')
  sc['human_review']={**meta,'decision':item['decision'],'reason':item['reason'],'source_score_sha256':item['score_sha256']}
  record['pass']=all(t['pass'] for t in record['turns'])
 # All validation happens before writing the new result set.
 shutil.copytree(scores,outdir)
 for rid,record in changed.items():save(outdir/(rid+'.json'),record)
 save(outdir/'human-review-log.json',review)
 summary=scores/'score-summary.json'
 if summary.exists():shutil.copy2(summary,outdir/'original-ai-score-summary.json')
 all_rows=[load(outdir/(rid+'.json')) for rid in groups if (outdir/(rid+'.json')).exists()]
 save(outdir/'score-summary.json',{'groups':len(all_rows),'passed':sum(r['pass'] for r in all_rows),'unresolved_judges':sum(bool(t.get('judge_error')) for r in all_rows for t in r['turns']),'human_reviewed_turns':sum(bool(t.get('human_review')) for r in all_rows for t in r['turns'])})
 return {'reviewed_groups':list(changed),'output':str(outdir),'original_scores_unchanged':True}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--review',required=True);p.add_argument('--dataset',required=True);p.add_argument('--runs',required=True);p.add_argument('--scores',required=True);p.add_argument('--out',required=True);a=p.parse_args();print(json.dumps(apply_review(a.review,a.dataset,a.runs,a.scores,a.out),ensure_ascii=False))
