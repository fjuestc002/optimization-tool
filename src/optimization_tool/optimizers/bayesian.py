"""Bayesian optimizer using scikit-optimize.

Supports three single-objective surrogates (GP, RF, GBRT), a multi-objective
mode via ParEGO (random scalarisation), and RF-based optimisation for higher
dimensions — all through the unified :class:`BaseOptimizer` interface.

Algorithm mapping
-----------------
* ``bayes_gp``    — GP + EI,        single-objective  (best sample efficiency)
* ``bayes_rf``    — Random Forest,  single-objective  (robust, higher dims)
* ``bayes_gbrt``  — GBRT,           single-objective  (fast with many evals)
* ``bayes_mo``    — GP + ParEGO,     multi-objective   (random scalarisation)
* ``bayes_turbo`` — RF + EI,        single/multi      (RF-based, higher dims)
"""

from __future__ import annotations

from typing import Any, Callable, Optional

import numpy as np

from optimization_tool.optimizers.base import BaseOptimizer, OptimizerResult
from optimization_tool.optimizers.registry import OPTIMIZER_REGISTRY


# ── Progress tracker ──────────────────────────────────────────────────────────


class _ProgressTracker:
    """Tracks per-iteration history — compatible with ``OptimizationLogger``."""

    def __init__(self, n_var: int, n_obj: int):
        self.n_var = n_var
        self.n_obj = n_obj
        self.n_eval = 0
        self.all_X: list[np.ndarray] = []
        self.all_F: list[np.ndarray] = []
        self.best_X: list[np.ndarray] = []
        self.best_F: list[np.ndarray] = []
        self.n_gen: list[int] = []
        self.n_evals: list[int] = []

    def add(self, x: np.ndarray, f: np.ndarray) -> None:
        """Record one evaluation."""
        self.n_eval += 1
        self.all_X.append(x.copy())
        self.all_F.append(f.copy())
        self.n_gen.append(self.n_eval)
        self.n_evals.append(self.n_eval)

        if self.n_obj == 1:
            if not self.best_F or f[0] < self.best_F[-1][0]:
                self.best_X.append(x.copy())
                self.best_F.append(f.copy())
            else:
                self.best_X.append(self.best_X[-1].copy())
                self.best_F.append(self.best_F[-1].copy())
        else:
            f_sum = float(f.sum())
            if not self.best_F or f_sum < float(self.best_F[-1].sum()):
                self.best_X.append(x.copy())
                self.best_F.append(f.copy())
            else:
                self.best_X.append(self.best_X[-1].copy())
                self.best_F.append(self.best_F[-1].copy())

    def get_data(self) -> dict[str, Any]:
        return {
            "n_gen": list(self.n_gen),
            "n_eval": list(self.n_evals),
            "best_X": [x.tolist() for x in self.best_X],
            "best_F": [f.tolist() for f in self.best_F],
            "all_X": [x.tolist() for x in self.all_X],
            "all_F": [f.tolist() for f in self.all_F],
        }


# ── Helpers: pymoo → scikit-optimize ─────────────────────────────────────────


def _build_bounds(problem: Any) -> list[tuple[float, float]]:
    """Extract variable bounds from a pymoo ``Problem``."""
    n = problem.n_var
    xl = [float(problem.xl[i]) for i in range(n)]
    xu = [float(problem.xu[i]) for i in range(n)]
    return list(zip(xl, xu))


def _make_single_eval_func(
    problem: Any,
    tracker: _ProgressTracker,
) -> Callable[[list[float]], float]:
    """Wrap a pymoo ``Problem._evaluate`` for ``skopt.gp_minimize``.

    Returns a function ``f(x) -> scalar`` suitable for single-objective
    Bayesian optimisation.
    """

    def func(x: list[float]) -> float:
        x_arr = np.array(x, dtype=float).reshape(1, -1)
        out: dict[str, Any] = {}
        problem._evaluate(x_arr, out)
        f = float(np.asarray(out["F"][0], dtype=float).flat[0])
        tracker.add(np.array(x), np.array([f]))
        return f

    return func


