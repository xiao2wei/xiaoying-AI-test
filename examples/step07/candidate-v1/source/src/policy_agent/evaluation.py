import argparse,json,time,math,concurrent.futures
from pathlib import Path
from .common import ROOT,load,save,sha,env,now
from .model import DeepSeek,ModelError
from .validation import validate,normal
JUDGE_PROMPT=(ROOT/'src/policy_agent/prompts/judge.txt').read_text(encoding='utf-8')
def validate_fact_spans(j,out):
 texts=[c['text'] for c in out.get('claims',[])]+out.get('gaps',[])
 if out.get('claims') and not j['facts']:raise ValueError('非空事实回答被评为零事实')
 for f in j['facts']:
  span=f.get('answer_span')
  if not isinstance(span,str) or len(normal(span))<2 or not any(normal(span) in normal(t) for t in texts):raise ValueError('评分器把未出现在实际回答中的内容计作事实')
 for c in out.get('claims',[]):
  if not any(normal(f['answer_span']) in normal(c['text']) for f in j['facts']):raise ValueError('评分器漏评一整条实际claim')
def actual_read(result):
 return {e['result']['chunk']['chunk_id']:e['result']['chunk'] for e in result.get('trace',[]) if e['kind']=='tool' and e.get('name')=='read' and e['result'].get('ok')}
def judge_turn(gold,result,calibration=False):
 gold={**gold,'skip_gap_metric':calibration}
 read=actual_read(result);program_errors=validate(result['output'],read)
 model=DeepSeek(env().get('DEEPSEEK_JUDGE_MODEL','deepseek-v4-pro'),thinking='enabled');trace=[]
 payload={'evaluate_actionable_gap':not calibration and gold['expected_status'] in ['needs_confirmation','insufficient_evidence'],'question':gold['question'],'history':result.get('history',[]),'expected_status':gold['expected_status'],'required_points':gold['required_points'],'gold_evidence':gold['evidence'],'actual_answer':result['output'],'actually_read':list(read.values()),'program_errors':program_errors,
 'tool_actions':[{'name':e['name'],'arguments':e['arguments'],'ok':e['result'].get('ok'),'error':e['result'].get('error')} for e in result.get('trace',[]) if e['kind']=='tool']}
 try:
  j=model.call([{'role':'system','content':JUDGE_PROMPT},{'role':'user','content':json.dumps(payload,ensure_ascii=False)}],trace,'judge',max_tokens=10000)
  return checked_judgement(j,gold,result,trace)
 except (ModelError,ValueError,KeyError,TypeError) as e:
  return {'pass':False,'judge':None,'critical_errors':program_errors,'program_errors':program_errors,'judge_trace':trace,'judge_error':type(e).__name__+':'+str(e),'human_review':None}
def checked_judgement(j,gold,result,trace):
 program_errors=validate(result['output'],actual_read(result))
 if sorted(x['index'] for x in j['points'])!=list(range(len(gold['required_points']))):raise ValueError('评分要点不完整或重复')
 for x in j['points']:
  if type(x['met']) is not bool:raise ValueError('要点评分不是布尔值')
  if x['met']:
   span=x.get('answer_span','')
   answer_texts=[c['text'] for c in result['output'].get('claims',[])]+result['output'].get('gaps',[])
   if not span or normal(span) not in normal('\n'.join(answer_texts)):raise ValueError('通过的要点缺少实际答案定位')
 for f in ['status_ok','decision_ok','answer_correct']:
  if type(j.get(f)) is not bool:raise ValueError('缺少布尔评分字段')
 if not isinstance(j.get('facts'),list) or not isinstance(j.get('serious_errors'),list):raise ValueError('缺少事实/严重错误列表')
 for f in j['facts']:
  for k in ['cited','citation_supported','supported_by_read']:
   if type(f.get(k)) is not bool:raise ValueError('事实判定字段缺失')
 validate_fact_spans(j,result['output'])
 critical=list(j['serious_errors'])+program_errors
 if any(not f['supported_by_read'] or (f['cited'] and not f['citation_supported']) for f in j['facts']):critical.append('存在无依据结论或不支持引用')
 if result['output'].get('status')!=gold['expected_status']:j['status_ok']=False
 gap_applicable=not gold.get('skip_gap_metric',False) and gold.get('expected_status') in ['needs_confirmation','insufficient_evidence']
 if gap_applicable:
  ga=j.get('actionable_gap')
  if not isinstance(ga,dict) or type(ga.get('passed')) is not bool:raise ValueError('缺少可执行资料缺口评审')
  if ga['passed'] and not ga.get('requested_items'):raise ValueError('缺口通过但未指出具体所需信息')
 else:ga={'applicable':False,'passed':None,'requested_items':[]}
 j['actionable_gap']=ga
 passed=(not gap_applicable or ga['passed']) and all(x['met'] for x in j['points']) and j['status_ok'] and j['decision_ok'] and not critical and all(f['cited'] for f in j['facts'])
 return {'pass':bool(passed),'judge':j,'critical_errors':critical,'program_errors':program_errors,'judge_trace':trace,'judge_error':None,'human_review':None}

