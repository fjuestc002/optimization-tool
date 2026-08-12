import sys
from pathlib import Path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from virtuoso_bridge import VirtuosoClient

c = VirtuosoClient.from_env(timeout=300)

for fn in [
    'maeExportOutputView()',
    'maeExportReport()',
    'maeExportResults()',
    'maeExportData()',
    'maeGetOutputValue("Delay" ?history "Interactive.0")',
    'maeGetOutputValue("Delay" "Interactive.0")',
    'maeGetOutputValue("Delay" "Active")',
    'maeGetOutputValue("Delay" "1")',
    'maeGetSetup(?typeName "history")',
]:
    res = c.execute_skill(fn)
    print(f"SKILL: {fn}\n  => status={res.status}, output={repr(res.output)}, errors={res.errors}")
