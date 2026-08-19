"""Project directory management for optimization runs.

Provides a lightweight "project shell" that automatically archives each
optimization run into a timestamped directory with configuration snapshots,
per-generation history, and final results — without requiring manual setup.

The project directory is optional. Without it, the tool behaves exactly as
before (backward compatible).

Typical project structure::

    my_project/
    ├── project.json              # project-level metadata (auto-generated)
    ├── runs/
    │   ├── 20260817_143001/      # each run = timestamped directory
    │   │   ├── config.json       #   full configuration snapshot
    │   │   ├── variables.csv     #   variable names + bounds
    │   │   ├── specs.csv         #   objective expressions + weights
    │   │   ├── history.jsonl     #   per-generation log (JSONL)
    │   │   ├── results.json      #   final Pareto set + metadata
    │   │   ├── convergence.png   #   convergence plot (if plot enabled)
    │   │   └── pareto.png        #   Pareto front plot (if plot enabled)
    │   └── ...
    └── context/                  # human notes (optional, never read by code)
"""

from __future__ import annotations

import csv
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


class ProjectRun:
    """One optimization run within a project directory.

    Usage::

        run = ProjectRun.create("my_opamp_opt")
        run.save_config(variables=var_names, objectives=obj_names,
                        algorithm="nsga2", generations=50, pop_size=20)
        # ... run optimization ...
        run.save_results(res, logger)
        run.copy_plot("convergence.png")
        run.copy_plot("pareto.png")
        print(run.dir)  # e.g. "my_opamp_opt/runs/20260817_143001"
    """

    def __init__(self, project_dir: str | Path, run_dir: str | Path):
        self.project_dir = Path(project_dir).resolve()
        self.dir = Path(run_dir).resolve()

    # ── Factory ──────────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        project_dir: str | Path,
        run_name: str | None = None,
    ) -> "ProjectRun":
        """Create a new timestamped run directory under *project_dir*.

        If *run_name* is omitted, a timestamp like ``20260817_143001``
        is generated.  The project directory and any missing parents are
        created automatically.
        """
        project_dir = Path(project_dir).resolve()
        runs_dir = project_dir / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)

        if run_name is None:
            run_name = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = runs_dir / run_name
        run_dir.mkdir(parents=True, exist_ok=True)

        # Ensure project-level metadata exists
        cls._ensure_project_meta(project_dir)

        return cls(project_dir, run_dir)

    @staticmethod
    def _ensure_project_meta(project_dir: Path) -> None:
        meta = project_dir / "project.json"
        if not meta.exists():
            meta.write_text(
                json.dumps(
                    {
                        "created": datetime.now().isoformat(),
                        "description": "",
                        "runs": [],
                    },
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

    # ── Save methods ─────────────────────────────────────────────────────

    def save_config(
        self,
        variables: list[str],
        objectives: list[str],
        algo: str,
        generations: int,
        pop_size: int,
        dry_run: bool,
        seed: int,
        extra: dict[str, Any] | None = None,
    ) -> Path:
        """Save a full configuration snapshot as ``config.json``."""
        config = {
            "timestamp": datetime.now().isoformat(),
            "algorithm": algo,
            "generations": generations,
            "population": pop_size,
            "dry_run": dry_run,
            "seed": seed,
            "variables": variables,
            "objectives": objectives,
        }
        if extra:
            config.update(extra)
        path = self.dir / "config.json"
        path.write_text(
            json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return path

    def save_variables_csv(
        self,
        names: list[str],
        values: list[float],
        mins: list[float],
        maxs: list[float],
    ) -> Path:
        """Save variable names, current values, and bounds as CSV."""
        path = self.dir / "variables.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["name", "value", "min", "max"])
            for n, v, lo, hi in zip(names, values, mins, maxs):
                w.writerow([n, v, lo, hi])
        return path

    def save_specs_csv(
        self,
        names: list[str],
        weights: list[float],
        specs: list[str],
    ) -> Path:
        """Save objective specs as CSV."""
        path = self.dir / "specs.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["name", "weight", "spec"])
            for n, wt, s in zip(names, weights, specs):
                w.writerow([n, wt, s])
        return path

    def save_history(
        self,
        n_gen: list[int],
        n_eval: list[int],
        best_X: list[list[float]],
        best_F: list[list[float]],
        var_names: list[str],
        obj_names: list[str],
    ) -> Path:
        """Save per-generation history as JSONL (one JSON object per line)."""
        path = self.dir / "history.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for gen, ev, x, fx in zip(n_gen, n_eval, best_X, best_F):
                record = {
                    "generation": gen,
                    "evaluations": ev,
                    "variables": {n: float(v) for n, v in zip(var_names, x)},
                    "objectives": {n: float(v) for n, v in zip(obj_names, fx)},
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return path

    def save_results(
        self,
        X: list[list[float]],
        F: list[list[float]],
        var_names: list[str],
        obj_names: list[str],
    ) -> Path:
        """Save final Pareto set as ``results.json``."""
        pareto = []
        for x, fx in zip(X, F):
            pareto.append(
                {
                    "variables": {n: float(v) for n, v in zip(var_names, x)},
                    "objectives": {n: float(v) for n, v in zip(obj_names, fx)},
                }
            )
        data = {
            "timestamp": datetime.now().isoformat(),
            "pareto_count": len(pareto),
            "pareto": pareto,
        }
        path = self.dir / "results.json"
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return path

    def copy_plot(self, src: str | Path) -> Optional[Path]:
        """Copy a plot file into the run directory (if it exists)."""
        src = Path(src)
        if src.exists():
            dst = self.dir / src.name
            shutil.copy2(src, dst)
            return dst
        return None

    # ── Convenience: save everything from one optimization run ────────────

    def save_all(
        self,
        res: Any,
        logger: Any,
        var_names: list[str],
        obj_names: list[str],
    ) -> None:
        """Save all artifacts from a completed pymoo optimization.

        Args:
            res: Return value of ``pymoo.optimize.minimize()``.
            logger: :class:`OptimizationLogger` instance with per-generation data.
            var_names: Variable names.
            obj_names: Objective names.
        """
        # Results (Pareto set)
        if hasattr(res, "X") and res.X is not None:
            self.save_results(
                res.X.tolist() if hasattr(res.X, "tolist") else list(res.X),
                res.F.tolist() if hasattr(res.F, "tolist") else list(res.F),
                var_names,
                obj_names,
            )

        # Per-generation history
        if logger is not None and logger.data.get("n_gen"):
            self.save_history(
                logger.data["n_gen"],
                logger.data["n_eval"],
                [x.tolist() for x in logger.data["best_X"]],
                [f.tolist() for f in logger.data["best_F"]],
                var_names,
                obj_names,
            )