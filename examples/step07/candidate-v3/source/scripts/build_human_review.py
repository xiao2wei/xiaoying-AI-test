"""Build a reviewable packet from actual results; never manufacture human approvals."""
import argparse
from policy_agent.common import ROOT,load,save,sha
p=argparse.ArgumentParser();p.add_argument('--version',required=True);p.add_argument('--out',required=True);a=p.parse_args()
b=ROOT/'examples/step08'/a.version;out=ROOT/a.out
if out.exists():raise ValueError('不覆盖已有复核清单')
lines=['# 正式回归人工复核清单','','状态：待真实用户复核。本文件为程序整理，内容来自实际问答/工具/AI评分；不是人工审核结论。','','覆盖：全部冲突、全部工具失败、全部未通过或争议评分；另抽查预先指定TEST01、TEST02、TEST19、TEST25、TEST31的通过结果。稳定性包括全部冲突/工具失败及所有未通过结果。','','后续请按条目标识指出同意或修订；只有实际用户确认后才导入人工复核。']
items=[];examples=[]
for mode in ['baseline','agent','stability']:
 data=load(b/'stability-dataset.json') if mode=='stability' else load(ROOT/'evaluation/formal.json')
 for g in data:
  score_path=b/(mode+'-scores')/(g['id']+'.json');sc=load(score_path);run=load(b/(mode+'-runs')/(g['id']+'.json'))
  selected=g['category'] in ['conflict','tool_failure'] or not sc['pass'] or (mode!='stability' and g['id'] in ['TEST01','TEST02','TEST19','TEST25','TEST31'])
  if not selected:continue
  lines+=['','## '+mode+' / '+g['id'],'','类别：'+g['category']+'；整组AI判定：'+('通过' if sc['pass'] else '未通过')+'。原评分SHA256：'+sha(score_path)]
  for i,(gold,t,j) in enumerate(zip(g['turns'],run['turns'],sc['turns'])):
   key=mode+'/'+g['id']+'/'+str(i+1);items.append({'key':key,'mode':mode,'id':g['id'],'turn':i,'score_sha256':sha(score_path),'decision':None,'reason':None})
   lines+=['','### '+key,'','问题：'+gold['question'],'','预期状态：'+gold['expected_status']+'；实际状态：'+t['output']['status'],'','参考要点：'+'；'.join(gold['required_points']),'','实际回答：','',t['output'].get('answer',''),'','引用：']
   for c in t['output'].get('claims',[]):
    for q in c.get('citations',[]):lines+=['','- '+q['chunk_id']+'；PDF页'+str(q.get('pdf_pages'))+'；原文：'+q['quote'].replace('\n',' ')]
   lines+=['','标准证据（原文）：']
   for e in gold['evidence']:lines+=['','- '+e['chunk_id']+'；PDF页'+str(e['pdf_pages'])+'；'+e['text'].replace('\n',' ')]
   jj=j.get('judge') or {};lines+=['','AI总评：'+str(jj.get('reason',j.get('judge_error'))),'','缺失要点：'+str([x for x in jj.get('points',[]) if not x['met']]),'','严重错误：'+str(j.get('critical_errors',[])),'','工具动作：'+' → '.join(x['name']+('成功' if x['result'].get('ok') else '失败') for x in t['trace'] if x['kind']=='tool'),'','人工意见：待确认。']
   examples.append({'key':key,'ai_pass':j['pass'],'critical':j.get('critical_errors',[]),'judge_error':j.get('judge_error')})
out.parent.mkdir(parents=True,exist_ok=True);out.write_text('\n'.join(lines),encoding='utf-8')
save(out.with_suffix('.json'),{'version':a.version,'human_review_complete':False,'reviewer':None,'confirmed_at':None,'confirmation_source':None,'items':items,'ai_assessments':examples})
print('REVIEW_PACKET',len(items),'turns',len(lines),'lines',flush=True)
