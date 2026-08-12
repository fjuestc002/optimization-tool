import sys
import time
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from optimization import run_optimization_loop

def main():
    run_dir = "/home/colon/Desktop/project1010drv"
    print("Starting real optimization loop (dry_run=False)...")
    t0 = time.time()
    res = run_optimization_loop(
        run_directory=run_dir,
        generations=2,
        pop_size=3,
        dry_run=False,
        seed=1,
        verbose=True,
    )
    print("Optimization finished in", round(time.time() - t0, 2), "s")
    if hasattr(res, "X") and res.X is not None:
        print("Pareto solutions (X):", res.X)
        print("Pareto objectives (F):", res.F)

if __name__ == "__main__":
    main()