class BayesianOptimizer(BaseOptimizer):
    """Bayesian optimisation via scikit-optimize.

    Parameters
    ----------
    name: Algorithm name (key in ``OPTIMIZER_REGISTRY``).
    pop_size: Ignored for Bayesian methods (kept for API compatibility).
    n_obj: Number of objectives.
    callback: Pymoo-style callback (``OptimizationLogger``).
    xl, xu: Variable bounds (unused; bounds are read from the problem).
    """

    def __init__(
        self,
        name: str,
        pop_size: int = 20,
        n_obj: int = 1,
        callback: Any = None,
        xl: Optional[np.ndarray] = None,
        xu: Optional[np.ndarray] = None,
    ):
        super().__init__(name, pop_size, n_obj, callback, xl, xu)
        self._resolve_config()

    def _resolve_config(self) -> None:
        entry = OPTIMIZER_REGISTRY.get(self.name, {})
        self.surrogate_type: str = entry.get("surrogate", "gp")
        self.acq_type: str = entry.get("acquisition", "EI")
        self.use_turbo: bool = entry.get("use_turbo", False)

    def _get_skopt_func(self):
        """Return the right ``skopt`` minimisation function."""
        import skopt

        mapping = {
            "gp": skopt.gp_minimize,
            "prf": skopt.forest_minimize,
            "lightgbm": skopt.gbrt_minimize,
        }
        return mapping.get(self.surrogate_type, skopt.gp_minimize)

    def _run_single_objective(
        self,
        problem: Any,
        n_gen: int,
        seed: int,
        verbose: bool,
        tracker: _ProgressTracker,
    ) -> OptimizerResult:
        """Run single-objective Bayesian optimisation."""
        from skopt import gp_minimize

        bounds = _build_bounds(problem)
        eval_func = _make_single_eval_func(problem, tracker)
        skopt_func = self._get_skopt_func()

        # Initial random points (at most 10, at least 2, capped to n_gen)
        n_initial = max(2, min(10, n_gen // 5))

        # Acquisition function
        acq = "EI"  # Expected Improvement
        if self.acq_type.lower() in ("pi", "lcb"):
            acq = self.acq_type.upper()

        res = skopt_func(
            eval_func,
            bounds,
            n_calls=n_gen,
            n_random_starts=n_initial,
            initial_point_generator="sobol",
            acq_func=acq,
            random_state=seed,
            verbose=verbose,
        )

        # Best solution
        best_x = np.array(res.x, dtype=float).reshape(1, -1)
        best_f = np.array([[res.fun]])

        # Populate callback data
        callback_data = tracker.get_data()

        # Copy into the pymoo-style logger if provided
        if self.callback is not None and hasattr(self.callback, "data"):
            for key in ("n_gen", "n_eval", "best_X", "best_F", "all_X", "all_F"):
                if key in callback_data:
                    self.callback.data[key] = callback_data[key]

        return OptimizerResult(X=best_x, F=best_f, callback_data=callback_data)

    def _run_multi_objective(
        self,
        problem: Any,
        n_gen: int,
        seed: int,
        verbose: bool,
        tracker: _ProgressTracker,
    ) -> OptimizerResult:
        """Multi-objective Bayesian optimisation via ParEGO + ask/tell.

        Uses scikit-optimize's ``Optimizer`` with ``ask()`` / ``tell()`` to
        drive the search.  At each iteration a random weight vector is drawn
        to scalarise the multi-objective problem, the GP model proposes the
        next candidate, the true vector is evaluated, and the model is updated
        with the scalarised value.  True objective vectors are accumulated
        for Pareto-front extraction at the end.
        """
        from skopt import Optimizer

        bounds = _build_bounds(problem)
        rng = np.random.RandomState(seed)
        n_var = problem.n_var

        # Build a GP-based Optimizer
        n_initial = max(2, min(10, n_gen // 5))
        opt = Optimizer(
            bounds,
            n_initial_points=n_initial,
            initial_point_generator="sobol",
            acq_func="EI",
            random_state=seed,
        )

        for i in range(n_gen):
            # Random weight vector (uniform on simplex)
            w = rng.rand(self.n_obj)
            w = w / w.sum()

            # Ask the optimiser for the next candidate
            if i < n_initial:
                # Random initial points (handled by Optimizer)
                x = opt.ask()
            else:
                x = opt.ask()

            # Evaluate the true function
            x_arr = np.array(x, dtype=float).reshape(1, -1)
            out: dict[str, Any] = {}
            problem._evaluate(x_arr, out)
            f_raw = np.asarray(out["F"][0], dtype=float)

            # Record the true objective vector
            tracker.add(np.array(x), f_raw.copy())

            # Scalarise (augmented Chebyshev) and tell the GP
            f_scalar = float(np.max(w * f_raw) + 0.05 * np.sum(w * f_raw))
            opt.tell(x, f_scalar)

            if verbose and (i + 1) % 10 == 0:
                print(f"  ParEGO iter {i+1}/{n_gen}")

        # ── Extract Pareto set from all evaluated points ────────────────
        all_X = np.array(tracker.all_X) if tracker.all_X else np.empty((0, n_var))
        all_F = np.array(tracker.all_F) if tracker.all_F else np.empty((0, self.n_obj))

        if len(all_F) > 0:
            pareto_mask = _is_pareto_efficient(all_F)
            X = all_X[pareto_mask]
            F = all_F[pareto_mask]
        else:
            X = np.empty((0, n_var))
            F = np.empty((0, self.n_obj))

        callback_data = tracker.get_data()

        if self.callback is not None and hasattr(self.callback, "data"):
            for key in ("n_gen", "n_eval", "best_X", "best_F", "all_X", "all_F"):
                if key in callback_data:
                    self.callback.data[key] = callback_data[key]

        return OptimizerResult(X=X, F=F, callback_data=callback_data)

    def optimize(
        self,
        problem: Any,
        n_gen: int,
        seed: int = 1,
        verbose: bool = False,
    ) -> OptimizerResult:
        tracker = _ProgressTracker(problem.n_var, self.n_obj)

        if self.n_obj > 1:
            return self._run_multi_objective(problem, n_gen, seed, verbose, tracker)
        else:
            return self._run_single_objective(problem, n_gen, seed, verbose, tracker)


# ── Pareto filter ─────────────────────────────────────────────────────────────


def _is_pareto_efficient(F: np.ndarray) -> np.ndarray:
    """Return a boolean mask indicating which rows of *F* are Pareto-optimal.

    Assumes minimisation (lower is better).
    """
    n = F.shape[0]
    is_efficient = np.ones(n, dtype=bool)
    for i in range(n):
        if is_efficient[i]:
            # Keep i if no other point dominates it
            is_efficient[is_efficient] = np.any(
                F[is_efficient] < F[i], axis=1
            )
            is_efficient[i] = True  # keep i
    return is_efficient