import json,time
from .common import ROOT
from .model import DeepSeek,ModelError
from .tools import ToolSession
from .validation import validate,failure,finish
from .runtime import package,PROMPT
AGENT_PROMPT=(ROOT/'src/policy_agent/prompts/agent.txt').read_text(encoding='utf-8')
def view(result):
 if not result.get('ok') or 'chunk' not in result:return result
 return {'ok':True,'chunk':result['chunk'],'tables':[{'table_id':t['table_id'],'rows':t['rows']} for t in result.get('tables',[])]}
def agent(question,retriever,history=None,fault=None,max_tools=10,max_rounds=12,model=None,review_model=None):
 review_model=review_model or model or DeepSeek(thinking='enabled')
 start=time.perf_counter();trace=[];session=ToolSession(retriever,trace,fault,max_tools);model=model or DeepSeek();history=history or []
 messages=[{'role':'system','content':PROMPT.replace('输出JSON对象：','finish.result的对象规范：').replace('不要输出其他字段。','result内不要输出其他字段。')+'\n'+AGENT_PROMPT}]+history+[{'role':'user','content':question}]
 raw=None;errors=[];out=None;reviewed=False;review_next=False
 for step in range(max_rounds):
  messages.append({'role':'user','content':json.dumps({'runtime':{'round':step+1,'remaining_decision_rounds':max_rounds-step,'remaining_tool_attempts':max_tools-session.count,'read_ids':list(session.read)}},ensure_ascii=False)})
  try:
   active_model=review_model if review_next else model
   decision=active_model.call(messages,trace,'agent_review' if review_next else 'agent',max_tokens=6000 if review_next else 2600)
   review_next=False
  except ModelError as e:out=failure('model_error',str(e));break
  trace.append({'kind':'decision','step':step+1,'action':decision.get('action'),'arguments':decision.get('arguments',{}),'reason':str(decision.get('reason',''))[:200]})
  messages.append({'role':'assistant','content':json.dumps(decision,ensure_ascii=False)})
  action=decision.get('action');args=decision.get('arguments',{})
  if action=='finish':
   raw=decision.get('result',{});errors=validate(raw,session.read) if isinstance(raw,dict) else ['invalid_result']
   if not errors:
    if not reviewed and raw.get('status') in ['answered','needs_confirmation','insufficient_evidence']:
     reviewed=True;review_next=True
     messages.append({'role':'user','content':'最终核对：仅围绕本题全部子问与直接适用条款，检查关键条件、数字、并列要求、例外及引用支持。通用制度问题已有依据时直接answered，gaps为空，不为假想个人审批另索身份/协议；真正的个人资格或待遇问题缺必要条件时才追问。每条claim的全部事实必须在自己的引用中可核对，必要时补充同一已读原文的前提引用；无关事实删去。资料缺口与不能作唯一判断的说明放gaps，不作为独立制度claim，gaps也不要重述制度事实。冲突需明确衔接依据方可裁决；否则查解释部门并具体请求其衔接文件。不猜测条文未写出的排除关系。存在缺漏则修改或继续查证，无问题则完整finish；只能选择一个当前动作。'})
     continue
    out=finish(raw);break
   messages.append({'role':'user','content':json.dumps({'validation_error':errors,'instruction':'必须输出完整finish动作，包括result对象，其内必须有status、claims数组、gaps数组。修正引用或明确无法完成。','example':{'action':'finish','result':{'status':'insufficient_evidence','claims':[],'gaps':['说明实际缺口']},'reason':'简要终止原因'}},ensure_ascii=False)});continue
  if action not in ['search','read'] or not isinstance(args,dict):
   messages.append({'role':'user','content':'INVALID_ACTION：动作必须是search/read/finish。最终回答必须放在 {action:finish,result:{status:...,claims:[],gaps:[]},reason:...} 中，不能只给status。'});continue
  if action=='read':
   ids=args.get('chunk_ids')
   if not isinstance(ids,list) or not 1<=len(ids)<=5 or any(not isinstance(cid,str) for cid in ids):
    # A malformed invocation is still one counted business-tool attempt.
    obs=[session.execute('read',{'chunk_id':None})]
   else:
    obs=[]
    for cid in ids:
     if session.count>=max_tools:out=failure('limit_reached','达到工具调用上限，任务未完成');break
     obs.append(session.execute('read',{'chunk_id':cid}))
  else:
   if session.count>=max_tools:out=failure('limit_reached','达到工具调用上限，任务未完成');break
   obs=[session.execute('search',args)]
  if out:break
  if session.count>=max_tools and not any(x.get('ok') for x in obs):
   out=failure('limit_reached','达到工具调用上限，最后一次工具尝试失败，任务未完成；已成功读取的资料已保留。');break
  messages.append({'role':'user','content':json.dumps({'tool_observations':[view(x) for x in obs]},ensure_ascii=False)})
 if out is None:out=failure('limit_reached','达到模型决策轮数上限，任务未完成')
 return package(out,raw,errors,trace,session,start,question,history,'agent')
