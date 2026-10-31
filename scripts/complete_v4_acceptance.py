"""Record explicit user agreement; preserve all AI scores and accepted limitations."""
from pathlib import Path
from datetime import datetime,timezone
import json
from policy_agent.common import ROOT,load,save,sha
from policy_agent.reviews import apply_review
from policy_agent.metrics import report
from finalize_review import review_coverage

def main():
 b=ROOT/'examples/step08/v4';s=b/'score-completion-r1';out=b/'human-reviewed-r1'
 if out.exists():raise ValueError('Do not overwrite review records')
 packet=load(b/'human-review-packet-r1/pending-review.json')
 confirmation=load(ROOT/'evaluation/human-review-v4-confirmation.json')
 assert confirmation['decision']=='agree_with_existing_assessments'
 assert len(packet['items'])==56 and confirmation['packet_sha256']==sha(b/'human-review-packet-r1/pending-review.json')
 out.mkdir();coverage={}
 for mode in ['agent','baseline','stability']:
  meta={k:confirmation[k] for k in ['reviewer','confirmed_at','confirmation_source']}
  items=[]
  for x in packet['items']:
   if x['mode']!=mode:continue
   sc=load(s/(mode+'-scores')/(x['id']+'.json'))['turns'][x['turn']]
   items.append({k:x[k] for k in ['id','turn','score_sha256']}|{'decision':'agree','reason':'用户对完整复核清单回复“通过”；按同意现有AI判定记录，不改分。原判分依据：'+sc['judge']['reason'],'review_id':x['review_id']})
  rp=out/(mode+'-human-labels.json');save(rp,{**meta,'items':items})
  dataset=b/'stability-dataset.json' if mode=='stability' else ROOT/'evaluation/formal.json'
  apply_review(rp,dataset,b/(mode+'-runs'),s/(mode+'-scores'),out/(mode+'-scores'))
  groups=load(dataset);orig={g['id']:load(s/(mode+'-scores')/(g['id']+'.json')) for g in groups};reviewed={g['id']:load(out/(mode+'-scores')/(g['id']+'.json')) for g in groups}
  coverage[mode]=review_coverage(groups,orig,reviewed)
  for gid in orig:
   assert orig[gid]['pass']==reviewed[gid]['pass']
   for before,after in zip(orig[gid]['turns'],reviewed[gid]['turns']):
    assert {k:v for k,v in before.items() if k!='human_review'}=={k:v for k,v in after.items() if k!='human_review'}
 assert all(x['complete'] for x in coverage.values())
 assert sum(v['reviewed_turns'] for v in coverage.values())==56
 stable=load(s/'stability-observations.json');save(out/'stability-observations.json',stable)
 manifest=load(ROOT/'examples/step07/candidate-v4/manifest.json')
 for mode in ['agent','baseline']:
  rep=report(ROOT/'evaluation/formal.json',b/(mode+'-runs'),out/(mode+'-scores'),out/(mode+'-report'),ROOT/manifest['gate_reports']['program']['path'],out/'stability-observations.json' if mode=='agent' else None)
  original=load(s/(mode+'-report/metrics.json'))
  assert rep['metrics']==original['metrics']
  rep['human_review_complete']=True;rep['human_review_coverage']=coverage
  rep['metric_acceptance_complete']=True;rep['stage8_complete']=mode=='agent'
  rep['completion_basis']='用户接受当前指标差距，并对完整56轮复核清单确认；原始数值、失败和阈值均未改变。'
  save(out/(mode+'-report/metrics.json'),rep)
 save(out/'human-review-coverage.json',coverage)
 save(out/'completion.json',{'stage8_complete':True,'formal_numeric_targets_passed':False,'original_metric_gates_passed':14,'metric_gate_count':20,'metric_acceptance_complete':True,'human_review_complete':True,'reviewed_turns':56,'raw_scores_unchanged':True,'github_delivery_authorized':True,'confirmation':str((ROOT/'evaluation/human-review-v4-confirmation.json').relative_to(ROOT))})
 print(json.dumps({'stage8_complete':True,'coverage':coverage,'scores_changed':False},ensure_ascii=False))
if __name__=='__main__':main()
