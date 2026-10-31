"""Render final stored real answers into Markdown. No model/API calls or score changes."""
from pathlib import Path
from decimal import Decimal,ROUND_HALF_UP
import json,hashlib
R=Path(__file__).resolve().parents[1]
B=R/'examples/step08/v4';S=B/'human-reviewed-r1'
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
pct=lambda v:'N/A' if v is None else f'{v*100:.2f}%'
def number(v):return str(Decimal(str(v)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP))
def quote(s):return '\n'.join('> '+line for line in s.split('\n'))
cat={'normal':'明确答案','conflict':'文档冲突','insufficient':'资料外或信息不足','paraphrase':'改写后的相似问题','context':'上下文追问','tool_failure':'工具失败'}
status={'answered':'已回答','needs_confirmation':'需要确认','insufficient_evidence':'资料不足','tool_error':'工具失败，未完成','limit_reached':'达到调用上限，未完成','model_error':'模型失败，未完成','validation_failed':'校验失败，未完成'}
metric_names=['首轮证据召回率 Recall@5','最终读取证据覆盖率','整体任务通过率','可回答问题正确率','回答完整度','引用支持率','事实结论引用覆盖率','无依据事实率','冲突处理通过率','资料不足处理通过率','工具失败处理通过率','相似问题通过率','上下文追问通过率','引用定位与执行边界等程序检查','关键缺陷场景数','关键场景稳定性','端到端耗时 P95','平均模型请求次数','平均工具调用次数','资料缺口说明可执行率']
metrics=load(S/'agent-report/metrics.json')['metrics'];baseline=load(S/'baseline-report/metrics.json')
formal=load(R/'evaluation/formal.json');stable=load(B/'stability-dataset.json')
source_hashes={};counts={};expected={'agent':(40,51),'baseline':(40,51),'stability':(30,36)}
for mode,title,filename,groups in [
 ('agent','最后一轮测试结果与真实问答','docs/LATEST-TEST-RESULTS.md',formal),
 ('baseline','最后一轮基础RAG：真实问题与实际回答','docs/reports/v4-baseline-qa.md',formal),
 ('stability','最后一轮稳定性：每次真实问题与实际回答','docs/reports/v4-stability-qa.md',stable)]:
 target=R/filename;target.parent.mkdir(parents=True,exist_ok=True);rel='../../' if mode!='agent' else '../'
 score_rows={g['id']:load(S/(mode+'-scores')/(g['id']+'.json')) for g in groups}
 passed=sum(v['pass'] for v in score_rows.values());nturn=sum(len(g['turns']) for g in groups)
 assert (len(groups),nturn)==expected[mode]
 lines=['# '+title,'','候选版本：candidate-v4。真实运行日期：2026-10-31；本次展示整理不重新提问模型，不修改答案或评分。','',f'**任务通过率：{pct(passed/len(groups))}。覆盖{len(groups)}组、{nturn}轮真实问答。**','', '以下“问题”和“实际回答”从保存的真实运行逐字提取，保留原有多轮顺序；相似问法组为独立提问，追问组承接前文。原文引用和工具动作可展开查看，不必打开JSON才能阅读答案。','', '“场景通过”按预设行为判定：资料不足时准确说明缺口、工具持续故障时如实返回未完成，也可以通过；不等于每组都应给出制度结论。表格中的百分比只改变展示形式，原始计数和精度保留。']
 if mode=='agent':
  lines+=['','## 本轮汇总','','|方案|通过率|覆盖范围|','|---|---:|---|','|Agent|90.00%|40组、51轮|','|基础RAG|85.00%|相同40组、51轮|','|Agent关键场景稳定性|90.00%|10组关键场景各运行3次，共36轮问答|','','Agent比基础RAG提高5个百分点。不是笔试得分；基础RAG的引用等个别指标优于Agent，完整对照见[指标报告](steps/08-v4-completed-results.md)。','', '本轮原定20项指标的达标比例为70.00%，用户接受当前差距并批量确认规定的56轮正式复核清单，原始失败不变。稳定性通过率达到90.00%，但原目标另要求关键缺陷为0，该约束未达标。','', '- [基础RAG全部真实问答](reports/v4-baseline-qa.md)','- [稳定性全部真实问答](reports/v4-stability-qa.md)','- [未通过案例的通俗解释](FAILED-CASES.md)','','### 六类验收结果','','|类别|通过率|测试组数|','|---|---:|---:|']
  for c,v in load(S/'agent-report/metrics.json')['category_summary'].items():lines.append('|'+cat[c]+'|'+pct(v['passed']/v['total'])+'|'+str(v['total'])+'|')
  lines+=['','### 全部20项指标','','|编号|指标|原目标|实测结果|原门槛判定|','|---|---|---|---|---|']
  for i,name in enumerate(metric_names,1):
   key=f'M{i:02}';m=metrics[key];d='≥' if m['direction']=='>=' else '≤'
   if i==15:actual=str(m['value'])+'个';goal='0个'
   elif i==17:actual=number(m['value'])+'秒';goal=d+str(m['target'])+'秒'
   elif i in [18,19]:actual=number(m['value'])+'次/组';goal=d+str(m['target'])+'次/组'
   else:actual=pct(m['value']);goal=d+pct(m['target'])
   if i==16:goal+='且关键缺陷为0'
   result='达标' if m['passed'] else '未达标，差距已获用户接受'
   lines.append('|'+key+'|'+name+'|'+goal+'|'+actual+'|'+result+'|')
  lines+=['','百分比保留两位小数，门槛判定使用原始精度。原始指标、人工确认和失败记录均保留；本报告不把用户接受差距改写成原门槛全部达标。']
 else:lines+=['','返回[总报告与Agent全部真实问答](../LATEST-TEST-RESULTS.md)。']
 lines+=['','## 问答目录','','|场景|类别|测试结果|轮数|','|---|---|---|---:|']
 for g in groups:lines.append('|['+g['id']+'](#'+g['id'].lower()+')|'+cat[g['category']]+'|'+('通过' if score_rows[g['id']]['pass'] else '未通过')+'|'+str(len(g['turns']))+'|')
 lines+=['','## 逐组真实问答']
 rendered_turns=0;rendered_failures=0
 for g in groups:
  rid=g['id'];rp=B/(mode+'-runs')/(rid+'.json');sp=S/(mode+'-scores')/(rid+'.json');run=load(rp);sc=score_rows[rid]
  source_hashes[rp.relative_to(R).as_posix()]=sha(rp);source_hashes[sp.relative_to(R).as_posix()]=sha(sp)
  assert len(run['turns'])==len(g['turns'])==len(sc['turns'])
  lines+=['','## '+rid,'','类别：'+cat[g['category']]+'；整组结果：**'+('通过' if sc['pass'] else '未通过')+'**。']
  if mode=='stability':lines+=['','原场景：'+g['base_id']+'；独立重复序号：'+str(g['repeat'])+'。']
  if g.get('mode')=='conversation':lines+=['','本组为连续对话，后续问题继承前面的问答。']
  elif len(g['turns'])>1:lines+=['','本组为独立的相似问法，不继承上一问历史。']
  if g.get('fault'):lines+=['','测试中按配置注入工具故障；模型回答仍来自真实DeepSeek，故障本身不等于场景失败。']
  for i,(gold,t,j) in enumerate(zip(g['turns'],run['turns'],sc['turns']),1):
   assert t['question']==gold['question'] and t['real_model']
   rendered_turns+=1;rendered_failures+=not j['pass']
   actual=t['output'];answer=actual.get('answer','');assert isinstance(answer,str) and answer
   lines+=['','### 第'+str(i)+'轮','','**问：**','',quote(t['question']),'','**实际回答：**','',quote(answer),'','任务状态：'+status.get(actual['status'],actual['status'])+'；本轮测试判定：**'+('通过' if j['pass'] else '未通过')+'**。','', '**评分说明：** '+j['judge']['reason']]
   if not j['pass']:
    misses=[p for p in j['judge']['points'] if not p['met']]
    badfacts=[f for f in j['judge']['facts'] if not all(f.get(k) for k in ['cited','citation_supported','supported_by_read'])]
    for p in misses:lines+=['','- 未满足的参考要点：'+gold['required_points'][p['index']]+'。评分理由：'+p['reason']]
    for f in badfacts:lines+=['','- 被标记的结论：“'+f['text']+'”。评分理由：'+f['reason']]
    if not misses and not badfacts:lines+=['','- 其他未通过依据：'+json.dumps(j.get('critical_errors',[]),ensure_ascii=False)]
   lines+=['','<details>','<summary>查看本轮引用原文、资料缺口与工具路径</summary>','']
   citations=[(c,q) for c in actual.get('claims',[]) for q in c.get('citations',[])]
   if citations:
    for c,q in citations:
     lines+=['','结论：'+c['text'],'','引用：'+q.get('doc_id',q['chunk_id'].split('-')[0])+' / '+q['chunk_id']+'；'+q.get('title','')+'；PDF页 '+', '.join(map(str,q.get('pdf_pages',[])))+'。','',quote(q['quote'])]
   else:lines+=['','本轮没有制度事实引用；是否合理取决于本题的资料和工具状态。']
   if actual.get('gaps'):
    lines+=['','资料缺口：','']+['- '+x for x in actual['gaps']]
   lines+=['','实际动作顺序：','']
   for z in t['trace']:
    if z['kind']=='decision':lines+=['- 模型选择 '+str(z.get('action'))+'：'+str(z.get('reason',''))]
    elif z['kind']=='tool':
     res=z['result'];obs='成功' if res.get('ok') else '失败：'+str(res.get('error',{}).get('code'))
     if z['name']=='search' and res.get('ok'):obs+='，候选 '+', '.join(x['chunk_id'] for x in res.get('hits',[]))
     if z['name']=='read' and res.get('ok'):obs+='，读取 '+res['chunk']['chunk_id']
     lines+=['- 工具 '+z['name']+'；参数 '+json.dumps(z.get('arguments',{}),ensure_ascii=False)+'；'+obs+'。']
   lines+=['','</details>']
  lines+=['','溯源：[完整原运行]('+rel+rp.relative_to(R).as_posix()+') · [原分与人工确认]('+rel+sp.relative_to(R).as_posix()+')。']
 assert rendered_turns==expected[mode][1]
 content='\n'.join(lines)+'\n';target.write_text(content,encoding='utf-8')
 counts[mode]={'groups':len(groups),'turns':rendered_turns,'failed_groups':sum(not x['pass'] for x in score_rows.values()),'failed_turns':rendered_failures,'output':filename,'sha256':sha(target)}
for p,h in source_hashes.items():assert sha(R/p)==h,p
manifest={'candidate':'candidate-v4','new_model_requests':0,'original_inputs_answers_scores_unchanged':True,'counts':counts,'source_sha256':source_hashes}
(R/'examples/submission/readable-report-audit.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'counts':counts,'original_files_unchanged':True,'new_model_requests':0},ensure_ascii=False))
