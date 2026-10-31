"""Explicit offline MOCK, never a model-quality or ReAct performance result."""
import argparse,json
from pathlib import Path
from unittest.mock import patch
from policy_agent.agent import agent
from policy_agent.retrieval import Corpus
from policy_agent.common import save

class OfflineCorpus(Corpus):
    def search(self,query,k=5,doc_ids=None):
        c=self.by_id['D03-C008']
        return {'ok':True,'query':query,'hits':[{'chunk_id':c['chunk_id'],'doc_id':c['doc_id'],'excerpt':c['text']}],'mock':True}

class ScriptedModel:
    def __init__(self,actions):self.actions=iter(actions)
    def call(self,messages,trace,purpose,**kwargs):
        trace.append({'kind':'mock_model','purpose':purpose,'real_api':False,'note':'预设动作，只验证流程'})
        return next(self.actions)

def run(out):
    out=Path(out)
    if out.exists():raise ValueError('Use a new output directory; do not overwrite evidence')
    corpus=OfflineCorpus();c=corpus.by_id['D03-C008']
    finish={'action':'finish','result':{'status':'answered','claims':[{'text':c['text'],'citations':[{'chunk_id':c['chunk_id'],'quote':c['text']}]}],'gaps':[]},'reason':'Mock：返回实际读取片段，仅验证引用流程'}
    gap={'action':'finish','result':{'status':'insufficient_evidence','claims':[],'gaps':['本资料未提供校园Wi-Fi接入信息，请提供学校官方网络接入说明。']},'reason':'Mock：预设资料不足分支'}
    cases=[('normal','读取科研经费条款',[
        {'action':'search','arguments':{'query':'科研经费执行期限'}},
        {'action':'read','arguments':{'chunk_ids':[c['chunk_id']]}},finish,finish],{},10,'answered'),
        ('insufficient','校园Wi-Fi如何接入？',[{'action':'search','arguments':{'query':'校园Wi-Fi接入'}},gap,gap],{},10,'insufficient_evidence'),
        ('tool_failure','工具持续失败时停止',[{'action':'search','arguments':{'query':'科研经费'}}]*2,{'tool':'search','mode':'always','code':'TEMPORARY_UNAVAILABLE'},2,'limit_reached')]
    outputs=[]
    with patch('policy_agent.model.requests.post',side_effect=AssertionError('Offline MOCK must not use the network')):
        for name,q,actions,fault,limit,expected in cases:
            r=agent(q,corpus,fault=fault,max_tools=limit,model=ScriptedModel(actions))
            assert r['output']['status']==expected and not r['real_model'] and r['model_calls']==0
            r.update(mock=True,quality_evidence=False,warning='OFFLINE MOCK：预设模型动作及检索候选；工具读取、校验和上限真实执行，不证明真实模型决策效果。')
            save(out/(name+'.json'),r);outputs.append({'case':name,'status':r['output']['status'],'tool_calls':r['tool_calls']})
    summary={'mode':'OFFLINE_MOCK','real_api_requests':0,'model_quality_evidence':False,'cases':outputs}
    save(out/'summary.json',summary);print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True);a=p.parse_args();run(a.out)
