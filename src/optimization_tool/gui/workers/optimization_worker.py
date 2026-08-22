"""QThread worker for running optimization in the background.

Emits per-generation progress signals for real-time GUI updates.
Works in two modes:
  - **dry-run**: creates a synthetic pymoo test problem (sphere / zdt1)
  - **real-run**: delegates to ``run_optimization_loop()`` with Virtuoso
"""

from __future__ import annotations

from typing import Any, Optional

import numpy as np
from PySide6.QtCore import QThread, Signal, QObject


class OptimizationWorkerSignals(QObject):
    """Signals emitted by OptimizationWorker."""

    progress = Signal(int, int, list, list)  # gen, n_eval, best_F, best_X
    log = Signal(str, str)                   # message, level ("info"/"ok"/"warn"/"error")
    plot_update = Signal(object)             # dict with gen/eval history for plots
    finished = Signal(object)                # OptimizerResult
    error = Signal(str)                      # error message


class _ProgressCallback:
    """Pymoo-compatible callback that emits Qt signals each generation.

    Wraps the standard ``OptimizationLogger`` behaviour and adds signal
    emission for the GUI.
    """

    def __init__(
        self,
        var_names: list[str],
        obj_names: list[str],
        signals: OptimizationWorkerSignals,
    ):
        self.var_names = var_names
        self.obj_names = obj_names
        self.signals = signals
        self.is_initialized = False
        self.data: dict = {
            "n_gen": [],
            "n_eval": [],
            "best_X": [],
            "best_F": [],
            "all_X": [],
            "all_F": [],
        }

    def __call__(self, algorithm: Any) -> None:
        """Called by pymoo after each generation."""
        gen = algorithm.n_gen
        pop = algorithm.pop
        X = pop.get("X")
        F = pop.get("F")

        # Best individual = minimum sum of objectives
        best_idx = int(np.argmin(F.sum(axis=1)))
        best_X = X[best_idx]
        best_F = F[best_idx]

        self.data["n_gen"].append(gen)
        self.data["n_eval"].append(algorithm.evaluator.n_eval)
        self.data["best_X"].append(best_X.copy())
        self.data["best_F"].append(best_F.copy())
        self.data["all_X"].append(X.copy())
        self.data["all_F"].append(F.copy())

        # Emit GUI signals
        n_eval = algorithm.evaluator.n_eval
        self.signals.progress.emit(gen, n_eval, best_F.tolist(), best_X.tolist())
        self.signals.plot_update.emit({
            "n_gen": list(self.data["n_gen"]),
            "n_eval": list(self.data["n_eval"]),
            "best_X": [x.tolist() for x in self.data["best_X"]],
            "best_F": [f.tolist() for f in self.data["best_F"]],
            "all_X": [x.tolist() for x in self.data["all_X"]],
            "all_F": [f.tolist() for f in self.data["all_F"]],
        })

        # Terminal display
        print(f"\n{'='*60}")
        print(f"  Generation {gen}  |  Evaluations: {n_eval}")
        print(f"{'='*60}")
        print("  Variables:")
        for i, name in enumerate(self.var_names):
            print(f"    {name}: {best_X[i]:.6e}")
        print("  Objectives:")
        for i, name in enumerate(self.obj_names):
            print(f"    {name}: {best_F[i]:.6e}")
        print(f"  Best sum: {best_F.sum():.6e}")


