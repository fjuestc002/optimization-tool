import sys
from pathlib import Path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from virtuoso_bridge import VirtuosoClient

c = VirtuosoClient.from_env()
res1 = c.execute_skill('maeGetVar("wwp")')
print('wwp skill res:', res1)

res2 = c.execute_skill('maeGetSetup(?typeName "variables")')
print('variables setup:', res2)
