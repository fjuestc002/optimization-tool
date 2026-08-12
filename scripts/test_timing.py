import sys
import time
from pathlib import Path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from virtuoso_bridge import VirtuosoClient

c = VirtuosoClient.from_env(timeout=300)
print('Connected with timeout=300')

t0 = time.time()
r1 = c.execute_skill('maeRunSimulation()', timeout=300)
print('maeRunSimulation time:', round(time.time() - t0, 2), 'result:', r1)

t1 = time.time()
r2 = c.execute_skill("maeWaitUntilDone('All)", timeout=300)
print('maeWaitUntilDone time:', round(time.time() - t1, 2), 'result:', r2)

t2 = time.time()
r3 = c.execute_skill('maeExportOutputView()', timeout=300)
print('maeExportOutputView time:', round(time.time() - t2, 2), 'result:', r3)

