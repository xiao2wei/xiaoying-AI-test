"""Recompute reviewed metrics and require real review coverage; never auto-label answers."""
import argparse
from policy_agent.common import ROOT,load,save,sha
from policy_agent.metrics import report

def required_review(groups,original_scores):
 required=[]
 for g in groups:
  s=original_scores[g['id']]
  selected=g['category'] in ['conflict','tool_failure'] or not s['pass'] or g['id'] in ['TEST01','TEST02','TEST19','TEST25','TEST31']
  if selected:required.extend((g['id'],i) for i in range(len(g['turns'])))
 return required

def review_coverage(groups,original,reviewed):
 needed=required_review(groups,original);missing=[]
 for rid,i in needed:
  row=reviewed.get(rid,{}).get('turns',[])
  h=row[i].get('human_review') if i<len(row) else None
  if not h or any(not h.get(k) for k in ['reviewer','confirmed_at','confirmation_source','decision','reason','source_score_sha256']):missing.append([rid,i])
 return {'required_turns':len(needed),'reviewed_turns':len(needed)-len(missing),'missing':missing,'complete':not missing}

def finalize(version):
 b=ROOT/'examples/step08'/version;formal=ROOT/'evaluation/formal.json';stable_data=b/'stability-dataset.json';coverage={}
 for mode in ['baseline','agent','stability']:
  groups=load(stable_data if mode=='stability' else formal)
  original={g['id']:load(b/(mode+'-scores')/(g['id']+'.json')) for g in groups}
  reviewed={g['id']:load(b/(mode+'-reviewed')/(g['id']+'.json')) for g in groups}
  coverage[mode]=review_coverage(groups,original,reviewed)
 if not all(v['complete'] for v in coverage.values()):save(b/'human-review-coverage.json',coverage);raise ValueError('真实人工复核尚不完整')
 observations=[]
 for g in load(stable_data):
  s=load(b/'stability-reviewed'/(g['id']+'.json'))
  gaps=[bool(t.get('judge') and t['judge'].get('actionable_gap',{}).get('passed')) for gt,t in zip(g['turns'],s['turns']) if gt['expected_status'] in ['needs_confirmation','insufficient_evidence']]
  observations.append({'id':g['base_id'],'repeat':g['repeat'],'pass':s['pass'],'critical_errors':[e for t in s['turns'] for e in t.get('critical_errors',[])],'judge_errors':[t['judge_error'] for t in s['turns'] if t.get('judge_error')],'actionable_applicable':bool(gaps),'actionable_pass':all(gaps) if gaps else None})
 stable=b/'stability-reviewed-observations.json';save(stable,observations)
 candidate=load(ROOT/'examples/step07'/load(b/'protocol.json')['candidate']/'manifest.json')
 for rel,h in {**candidate['source_files'],**candidate['data_files']}.items():
  if sha(ROOT/rel)!=h:raise ValueError('冻结后源文件发生变化，需重新说明验证影响:'+rel)
 program=ROOT/candidate['gate_reports']['program']['path']
 reports={}
 for mode in ['baseline','agent']:
  out=b/(mode+'-reviewed-report');r=report(formal,b/(mode+'-runs'),b/(mode+'-reviewed'),out,program,stable if mode=='agent' else None)
  r['human_review_complete']=True;r['human_review_coverage']=coverage;r['stage8_complete']=mode=='agent' and r['formal_numeric_targets_passed'];save(out/'metrics.json',r);reports[mode]=r
 save(b/'human-review-coverage.json',coverage)
 save(b/'completion.json',{'stage8_complete':reports['agent']['stage8_complete'],'numeric_targets_passed':reports['agent']['formal_numeric_targets_passed'],'human_review_complete':True,'candidate_frozen_files_verified':True,'github_delivery_deferred':True})
 print('STEP8_COMPLETE' if reports['agent']['stage8_complete'] else 'NUMERIC_GATES_STILL_FAILED')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--version',required=True);a=p.parse_args();finalize(a.version)
