"""Recomputable metrics; no model calls or automatic removal of failed rows."""
import math,json,argparse
from pathlib import Path
from .common import ROOT,load,save

def mean(xs):return sum(xs)/len(xs) if xs else None
def coverage(units,ids):
 return sum(bool(set(u)&set(ids)) for u in units)/len(units) if units else None
def nearest_rank(values,q=.95):return sorted(values)[math.ceil(q*len(values))-1] if values else None
def ratio(name,n,d,target,lower=True,detail=None):
 value=n/d if d else None
 return {'name':name,'numerator':n,'denominator':d,'value':value,'target':target,'direction':'>=' if lower else '<=','passed':None if value is None else (value>=target if lower else value<=target),'detail':detail or {}}
def stability_valid(rows,ids):
 pairs=[(x.get('id'),x.get('repeat')) for x in rows]
 return len(rows)==len(ids)*3 and len(set(pairs))==len(pairs) and set(pairs)=={(i,r) for i in ids for r in [1,2,3]}
def aggregate(groups,runs,scores,program=None,stability=None,development=False):
 lookup={x['id']:x for x in runs};judges={x['id']:x for x in scores};detail={};facts=[];unresolved=[]
 recalls=[];reads=[];correct=[];complete=[];passed=[];critical=[];times=[];models=[];tools=[];categories={}
 provenance_n=0;provenance_d=0;gap_rows=[]
 for g in groups:
  rid=g['id'];r=lookup.get(rid,{});s=judges.get(rid,{})
  rs=r.get('turns',[]);ss=s.get('turns',[]);first=[];read=[];cor=[];comp=[];errs=[];gap_checks=[];is_pass=len(ss)==len(g['turns']) and bool(ss) and all(x['pass'] for x in ss)
  for i,t in enumerate(g['turns']):
   ar=rs[i] if i<len(rs) else {};sc=ss[i] if i<len(ss) else {};j=sc.get('judge')
   if t['search_evaluable']:first.append(coverage(t['evidence_units'],ar.get('first_hits',[])))
   if t['read_evaluable']:read.append(coverage(t['evidence_units'],ar.get('read_ids',[])))
   if not j:unresolved.append(rid+':'+str(i))
   if t.get('expected_status') in ['needs_confirmation','insufficient_evidence']:gap_checks.append(bool(j and j.get('actionable_gap',{}).get('passed')))
   if t['answerable']:
    cor.append(bool(j and j['answer_correct'] and ar.get('output',{}).get('status')=='answered' and not sc.get('critical_errors')))
    comp.append(sum(x['met'] for x in j['points'])/len(t['required_points']) if j else 0)
   if j:facts.extend([{**f,'group':rid,'turn':i} for f in j['facts']])
   errs.extend(sc.get('critical_errors',[]));provenance_d+=1;provenance_n+=bool(sc and not sc.get('program_errors') and ar)
  if gap_checks:gap_rows.append((rid,all(gap_checks)))
  if first:recalls.append((rid,mean(first)))
  if read:reads.append((rid,mean(read)))
  if cor:correct.append((rid,all(cor)));complete.append((rid,mean(comp)))
  if r.get('mode')=='agent' and r.get('tool_calls',0)>10:errs.append('group_tool_limit_exceeded')
  if r.get('unknown_call_counts'):unresolved.append(rid+':unknown_call_counts')
  if errs:critical.append({'id':rid,'errors':errs})
  passed.append((rid,is_pass));categories.setdefault(g['category'],[]).append((rid,is_pass))
  times.append((rid,r.get('seconds')));models.append((rid,r.get('model_calls',0)));tools.append((rid,r.get('tool_calls',0)))
  detail[rid]={'pass':is_pass,'first_recall':mean(first),'read_coverage':mean(read),'correct':all(cor) if cor else None,'completeness':mean(comp),'critical_errors':errs,'seconds':r.get('seconds'),'model_calls':r.get('model_calls'),'tool_calls':r.get('tool_calls')}
 def macro(name,rows,target):return ratio(name,sum(x[1] for x in rows),len(rows),target,detail=dict(rows))
 metrics={
 'M01':macro('初次检索Recall@5',recalls,.9),'M02':macro('最终实际读取证据覆盖率',reads,.95),
 'M03':macro('任务通过率',passed,1.0 if development else .9),'M04':macro('可回答问题正确率',correct,.9),'M05':macro('可回答问题完整度',complete,.95),
 'M06':ratio('引用支持率',sum(f['cited'] and f['citation_supported'] for f in facts),sum(f['cited'] for f in facts),1),
 'M07':ratio('事实引用覆盖率',sum(f['cited'] for f in facts),len(facts),1),
 'M08':ratio('无依据事实率',sum(not f['supported_by_read'] for f in facts),len(facts),0,False)}
 for mid,cat,target in [('M09','conflict',1),('M10','insufficient',1),('M11','tool_failure',1),('M12','paraphrase',5/6),('M13','context',4/5)]:metrics[mid]=macro(cat+'通过率',categories.get(cat,[]),target)
 pn=(program or {}).get('passed',0);pd=(program or {}).get('run',0)
 metrics['M14']=ratio('程序检查',pn+provenance_n,pd+provenance_d,1,detail={'test_passed':pn,'test_run':pd,'provenance_passed':provenance_n,'provenance_run':provenance_d,'test_report_present':bool(program)})
 if not program:metrics['M14']['passed']=False
 metrics['M15']={'name':'关键缺陷场景数','numerator':len(critical),'denominator':len(groups),'value':len(critical),'target':0,'direction':'<=','passed':not critical and not unresolved,'detail':critical}
 stable=stability or [];stable_ok=sum(x.get('pass',False) for x in stable)
 metrics['M16']=ratio('稳定性通过率',stable_ok,len(stable),.9,detail={'required_observations':30,'actual':len(stable)})
 if stable:
  metrics['M16']['passed']=stability_valid(stable,load(ROOT/'evaluation/manifest.json')['stability_ids']) and stable_ok>=27 and not any(x.get('critical_errors') or x.get('judge_errors') for x in stable)
  stable_critical=[{'id':x['id'],'repeat':x['repeat'],'errors':x['critical_errors']} for x in stable if x.get('critical_errors')]
  metrics['M15'].update(numerator=len(critical)+len(stable_critical),denominator=len(groups)+len(stable),value=len(critical)+len(stable_critical),passed=not critical and not stable_critical and not unresolved and not any(x.get('judge_errors') for x in stable),detail=critical+stable_critical)
  gap_rows.extend((f"{x['id']}-repeat{x['repeat']}",x['actionable_pass']) for x in stable if x.get('actionable_applicable'))
 valid_times=[v for _,v in times if v is not None];p95=nearest_rank(valid_times)
 metrics['M17']={'name':'端到端P95秒','numerator':p95,'denominator':len(groups),'value':p95,'target':120,'direction':'<=','passed':p95 is not None and len(valid_times)==len(groups) and p95<=120,'detail':dict(times)}
 metrics['M18']=ratio('平均模型请求次数',sum(x[1] for x in models),len(groups),8,False,dict(models))
 metrics['M19']=ratio('平均业务工具尝试次数',sum(x[1] for x in tools),len(groups),8,False,dict(tools))
 metrics['M20']=macro('资料缺口说明可执行率',gap_rows,1)
 recover=[g['id'] for g in groups if g['category']=='tool_failure' and g['turns'][0]['expected_status']=='answered'];stop=[g['id'] for g in groups if g['category']=='tool_failure' and g['id'] not in recover]
 return {'scope':'development' if development else 'formal','group_count':len(groups),'metrics':metrics,'per_group':detail,'atomic_facts':facts,'unresolved':unresolved,'critical':critical,
 'category_summary':{k:{'passed':sum(v for _,v in rows),'total':len(rows)} for k,rows in categories.items()},
 'failure_breakdown':{'recovery':{'passed':sum(detail[i]['pass'] for i in recover),'total':len(recover)},'safe_stop':{'passed':sum(detail[i]['pass'] for i in stop),'total':len(stop)}},
 'all_applicable_numeric_targets_passed':all(m['passed'] for mid,m in metrics.items() if mid!='M16' or stability is not None) and not unresolved,
 'formal_numeric_targets_passed':not development and len(groups)==40 and len(stable)==30 and all(m['passed'] for m in metrics.values()) and not unresolved,
 'human_review_complete':False,'note':'数值通过不等于阶段完成；人工校准、复核与冻结要求单独检查。N/A不代表通过。'}
