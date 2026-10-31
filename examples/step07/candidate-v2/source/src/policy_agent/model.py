import json, time, hashlib, threading
import requests
from .common import ROOT, env, now
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
   spent=sum(json.loads(x).get('estimated_usd_upper_bound',0) for x in self.ledger.read_text(encoding='utf-8').splitlines()) if self.ledger.exists() else 0
  if spent>=self.budget:raise ModelError('达到配置的模型费用预算，未调用模型')
  messages=list(messages)
  payload={'model':self.model,'messages':messages,'thinking':{'type':self.thinking},'temperature':0,'max_tokens':max_tokens,'stream':False,'response_format':{'type':'json_object'}}
  if self.thinking=='enabled':payload['reasoning_effort']=self.reasoning_effort
  for attempt in range(2):
   start=time.perf_counter();entry={'kind':'model','purpose':purpose,'model':self.model,'time':now(),'attempt':attempt+1,'prompt_sha256':hashlib.sha256(json.dumps(messages,ensure_ascii=False).encode()).hexdigest(),'real_api':True,'thinking':self.thinking,'reasoning_effort':self.reasoning_effort if self.thinking=='enabled' else None,'read_timeout_seconds':180 if purpose=='judge' else 40}
   try:
    r=requests.post(self.base+'/chat/completions',headers={'Authorization':'Bearer '+self.key,'Content-Type':'application/json'},json=payload,timeout=(8,180 if purpose=='judge' else 40))
    entry['http_status']=r.status_code
    if r.status_code!=200:
     entry['error']='HTTP_'+str(r.status_code)
     if r.status_code in [401,402]:
      with LOCK:SERVICE_FAILURES[credential_id]=entry['error']
     raise ModelError(entry['error'])
    d=r.json();m=d['choices'][0]['message'];content=m.get('content') or ''
    entry.update(response_id=d.get('id'),response_model=d.get('model'),usage=d.get('usage',{}),content=content,finish_reason=d['choices'][0].get('finish_reason'))
    u=entry['usage'];rates=(.3,1.2) if self.model=='deepseek-flash' else (1.32,3.96)
    entry['estimated_usd_upper_bound']=(u.get('prompt_tokens',0)*rates[0]+u.get('completion_tokens',0)*rates[1])/1e6
    if entry['finish_reason']=='length':entry['error']='OUTPUT_TOKEN_LIMIT_REACHED';raise ModelError(entry['error'])
    result=json.loads(content)
    if not isinstance(result,dict):raise ValueError('JSON应为对象')
    return result
   except (requests.RequestException,ValueError,KeyError,ModelError) as ex:
    entry['error']=entry.get('error',type(ex).__name__)
    if isinstance(ex,ValueError) and entry.get('content') and attempt==0:
     messages.extend([{'role':'assistant','content':entry['content']},{'role':'user','content':'上一次输出格式校验失败。请只输出一个完整JSON对象。若是动作决策，只选择当前一个动作，等待实际工具结果后再决定后续动作，不得输出多个JSON对象或预演工具执行。'}])
    if attempt==1 or entry.get('finish_reason')=='length' or entry.get('http_status') in [400,401,402,403]:raise ModelError(entry['error']) from None
    if entry.get('http_status')==429:
     try:delay=min(15,max(1,float(r.headers.get('Retry-After','3'))))
     except ValueError:delay=3
     entry['retry_delay_seconds']=delay;time.sleep(delay)
   finally:
    entry['seconds']=round(time.perf_counter()-start,4);trace.append(entry)
    with LOCK:
     with self.ledger.open('a',encoding='utf-8') as f:f.write(json.dumps(entry,ensure_ascii=False)+'\n')