class OptimizationWorker(QThread):
    """Run optimization in a separate thread.

    Emits ``signals.progress`` and ``signals.plot_update`` after each
    generation so the UI can update convergence plots in real time.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.signals = OptimizationWorkerSignals()
        self._params = {}
        self._abort = False

    def configure(self, **kwargs):
        """Set optimization parameters before starting."""
        self._params = dict(kwargs)

    def abort(self):
        """Signal the worker to stop at the next generation."""
        self._abort = True

    def run(self):
        """Execute optimisation in background thread."""
        try:
            params = dict(self._params)
            dry_run = params.get("dry_run", True)

            if dry_run:
                self._run_dry(params)
            else:
                self._run_real(params)

        except KeyboardInterrupt:
            self.signals.log.emit("优化已停止", "warn")
            self.signals.finished.emit(None)

        except Exception as exc:
            import traceback
            tb = traceback.format_exc()
            self.signals.log.emit(f"优化错误: {exc}", "error")
            self.signals.log.emit(tb, "error")
            self.signals.error.emit(str(exc))

    # ── Dry-run: synthetic test problem ────────────────────────────────────

    def _run_dry(self, params: dict) -> None:
        """Run optimisation on a synthetic pymoo test problem."""
        from pymoo.problems import get_problem

        from optimization_tool.optimizers import optimize

        algo = params.get("algo", "nsga2")
        generations = params.get("generations", 50)
        pop_size = params.get("pop_size", 50)
        seed = params.get("seed", 1)
        verbose = params.get("verbose", False)

        # Choose a test problem that matches the algorithm
        algo_lower = algo.lower()
        is_multi = algo_lower in (
            "nsga2", "nsga3", "spea2", "moead", "ctaea", "rnsga3",
            "bayes_mo", "bayes_turbo",
        )
        problem_name = "zdt1" if is_multi else "sphere"
        n_obj = 2 if is_multi else 1

        problem = get_problem(problem_name)
        var_names = [f"x{i+1}" for i in range(problem.n_var)]
        obj_names = [f"f{i+1}" for i in range(n_obj)]

        self.signals.log.emit(f"Dry-Run 模式 — 测试问题: {problem_name}", "info")
        self.signals.log.emit(
            f"  算法: {algo}, 代数: {generations}, 种群: {pop_size}", "info"
        )

        # Create progress callback
        callback = _ProgressCallback(var_names, obj_names, self.signals)

        result = optimize(
            problem,
            algo,
            termination=("n_gen", generations),
            pop_size=pop_size,
            n_obj=n_obj,
            seed=seed,
            verbose=verbose,
            callback=callback,
        )

        # Attach callback data for the UI
        if not result.callback_data:
            result.callback_data = callback.data
        # Ensure var_names / obj_names are in callback_data for the results table
        result.callback_data["var_names"] = var_names
        result.callback_data["obj_names"] = obj_names

        # For Bayesian optimizers (which don't emit per-iteration signals),
        # emit the full history now so the convergence plot can render
        cb = result.callback_data
        if cb and cb.get("n_gen"):
            self.signals.plot_update.emit({
                "n_gen": cb["n_gen"],
                "n_eval": cb["n_eval"],
                "best_X": cb["best_X"],
                "best_F": cb["best_F"],
                "all_X": cb["all_X"],
                "all_F": cb["all_F"],
            })

        if self._abort:
            self.signals.log.emit("优化已中止", "warn")
        else:
            self.signals.log.emit(f"优化完成 ✓  Pareto 解数: {len(result.F)}", "ok")

        self.signals.finished.emit(result)

    # ── Real-run: Virtuoso-backed ──────────────────────────────────────────

    def _run_real(self, params: dict) -> None:
        """Run optimisation with Virtuoso via ``run_optimization_loop``."""
        from optimization_tool.optimization import run_optimization_loop

        self.signals.log.emit("优化开始 (Virtuoso 模式)...", "info")

        # Build a progress callback that emits Qt signals
        signals = self.signals

        def _progress_callback(*, gen, n_eval, best_X, best_F, all_X, all_F, obj_names=None):
            if self._abort:
                raise KeyboardInterrupt("优化已中止")
            signals.progress.emit(gen, n_eval, best_F.tolist(), best_X.tolist())
            signals.plot_update.emit({
                "n_gen": [gen],
                "n_eval": [n_eval],
                "best_X": [best_X.tolist()],
                "best_F": [best_F.tolist()],
                "all_X": [all_X.tolist()],
                "all_F": [all_F.tolist()],
                "obj_names": obj_names,
            })

        # Extract project object if present (not a standard run_optimization_loop param)
        project_obj = params.pop("project_obj", None)

        result = run_optimization_loop(
            **params,
            progress_callback=_progress_callback,
            project_obj=project_obj,
        )

        if self._abort:
            self.signals.log.emit("优化已中止", "warn")
        else:
            n_pareto = len(result.X) if hasattr(result, "X") and result.X is not None else 0
            self.signals.log.emit(f"优化完成 ✓  Pareto 解数: {n_pareto}", "ok")

        self.signals.finished.emit(result)