def report(dataset,runs,scores,outdir,program_path=None,stability_path=None):
 groups=load(dataset);rd=Path(runs);sd=Path(scores);outdir=Path(outdir)
 result=aggregate(groups,[load(rd/(g['id']+'.json')) for g in groups if (rd/(g['id']+'.json')).exists()],[load(sd/(g['id']+'.json')) for g in groups if (sd/(g['id']+'.json')).exists()],load(program_path) if program_path else None,load(stability_path) if stability_path else None,all(g['id'].startswith('DEV') for g in groups))
 save(outdir/'metrics.json',result)
 lines=['# 实际评测报告','','范围：'+result['scope']+'；'+str(result['group_count'])+'组。人工复核状态单独记录。','','|指标|实际|分子/分母|目标|结果|','|---|---|---|---|---|']
 for mid,m in result['metrics'].items():lines.append('|'+mid+' '+m['name']+'|'+('N/A' if m['value'] is None else f"{m['value']:.4f}")+'|'+str(m['numerator'])+'/'+str(m['denominator'])+'|'+m['direction']+str(m['target'])+'|'+('N/A' if m['passed'] is None else ('通过' if m['passed'] else '未通过'))+'|')
 lines+=['','未决评分：'+str(result['unresolved']),'','## 逐组结果','','|ID|通过|初次召回|最终证据覆盖|完整度|','|---|---|---|---|---|']
 for rid,v in result['per_group'].items():lines.append('|'+rid+'|'+'|'.join(str(v[k]) for k in ['pass','first_recall','read_coverage','completeness'])+'|')
 (outdir/'report.md').write_text('\n'.join(lines),encoding='utf-8');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--dataset',required=True);p.add_argument('--runs',required=True);p.add_argument('--scores',required=True);p.add_argument('--out',required=True);p.add_argument('--program');p.add_argument('--stability');a=p.parse_args();r=report(a.dataset,a.runs,a.scores,a.out,a.program,a.stability);print(json.dumps({k:{'value':v['value'],'passed':v['passed']} for k,v in r['metrics'].items()},ensure_ascii=False))
