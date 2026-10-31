from concurrent.futures import ThreadPoolExecutor
from policy_agent.evaluation import score
from policy_agent.metrics import report
pairs=[('agent','examples/step05/agent-dev-v2'),('baseline','examples/step04/baseline-dev-v1')]
def run(pair):
 name,runs=pair;scores=f'examples/step06/{name}-scores-v5';out=f'examples/step06/{name}-report-v5'
 score('evaluation/dev.json',runs,scores,workers=4)
 report('evaluation/dev.json',runs,scores,out,'examples/step06/program-tests.json')
 return name
with ThreadPoolExecutor(max_workers=2) as pool:
 for name in pool.map(run,pairs):print('COMPLETE',name,flush=True)
