"""Pymoo algorithm adapter.

Wraps every pymoo evolutionary algorithm into a :class:`BaseOptimizer`
so it can be used through the unified ``optimize()`` interface.
"""

from __future__ import annotations

import importlib
from typing import Any, Optional

import numpy as np

from optimization_tool.optimizers.base import BaseOptimizer, OptimizerResult
from optimization_tool.optimizers.registry import OPTIMIZER_REGISTRY


def _create_pymoo_algorithm(
    name: str,
    pop_size: int,
    n_obj: int,
    callback: Any,
    xl: Optional[np.ndarray] = None,
    xu: Optional[np.ndarray] = None,
) -> Any:
    """Create a pymoo algorithm instance by name (same logic as original)."""
    name = name.lower()
    info = OPTIMIZER_REGISTRY[name]
    module = importlib.import_module(info["module"])
    cls = getattr(module, info["class"])

    if name in ("nsga3", "moead", "ctaea"):
        from pymoo.util.ref_dirs import get_reference_directions

        ref_dirs = get_reference_directions("das-dennis", n_obj, n_partitions=12)
        if name == "nsga3":
            return cls(pop_size=pop_size, ref_dirs=ref_dirs, callback=callback)
        elif name == "moead":
            return cls(ref_dirs=ref_dirs, callback=callback)
        else:  # ctaea
            return cls(ref_dirs=ref_dirs, callback=callback)
    elif name == "cmaes":
        if xl is None or xu is None:
            raise ValueError(
                "CMAES requires xl and xu (variable bounds) to compute initial step size."
            )
        x0 = (xl + xu) / 2.0
        sigma = float((xu - xl).mean() * 0.1)
        if sigma <= 0:
            sigma = 0.1
        return cls(x0=x0, sigma=sigma, pop_size=pop_size, callback=callback)
    elif name == "rnsga3":
        raise ValueError(
            "RNSGA3 requires pre-defined reference points in objective space, "
            "which are not available in the generic optimization loop."
        )
    else:
        # GA, DE, PSO, NSGA2, SPEA2
        return cls(pop_size=pop_size, callback=callback)


class PymooOptimizer(BaseOptimizer):
    """Wraps a pymoo evolutionary algorithm into the BaseOptimizer interface."""

    def optimize(
        self,
        problem: Any,
        n_gen: int,
        seed: int = 1,
        verbose: bool = False,
    ) -> OptimizerResult:
        from pymoo.optimize import minimize
        from pymoo.termination import get_termination

        algorithm = _create_pymoo_algorithm(
            self.name,
            self.pop_size,
            self.n_obj,
            self.callback,
            xl=self.xl,
            xu=self.xu,
        )
        termination = get_termination("n_gen", n_gen)
        res = minimize(
            problem,
            algorithm,
            termination,
            seed=seed,
            verbose=verbose,
            copy_algorithm=False,
        )

        # Ensure callback_data exists
        callback_data = getattr(res, "callback_data", {})
        if not callback_data and self.callback is not None:
            callback_data = getattr(self.callback, "data", {})

        return OptimizerResult(
            X=res.X if hasattr(res, "X") else None,
            F=res.F if hasattr(res, "F") else None,
            callback_data=callback_data,
        )