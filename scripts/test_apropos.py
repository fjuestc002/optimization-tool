import sys
from pathlib import Path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from virtuoso_bridge import VirtuosoClient

c = VirtuosoClient.from_env(timeout=300)

for query in ['^mae', '^maeGet', '^maeExport', 'Output']:
    res = c.execute_skill(f'apropos("{query}")')
    funcs = [s for s in res.output.replace('(', '').replace(')', '').split() if 'mae' in s.lower() or 'output' in s.lower()]
    print(f"apropos '{query}':", funcs[:30])
