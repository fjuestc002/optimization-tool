"""Dry-run optimization test (standalone, no Virtuoso needed).

Usage:
    python scripts/test_dry_run.py

Runs a short 5-generation NSGA2 optimization with a mock Virtuoso client
so no SSH connection is required. Demonstrates per-generation logging and
saves/display visualization plots.
"""

import sys
import time
from pathlib import Path

# Ensure project root is on sys.path so we can import optimization
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

import optimization as opt_mod


# ── Mock VirtuosoClient ──────────────────────────────────────────────────────


class MockResult:
    """Mimics the return value of client.execute_skill()."""
    def __init__(self, output: str):
        self.output = output


class MockVirtuosoClient:
    """Returns hardcoded data for a 2-variable, 3-objective optimization."""

    def __init__(self):
        self._var_info = {
            "wwp": "{Inclusion List}3e-07{Inclusion List}{From/To}Auto:300n:10:1u{From/To}",
            "wwn": "{Inclusion List}3e-07{Inclusion List}{From/To}Auto:300n:10:1u{From/To}",
        }

    @classmethod
    def from_env(cls) -> "MockVirtuosoClient":
        return cls()

    def execute_skill(self, skill: str) -> MockResult:
        if 'maeGetSetup(?typeName "variables"' in skill:
            return MockResult('("wwp" "wwn")')
        if "maeGetSetup()" in skill:
            # Format: prefix_letter + lib_name + :cell_name
            # The code strips the first 2 chars of parts[0] to get lib_name
            return MockResult("idigital_1010:test_inv3_maestro")
        if "maeGetVar" in skill:
            name = skill.split('"')[1]
            info = self._var_info.get(name, "0.0")
            return MockResult(info)
        return MockResult("")

    def download_file(self, remote_path: str, local_path: str) -> None:
        """Create a minimal CSV with 3 objectives."""
        import csv
        local = Path(local_path)
        local.parent.mkdir(parents=True, exist_ok=True)
        with open(local, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Name", "Weight", "Spec", "Type", "Value"])
            writer.writerow(["Delay", "1.0", "< 300p", "expr", "1.0e-09"])
            writer.writerow(["RiseTime", "1.0", "< 900p", "expr", "2.0e-09"])
            writer.writerow(["FallTime", "1.0", "< 900p", "expr", "1.5e-09"])


# ── Main ────────────────────────────────────────────────────────────────────


def main():
    # Inject mock Virtuoso client
    opt_mod._get_virtuoso_client_class = lambda: MockVirtuosoClient

    print("=" * 60)
    print("  Dry-run optimization test (standalone)")
    print("  Mock VirtuosoClient — no SSH required")
    print("=" * 60)

    t0 = time.time()
    res = opt_mod.run_optimization_loop(
        dry_run=True,
        generations=5,
        pop_size=10,
        seed=1,
        verbose=True,
        plot=True,
        plot_dir=".",
        show=True,  # interactive display; change to False for headless
    )
    elapsed = round(time.time() - t0, 2)

    print(f"\n{'='*60}")
    print(f"  Optimization finished in {elapsed}s")
    print(f"{'='*60}")

    if hasattr(res, "X") and res.X is not None:
        print(f"  Pareto solutions: {len(res.X)}")
        print(f"  Pareto objectives shape: {res.F.shape}")
        print(f"  Best front (F):")
        for i, f in enumerate(res.F[:5]):
            print(f"    [{i}] {f}")
        if len(res.F) > 5:
            print(f"    ... and {len(res.F) - 5} more")
    else:
        print("  No Pareto solutions found.")


if __name__ == "__main__":
    main()