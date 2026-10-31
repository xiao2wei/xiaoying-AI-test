import json,time
from .common import ROOT
from .model import DeepSeek,ModelError
from .tools import ToolSession
from .validation import validate,failure,finish
PROMPT=(ROOT/'src/policy_agent/prompts/answer.txt').read_text(encoding='utf-8')
def baseline(question,retriever,history=None,fault=None,max_tools=10,max_rounds=12,model=None):
 start=time.perf_counter();trace=[];session=ToolSession(retriever,trace,fault,max_tools);model=model or DeepSeek()
 history=history or [];query=' '.join([h['content'] for h in history if h['role']=='user']+[question])
 search=session.execute('search',{'query':query});results=[]
 if search.get('ok'):
  for hit in search['hits']:results.append(session.execute('read',{'chunk_id':hit['chunk_id']}))
 messages=[{'role':'system','content':PROMPT}]+history+[{'role':'user','content':json.dumps({'question':question,'search_result':search,'read_results':results},ensure_ascii=False)}]
 try:
  raw=model.call(messages,trace,'baseline');errors=validate(raw,session.read)
  out=failure('validation_failed','引用或格式校验未通过：'+','.join(errors)) if errors else finish(raw)
 except ModelError as e:raw=None;errors=[];out=failure('model_error',str(e))
 return package(out,raw,errors,trace,session,start,question,history,'baseline')
def package(out,raw,errors,trace,session,start,question,history,mode):
 return {'mode':mode,'question':question,'history':history,'output':out,'raw_final':raw,'validation_errors':errors,'trace':trace,'read_ids':list(session.read),'first_hits':session.first_hits or [],'seconds':round(time.perf_counter()-start,4),'model_calls':sum(e['kind']=='model' for e in trace),'tool_calls':session.count,'real_model':any(e.get('real_api',False) for e in trace if e['kind']=='model'),'fault':session.fault}
