import time
class ToolSession:
 def __init__(self,retriever,trace,fault=None,max_tools=10):
  self.r=retriever;self.trace=trace;self.fault=fault or {};self.limit=max_tools;self.count=0;self.fault_count=0;self.read={};self.first_hits=None
 def execute(self,name,args):
  if self.count>=self.limit:return {'ok':False,'error':{'code':'LIMIT_REACHED','retryable':False,'message':'工具调用上限已到'}}
  self.count+=1;t=time.perf_counter()
  try:
   if self.fault.get('tool')==name and (self.fault.get('mode')=='always' or self.fault_count==0):
    self.fault_count+=1;result={'ok':False,'error':{'code':self.fault['code'],'retryable':self.fault['code']=='TEMPORARY_UNAVAILABLE','message':'显式测试故障注入：'+self.fault['code']},'fault_injected':True}
   elif name=='search':result=self.r.search(**args)
   elif name=='read':result=self.r.read(args.get('chunk_id'))
   else:result={'ok':False,'error':{'code':'UNKNOWN_TOOL','retryable':False,'message':'工具不存在'}}
  except (TypeError,KeyError,ValueError) as e:result={'ok':False,'error':{'code':'INVALID_ARGUMENT','retryable':False,'message':str(e)[:150]}}
  except Exception as e:result={'ok':False,'error':{'code':'TOOL_RUNTIME_ERROR','retryable':False,'message':type(e).__name__}}
  if name=='search' and self.first_hits is None:
   self.first_hits=[h['chunk_id'] for h in result.get('hits',[])]
  if name=='read' and result.get('ok'):self.read[result['chunk']['chunk_id']]=result['chunk']
  self.trace.append({'kind':'tool','name':name,'arguments':args,'result':result,'seconds':round(time.perf_counter()-t,4),'attempt_number':self.count})
  return result
