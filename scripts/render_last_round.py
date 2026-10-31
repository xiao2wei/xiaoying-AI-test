"""Render stored real answers and separate content assessments; no model/API calls."""
from pathlib import Path
from decimal import Decimal,ROUND_HALF_UP
import json,hashlib
R=Path(__file__).resolve().parents[1]
B=R/'examples/step08/v4';S=B/'human-reviewed-r1';C=B/'content-policy-v1'
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
pct=lambda v:'N/A' if v is None else f'{v*100:.2f}%'
def number(v):return str(Decimal(str(v)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP))
def quote(s):return '\n'.join('> '+line for line in s.split('\n'))
cat={'normal':'明确答案','conflict':'文档冲突','insufficient':'资料外或信息不足','paraphrase':'改写后的相似问题','context':'上下文追问','tool_failure':'工具失败'}
status={'answered':'已回答','needs_confirmation':'需要确认','insufficient_evidence':'资料不足','tool_error':'工具失败，业务未完成','limit_reached':'达到调用上限，业务未完成','model_error':'模型失败，未完成','validation_failed':'校验失败，未完成'}
labels={'correct':'正确处理','correct_with_citation_note':'回答正确，但依据未给全','correct_handling':'正确处理（按预期停止，业务未完成）','incorrect':'回答错误（失败）','incomplete':'未完成（不记回答错误）','unverified':'待核查'}
def turn_label(row):
 if row['outcome']!='correct':return labels[row['outcome']]
 return {'answered':'回答正确','needs_confirmation':'正确说明冲突或需要确认的事项','insufficient_evidence':'正确说明资料不足'}.get(row['actual_status'],'正确处理')
metric_names=['首轮证据召回率 Recall@5','最终读取证据覆盖率','整体任务通过率','可回答问题正确率','回答完整度','引用支持率','事实结论引用覆盖率','无依据事实率','冲突处理通过率','资料不足处理通过率','工具失败处理通过率','相似问题通过率','上下文追问通过率','引用定位与执行边界等程序检查','关键缺陷场景数','关键场景稳定性','端到端耗时 P95','平均模型请求次数','平均工具调用次数','资料缺口说明可执行率']
metrics=load(S/'agent-report/metrics.json')['metrics'];summary=load(C/'summary.json')
formal=load(R/'evaluation/formal.json');stable=load(B/'stability-dataset.json')
source_hashes={};counts={};expected={'agent':(40,51),'baseline':(40,51),'stability':(30,36)}
for p in [C/'summary.json',R/'evaluation/content-policy-v1.json',R/'evaluation/content-review-v1.json']:
 source_hashes[p.relative_to(R).as_posix()]=sha(p)
