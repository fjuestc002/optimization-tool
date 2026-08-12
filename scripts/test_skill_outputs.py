import sys
from pathlib import Path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from virtuoso_bridge import VirtuosoClient

c = VirtuosoClient.from_env(timeout=300)

for cmd in [
    'maeGetOutputValue("Delay")',
    'maeGetOutputValue("RiseTime")',
    'maeGetOutputValue("FallTime")',
    'maeGetOutputValue()',
    'maeGetSetup(?typeName "outputs")',
    'axlGetOutputs()',
]:
    res = c.execute_skill(cmd)
    print(f"SKILL: {cmd} => status={res.status}, output={repr(res.output)}, errors={res.errors}")
