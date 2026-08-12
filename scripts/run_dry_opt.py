import sys
from pathlib import Path

# Ensure project root is on sys.path so this script can import root-level modules.
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from optimization import run_optimization_loop

if __name__ == '__main__':
    res = run_optimization_loop(run_directory='/home/colon/Desktop/project1010drv', generations=3, pop_size=10, dry_run=True, seed=1)
    print('Optimization finished')
    try:
        print('Pareto size:', len(res.X) if hasattr(res, 'X') and res.X is not None else 'N/A')
        print('F shape:', res.F.shape if hasattr(res, 'F') and res.F is not None else 'N/A')
    except Exception as e:
        print('Result introspect error:', e)
