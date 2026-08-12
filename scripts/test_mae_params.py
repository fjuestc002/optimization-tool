import sys
from pathlib import Path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from virtuoso_bridge import VirtuosoClient

c = VirtuosoClient.from_env(timeout=300)

for cmd in [
    'maeExportOutputView(?outputType "results")',
    'maeExportOutputView(?type "results")',
    'maeExportOutputView(?results t)',
    'maeExportOutputView(?view "results")',
    'maeExportOutputView(?fileName "test_out.csv")',
]:
    res = c.execute_skill(cmd)
    print(f"SKILL: {cmd}\n  => status={res.status}, output={repr(res.output)}, errors={res.errors}")
