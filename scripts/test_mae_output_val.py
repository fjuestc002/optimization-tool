import sys
from pathlib import Path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from virtuoso_bridge import VirtuosoClient

c = VirtuosoClient.from_env(timeout=300)

test_name = "digital_1010:test_inv3:1"

cmds = [
    f'maeGetOutputValue("Delay" "{test_name}")',
    f'maeGetOutputValue("Delay" ?testName "{test_name}")',
    f'maeGetOutputValue("RiseTime" "{test_name}")',
    f'maeGetOutputValue("FallTime" "{test_name}")',
    'maeGetOutputValue(?name "Delay" ?testName "' + test_name + '")',
]

for cmd in cmds:
    res = c.execute_skill(cmd)
    print(f"SKILL: {cmd}\n  => output={repr(res.output)}, errors={res.errors}")
