"""Two real-model runs with different views of the same PDF; not part of 40-group scores."""
import json
from policy_agent.common import ROOT,save,sha
from policy_agent.retrieval import Retriever
from policy_agent.agent import agent
class VisibleDocuments:
 def __init__(self,base,visible):self.base=base;self.visible=set(visible)
 def search(self,query,k=5,doc_ids=None):
  ids=sorted(self.visible.intersection(doc_ids)) if doc_ids else sorted(self.visible)
  if not ids:return {'ok':True,'query':query,'hits':[],'note':'本次检索范围内无匹配资料'}
  return self.base.search(query,k=k,doc_ids=ids)
 def read(self,cid):
  c=self.base.by_id.get(cid)
  if c and c['doc_id'] in self.visible:return self.base.read(cid)
  return {'ok':False,'error':{'code':'DOCUMENT_NOT_AVAILABLE','retryable':False,'message':'本次资料范围不含该片段'}}
def main():
 out=ROOT/'examples/submission/evidence-change'
 if out.exists():raise ValueError('Do not overwrite existing real runs')
 out.mkdir(parents=True);base=Retriever();base.search('护理假');question='职工配偶生育时，男职工可以享受多少天护理假？'
 results={}
 for key,visible in [('single_policy',['D19']),('both_policies',['D19','D20'])]:
  r=agent(question,VisibleDocuments(base,visible));r['delivery_probe']={'visible_doc_ids':visible,'source':'same_original_pdf','modified_document_text':False,'question_unchanged':True}
  save(out/(key+'.json'),r);results[key]=r
  print(key,r['output']['status'],r['model_calls'],flush=True)
  if r['output']['status']=='model_error':raise RuntimeError('API unavailable; preserve run and stop')
 a=results['single_policy'];b=results['both_policies']
 checks={'both_real_models':a['real_model'] and b['real_model'],'single_has_evidence':a['output']['status']=='answered' and 'D19-C010' in a['read_ids'],'both_reads_conflict':b['output']['status']=='needs_confirmation' and all(x in b['read_ids'] for x in ['D19-C010','D20-C012']),'output_changed':a['output']!=b['output']}
 save(out/'summary.json',{'checks':checks,'passed':all(checks.values()),'mode':'real_DeepSeek','not_in_formal_40_or_stability_30':True,'scope':'同题，仅改变可见文档范围；不声称已验证任意新PDF。','model_requests':sum(r['model_calls'] for r in results.values()),'tool_calls':sum(r['tool_calls'] for r in results.values()),'run_sha256':{k:sha(out/(k+'.json')) for k in results}})
 if not all(checks.values()):raise AssertionError(checks)
if __name__=='__main__':main()
