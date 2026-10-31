"""Transport schema for one action. Used only to repair malformed action responses."""
def obj(properties):return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}
def string():return {'type':'string'}
def array(item):return {'type':'array','items':item}
CITATION=obj({'chunk_id':string(),'quote':string()})
RESULT=obj({'status':{'type':'string','enum':['answered','needs_confirmation','insufficient_evidence','tool_error','limit_reached','model_error','validation_failed']},'claims':array(obj({'text':string(),'citations':array(CITATION)})),'gaps':array(string())})
SEARCH=obj({'action':{'type':'string','enum':['search']},'arguments':obj({'query':string(),'doc_ids':array(string())}),'reason':string()})
READ=obj({'action':{'type':'string','enum':['read']},'arguments':obj({'chunk_ids':array(string())}),'reason':string()})
FINISH=obj({'action':{'type':'string','enum':['finish']},'result':RESULT,'reason':string()})
ACTION_TOOL={'type':'function','function':{'name':'submit_action','strict':True,'description':'提交当前一个动作的结构化表示；业务工具由程序随后执行。','parameters':obj({'decision':{'anyOf':[SEARCH,READ,FINISH]}})}}