for mode,title,filename,groups in [
 ('agent','最后一轮测试结果与真实问答','docs/LATEST-TEST-RESULTS.md',formal),
 ('baseline','最后一轮基础RAG：真实问题与实际回答','docs/reports/v4-baseline-qa.md',formal),
 ('stability','最后一轮稳定性：每次真实问题与实际回答','docs/reports/v4-stability-qa.md',stable)]:
 target=R/filename;target.parent.mkdir(parents=True,exist_ok=True);rel='../../' if mode!='agent' else '../';docrel='../' if mode!='agent' else ''
 score_rows={g['id']:load(S/(mode+'-scores')/(g['id']+'.json')) for g in groups}
 ap=C/(mode+'-assessments.json');assessed={g['id']:g for g in load(ap)};source_hashes[ap.relative_to(R).as_posix()]=sha(ap)
 sm=summary['modes'][mode];nturn=sum(len(g['turns']) for g in groups)
 assert (len(groups),nturn)==expected[mode]
 lines=['# '+title,'','候选版本：candidate-v4。真实运行日期：2026-10-31；本报告按用户后续授权的“内容正确优先”规则重分类。没有重新调用模型，没有改写原始问题、答案、Trace或旧评分。','',f'**正确处理率：{pct(sm["correct_handling_rate"])}；回答错误{sm["incorrect_answer_groups"]}组；未达到预期处理要求{sm["incomplete_groups"]}组。覆盖{len(groups)}组、{nturn}轮真实问答。**','', '“正确处理率”包括正确回答、合理说明资料不足/请求确认，以及按测试预期如实停止；不表示每组都产出了制度答案。工具故障后未达到场景要求的情况单列“未完成”，不称为答错，也不算正确完成。','', '回答与PDF一致但未给全依据，判为正确并注明；真正没有PDF支持的事实不能因此自动判对。规则、核对依据和旧口径对照见[评分口径说明]('+docrel+'CONTENT-POLICY.md)。','', '以下“问”和“实际回答”逐字来自真实运行；多轮顺序保持不变。补充核对证据只用于解释本次判断，不伪装成模型当时读过或引过的资料。']
 if mode=='agent':
  lines+=['','## 本轮汇总','','|方案|新口径正确处理率|回答错误|未达到预期处理要求|旧严格通过率|','|---|---:|---:|---:|---:|']
  for key,name in [('agent','Agent'),('baseline','基础RAG'),('stability','Agent关键场景稳定性')]:
   ms=summary['modes'][key];lines.append('|'+name+'|'+pct(ms['correct_handling_rate'])+'|'+str(ms['incorrect_answer_groups'])+'组|'+str(ms['incomplete_groups'])+'组|'+pct(ms['legacy_strict_pass_rate'])+'|')
  lines+=['','这是同一批已曝光测试记录按新口径的事后统计，不是新增独立测试或模型能力提升。Agent与基础RAG采用相同口径；基础RAG的3组未完成全部来自测试显式注入的工具故障，不是DeepSeek、VPN或SSL异常；原配置重跑仍会触发。Agent有2轮、稳定性有2轮保留“依据未给全”提示。','', '- [基础RAG全部真实问答](reports/v4-baseline-qa.md)','- [稳定性全部真实问答](reports/v4-stability-qa.md)','- [原未通过案例的重新分类与原因](FAILED-CASES.md)','','### 六类验收结果（新口径）','','|类别|正确处理率|测试组数|','|---|---:|---:|']
  for c,v in sm['category_summary'].items():lines.append('|'+cat[c]+'|'+pct(v['correct_handling_rate'])+'|'+str(v['groups'])+'|')
  lines+=['','<details>','<summary>查看旧口径20项指标：历史质量诊断，不能与新主判定混用</summary>','','旧口径同时要求内容、参考要点和引用绑定等逐项合格。原结果及14项达标的记录保留，用户已接受差距；新口径不把旧数值自动改成达标。旧“无依据”指当次读取/引用对结论的支持，不等于整份PDF没有相关条文。','','|编号|指标|原目标|旧口径实测结果|原门槛判定|','|---|---|---|---|---|']
  for i,name in enumerate(metric_names,1):
   key=f'M{i:02}';m=metrics[key];d='≥' if m['direction']=='>=' else '≤'
   if i==15:actual=str(m['value'])+'个';goal='0个'
   elif i==17:actual=number(m['value'])+'秒';goal=d+str(m['target'])+'秒'
   elif i in [18,19]:actual=number(m['value'])+'次/组';goal=d+str(m['target'])+'次/组'
   else:actual=pct(m['value']);goal=d+pct(m['target'])
   if i==16:goal+='且关键缺陷为0'
   lines.append('|'+key+'|'+name+'|'+goal+'|'+actual+'|'+('原门槛达标' if m['passed'] else '原门槛未达标')+'|')
  lines+=['','原始记录见[旧口径完整结果](steps/08-v4-completed-results.md)。该表中的关键缺陷标记保留原裁判含义，不是本次内容核对后发现的错误答案数。','','</details>']
 else:lines+=['','返回[总报告与Agent全部真实问答](../LATEST-TEST-RESULTS.md)。']
 lines+=['','## 问答目录','','|场景|类别|新口径结果|轮数|','|---|---|---|---:|']
 for g in groups:lines.append('|['+g['id']+'](#'+g['id'].lower()+')|'+cat[g['category']]+'|'+labels[assessed[g['id']]['outcome']]+'|'+str(len(g['turns']))+'|')
 lines+=['','## 逐组真实问答'];rendered_turns=0
 for g in groups:
  rid=g['id'];rp=B/(mode+'-runs')/(rid+'.json');sp=S/(mode+'-scores')/(rid+'.json');run=load(rp);sc=score_rows[rid];ac=assessed[rid]
  source_hashes[rp.relative_to(R).as_posix()]=sha(rp);source_hashes[sp.relative_to(R).as_posix()]=sha(sp)
  assert len(run['turns'])==len(g['turns'])==len(sc['turns'])==len(ac['turns'])
  lines+=['','## '+rid,'','类别：'+cat[g['category']]+'；整组结果：**'+labels[ac['outcome']]+'**。']
  if mode=='stability':lines+=['','原场景：'+g['base_id']+'；独立重复序号：'+str(g['repeat'])+'。']
  if g.get('mode')=='conversation':lines+=['','本组为连续对话，后续问题继承前面的问答。']
  elif len(g['turns'])>1:lines+=['','本组为独立的相似问法，不继承上一问历史。']
  if g.get('fault'):lines+=['','测试按配置注入工具故障；模型回答仍来自真实DeepSeek，故障本身不等于回答错误。']
  for i,(gold,t,j,a) in enumerate(zip(g['turns'],run['turns'],sc['turns'],ac['turns']),1):
   assert t['question']==gold['question']==a['question'] and t['real_model'];rendered_turns+=1
   actual=t['output'];answer=actual.get('answer','');assert isinstance(answer,str) and answer
   lines+=['','### 第'+str(i)+'轮','','**问：**','',quote(t['question']),'','**实际回答：**','',quote(answer),'','任务状态：'+status.get(actual['status'],actual['status'])+'；新口径判定：**'+turn_label(a)+'**。','','**判定说明：** '+a['reason']]
   if a['citation_issue']:lines+=['','**依据展示说明：回答内容符合PDF规定，但原回答未完整给出或关联支撑依据。该问题单独记录，不判回答失败。**']
   if a['review_evidence']:
    lines+=['','本次内容核对位置：'+ '；'.join(e['chunk_id']+'（PDF第'+', '.join(map(str,e['pdf_pages']))+'页）' for e in a['review_evidence'])+'。完整核对原文见下方展开内容。']
   lines+=['','<details>','<summary>查看原始引用、资料缺口、工具路径与评分溯源</summary>','']
   citations=[(c,q) for c in actual.get('claims',[]) for q in c.get('citations',[])]
   if citations:
    for c,q in citations:lines+=['','模型原始结论：'+c['text'],'','模型原始引用：'+q.get('doc_id',q['chunk_id'].split('-')[0])+' / '+q['chunk_id']+'；'+q.get('title','')+'；PDF页 '+', '.join(map(str,q.get('pdf_pages',[])))+'。','',quote(q['quote'])]
   else:lines+=['','本轮没有制度事实引用；是否合理取决于本题资料和工具状态。']
   if actual.get('gaps'):lines+=['','原始资料缺口：','']+['- '+x for x in actual['gaps']]
   lines+=['','实际动作顺序：','']
   for z in t['trace']:
    if z['kind']=='decision':lines+=['- 模型选择 '+str(z.get('action'))+'：'+str(z.get('reason',''))]
    elif z['kind']=='tool':
     res=z['result'];obs='成功' if res.get('ok') else '失败：'+str(res.get('error',{}).get('code'))
     if z['name']=='search' and res.get('ok'):obs+='，候选 '+', '.join(x['chunk_id'] for x in res.get('hits',[]))
     if z['name']=='read' and res.get('ok'):obs+='，读取 '+res['chunk']['chunk_id']
     lines+=['- 工具 '+z['name']+'；参数 '+json.dumps(z.get('arguments',{}),ensure_ascii=False)+'；'+obs+'。']
   lines+=['','旧严格判定（历史保留，不作当前主结果）：'+('通过' if j['pass'] else '未通过')+'。'+j['judge']['reason']]
   if not j['pass']:
    for p in j['judge']['points']:
     if not p['met']:lines+=['','- 旧扣分要点：'+gold['required_points'][p['index']]+'。原评分理由：'+p['reason']]
    for f in j['judge']['facts']:
     if not all(f.get(k) for k in ['cited','citation_supported','supported_by_read']):lines+=['','- 旧引用标记：“'+f['text']+'”。原评分理由：'+f['reason']]
   if a['review_evidence']:
    lines+=['','**本次Codex内容核对依据（AI复核，不是新增人工标签）：** 以下资料用于评测解释；不得将补查内容写回原始模型答案或Trace。']
    for e in a['review_evidence']:
     note='原运行确实读取过该片段；此处为复核列示' if e['originally_read'] else '**原运行未读取该片段，本次评测补查；不是模型原始引用**'
     lines+=['',e['chunk_id']+'；PDF第'+', '.join(map(str,e['pdf_pages']))+'页；'+note+'。','',quote(e['text'])]
   lines+=['','</details>']
  lines+=['','溯源：[完整原运行]('+rel+rp.relative_to(R).as_posix()+') · [旧评分与原人工确认]('+rel+sp.relative_to(R).as_posix()+') · [独立的新口径判断]('+rel+ap.relative_to(R).as_posix()+')。']
 assert rendered_turns==expected[mode][1]
 target.write_text('\n'.join(lines)+'\n',encoding='utf-8')
 counts[mode]={'groups':len(groups),'turns':rendered_turns,'correct_handling_rate':sm['correct_handling_rate'],'incorrect_groups':sm['incorrect_answer_groups'],'incomplete_groups':sm['incomplete_groups'],'legacy_failed_groups':sum(not x['pass'] for x in score_rows.values()),'output':filename,'sha256':sha(target)}
for p,h in source_hashes.items():assert sha(R/p)==h,p
manifest={'candidate':'candidate-v4','policy_version':summary['policy_version'],'new_model_requests':0,'original_inputs_answers_scores_unchanged':True,'counts':counts,'source_sha256':source_hashes}
(R/'examples/submission/readable-report-audit.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'counts':counts,'original_files_unchanged':True,'new_model_requests':0},ensure_ascii=False))