def score(dataset,runs,outdir,workers=2):
 groups=load(dataset);runs=Path(runs);outdir=Path(outdir)
 if outdir.exists() and list(outdir.glob('*.json')):raise ValueError('禁止覆盖既有评分结果，请使用新目录')
 outdir.mkdir(parents=True,exist_ok=True)
 save(outdir/'manifest.json',{'dataset_sha256':sha(dataset),'runs':str(runs),'judge_prompt_sha256':sha(ROOT/'src/policy_agent/prompts/judge.txt'),'judge_model':env().get('DEEPSEEK_JUDGE_MODEL','deepseek-v4-pro'),'created_at':now()})
 def one(g):
  p=runs/(g['id']+'.json')
  r=load(p) if p.exists() else {'turns':[],'error':'missing_run'};scores=[]
  for i,t in enumerate(g['turns']):
   if i>=len(r.get('turns',[])):scores.append({'pass':False,'judge':None,'judge_error':'missing_turn','critical_errors':[],'program_errors':['missing_turn'],'judge_trace':[],'human_review':None})
   else:scores.append(judge_turn(t,r['turns'][i]))
  item={'id':g['id'],'category':g['category'],'turns':scores,'pass':all(t['pass'] for t in scores),'run_sha256':sha(p) if p.exists() else None}
  save(outdir/(g['id']+'.json'),item);print(g['id'],item['pass'],flush=True);return item
 with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:items=list(pool.map(one,groups))
 save(outdir/'score-summary.json',{'groups':len(items),'passed':sum(x['pass'] for x in items),'unresolved_judges':sum(bool(t['judge_error']) for x in items for t in x['turns'])})
 return items
def calibrate(outdir,workers=2):
 data=load(ROOT/'evaluation/calibration.json');corpus={c['chunk_id']:c for c in load(ROOT/'data/processed/chunks.json')};outdir=Path(outdir)
 if outdir.exists() and list(outdir.glob('*.json')):raise ValueError('校准输出目录已存在')
 outdir.mkdir(parents=True,exist_ok=True)
 def one(x):
  result={'output':x['answer'],'history':[],'trace':[{'kind':'tool','name':'read','arguments':{'chunk_id':cid},'result':{'ok':True,'chunk':corpus[cid]}} for cid in x['read_ids']]}
  if not x['read_ids']:result['trace'].append({'kind':'tool','name':'search','arguments':{'query':x['question']},'result':{'ok':False,'error':{'code':'PERSISTENT_UNAVAILABLE'}} if x['id']=='CAL11' else {'ok':True,'hits':[]}})
  gold={'question':x['question'],'expected_status':x['expected'],'required_points':x['points'],'evidence':x['evidence']}
  j=judge_turn(gold,result,True);j.update(id=x['id'],fixture_type=x['fixture_type'],proposed_pass=x['proposed_pass'],human_label=x['human_label'],agreement_with_proposed=(j['pass']==x['proposed_pass']),agreement_with_human=None if x['human_label'] is None else j['pass']==x['human_label'])
  save(outdir/(x['id']+'.json'),j);print(x['id'],j['pass'],j['judge_error'],flush=True);return j
 with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:rows=list(pool.map(one,data))
 labels_complete=all(x['human_label'] is not None for x in rows)
 summary={'samples':len(rows),'agreement_with_proposed':sum(x['agreement_with_proposed'] for x in rows),'human_labels_complete':labels_complete,'human_agreement':sum(bool(x['agreement_with_human']) for x in rows) if labels_complete else None,'serious_false_passes':sum(x['pass'] and not x['proposed_pass'] for x in rows),'calibration_gate_passed':labels_complete and sum(bool(x['agreement_with_human']) for x in rows)>=math.ceil(.9*len(rows)) and not any(x['pass'] and x['human_label'] is False for x in rows),'note':'建议标签一致率不是人工标签一致率；本夹具不算Agent性能'}
 save(outdir/'summary.json',summary);return summary

def main():
 p=argparse.ArgumentParser();s=p.add_subparsers(dest='command',required=True)
 c=s.add_parser('calibrate');c.add_argument('--out',required=True)
 q=s.add_parser('score');q.add_argument('--dataset',default=str(ROOT/'evaluation/dev.json'));q.add_argument('--runs',required=True);q.add_argument('--out',required=True);q.add_argument('--workers',type=int,default=2)
 a=p.parse_args()
 if a.command=='calibrate':print(json.dumps(calibrate(a.out),ensure_ascii=False))
 else:
  score(a.dataset,a.runs,a.out,a.workers)
  from .metrics import report
  program=ROOT/'examples/step06/program-tests.json'
  report(a.dataset,a.runs,a.out,Path(a.out)/'report',program if program.exists() else None)
if __name__=='__main__':main()
