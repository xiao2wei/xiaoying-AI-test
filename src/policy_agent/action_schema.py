"""Simple transport schemas for current action format repair; validated locally too."""
def obj(properties):return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}
def string():return {'type':'string'}
def array(item):return {'type':'array','items':item}
CITATION=obj({'chunk_id':string(),'quote':string()})
RESULT=obj({'status':{'type':'string','enum':['answered','needs_confirmation','insufficient_evidence','tool_error','limit_reached','model_error','validation_failed']},'claims':array(obj({'text':string(),'citations':array(CITATION)})),'gaps':array(string())})
def tool(name,parameters):return {'type':'function','function':{'name':name,'strict':True,'description':'提交当前'+name+'动作；实际工具由程序随后执行。','parameters':parameters}}
ACTION_TOOLS=[tool('search',obj({'query':string(),'doc_ids':array(string()),'reason':string()})),tool('read',obj({'chunk_ids':array(string()),'reason':string()})),tool('finish',obj({'result':RESULT,'reason':string()}))]
