import unittest,json,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1]
result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(R/'tests')))
report={'run':result.testsRun,'passed':result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'method':'deterministic_program_tests_not_model_performance'}
p=R/(sys.argv[1] if len(sys.argv)>1 else 'examples/program-tests.json');p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(report,indent=2),encoding='utf-8');sys.exit(not result.wasSuccessful())
