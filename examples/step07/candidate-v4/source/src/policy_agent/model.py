import json, time, hashlib, threading
import requests
from .common import ROOT, env, now
from .json_format import decode_object
from .cost import estimated_peak_usd
from .action_schema import ACTION_TOOLS
LOCK=threading.Lock()
SERVICE_FAILURES={}
class ModelError(RuntimeError):pass
class DeepSeek:
 def __init__(self,model=None,thinking="disabled",reasoning_effort="high"):
  self.thinking=thinking;self.reasoning_effort=reasoning_effort
  e=env();self.key=e.get('DEEPSEEK_API_KEY');self.base=e.get('DEEPSEEK_BASE_URL','https://api.deepseek.com').rstrip('/');self.model=model or e.get('DEEPSEEK_MODEL','deepseek-flash')
  if not self.key:raise ModelError('缺少DEEPSEEK_API_KEY；本程序不回退Mock')
  self.budget=float(e.get('DEEPSEEK_BUDGET_USD','10'));self.ledger=ROOT/'examples/model-usage.jsonl';self.ledger.parent.mkdir(parents=True,exist_ok=True)
 def call(self,messages,trace,purpose='answer',max_tokens=2600):
  credential_id=hashlib.sha256((self.base+self.key).encode()).hexdigest()
  with LOCK:
   if credential_id in SERVICE_FAILURES:
    trace.append({'kind':'service_block','request_sent':False,'error':SERVICE_FAILURES[credential_id]})
    raise ModelError('模型服务暂不可用：'+SERVICE_FAILURES[credential_id]+'；请处理账户问题后重启运行')
   spent=sum(estimated_peak_usd(json.loads(x)) for x in self.ledger.read_text(encoding='utf-8').splitlines()) if self.ledger.exists() else 0
  if spent>=self.budget:raise ModelError('达到配置的模型费用预算，未调用模型')
  messages=list(messages);strict_retry=False
  payload={'model':self.model,'messages':messages,'thinking':{'type':self.thinking},'temperature':0,'max_tokens':max_tokens,'stream':False,'response_format':{'type':'json_object'}}
  if self.thinking=='enabled':payload['reasoning_effort']=self.reasoning_effort
  for attempt in range(2):
   start=time.perf_counter();entry={'kind':'model','purpose':purpose,'model':self.model,'time':now(),'attempt':attempt+1,'prompt_sha256':hashlib.sha256(json.dumps(messages,ensure_ascii=False).encode()).hexdigest(),'real_api':True,'thinking':self.thinking,'reasoning_effort':self.reasoning_effort if self.thinking=='enabled' else None,'read_timeout_seconds':180 if purpose=='judge' else 40}
   try:
    request_payload=dict(payload);request_base=self.base
    if strict_retry:
     request_base=self.base if self.base.endswith('/beta') else self.base+'/beta'
     request_payload.pop('response_format',None);request_payload['thinking']={'type':'disabled'};request_payload.pop('reasoning_effort',None);request_payload['tools']=ACTION_TOOLS;request_payload['tool_choice']='required'
     entry['response_transport']='strict_action_tool' if attempt==0 else 'strict_action_tool_retry'
     entry['thinking']='disabled';entry['reasoning_effort']=None
    else:entry['response_transport']='json_object'
    r=requests.post(request_base+'/chat/completions',headers={'Authorization':'Bearer '+self.key,'Content-Type':'application/json'},json=request_payload,timeout=(8,180 if purpose=='judge' else 40))
    entry['http_status']=r.status_code
    if r.status_code!=200:
     try:
      server_error=r.json().get('error',{});entry['server_error']={k:str(server_error[k]).replace(self.key,'[REDACTED]')[:400] for k in ['type','code','message'] if k in server_error}
     except (ValueError,AttributeError):pass
     entry['error']='HTTP_'+str(r.status_code)
     if r.status_code in [401,402]:
      with LOCK:SERVICE_FAILURES[credential_id]=entry['error']
     raise ModelError(entry['error'])
    d=r.json();m=d['choices'][0]['message'];content=m.get('content') or ''
    entry.update(response_id=d.get('id'),response_model=d.get('model'),usage=d.get('usage',{}),content=content,finish_reason=d['choices'][0].get('finish_reason'))
    entry['estimated_usd_upper_bound']=estimated_peak_usd(entry)
    entry['cost_estimate_method']='published_time_band_with_cache_hits_holidays_conservative_20261031'
    if entry['finish_reason']=='length':entry['error']='OUTPUT_TOKEN_LIMIT_REACHED';raise ModelError(entry['error'])
    if strict_retry:
     calls=m.get('tool_calls',[]);entry['structured_tool_calls']=calls
     if len(calls)!=1 or calls[0].get('function',{}).get('name') not in ['search','read','finish']:raise ValueError('严格格式未返回唯一动作')
     fn=calls[0]['function'];args,repairs=decode_object(fn['arguments']);reason=args.pop('reason','')
     result={'action':fn['name'],'reason':reason}
     if fn['name']=='finish':result['result']=args.get('result')
     else:result['arguments']=args
     if repairs:entry['native_argument_repairs']=repairs
     if attempt>0:entry['format_repairs']=['strict_action_tool_retry']
    else:
     result,repairs=decode_object(content)
     if repairs:entry['format_repairs']=repairs
    return result
   except (requests.RequestException,ValueError,KeyError,ModelError) as ex:
    entry['error']=entry.get('error',type(ex).__name__)
    if isinstance(ex,ValueError) and entry.get('content') and attempt==0:
     messages.extend([{'role':'assistant','content':entry['content']},{'role':'user','content':'上一次输出格式校验失败。请只输出一个完整JSON对象。若是动作决策，只选择当前一个动作，等待实际工具结果后再决定后续动作，不得输出多个JSON对象或预演工具执行。'}])
    if purpose in ['agent','agent_review'] and attempt==0 and (isinstance(ex,ValueError) or entry.get('finish_reason')=='length'):strict_retry=True
    if attempt==1 or (entry.get('finish_reason')=='length' and not strict_retry) or entry.get('http_status') in [400,401,402,403]:raise ModelError(entry['error']) from None
    if entry.get('http_status')==429:
     try:delay=min(15,max(1,float(r.headers.get('Retry-After','3'))))
     except ValueError:delay=3
     entry['retry_delay_seconds']=delay;time.sleep(delay)
   finally:
    entry['seconds']=round(time.perf_counter()-start,4);trace.append(entry)
    with LOCK:
     with self.ledger.open('a',encoding='utf-8') as f:f.write(json.dumps(entry,ensure_ascii=False)+'\n')
