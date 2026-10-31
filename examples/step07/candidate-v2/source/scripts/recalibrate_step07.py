from concurrent.futures import ThreadPoolExecutor
import runpy
from policy_agent.evaluation import calibrate
with ThreadPoolExecutor(max_workers=2) as pool:
 a=pool.submit(calibrate,'examples/step07/calibration-v5',6)
 b=pool.submit(runpy.run_path,'scripts/check_actionable_gaps.py')
 print(a.result(),flush=True);b.result()
