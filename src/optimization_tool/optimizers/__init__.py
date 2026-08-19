"""Unified optimizer interface.

Provides a single ``optimize()`` entry point that dispatches to either
pymoo (evolutionary) or OpenBox (Bayesian) backends, depending on the
algorithm name.

Usage::

    from optimization_tool.optimizers import optimize, list_optimizers

    res = optimize(problem, algo, termination=("n_gen", 50),
                   pop_size=20, n_obj=2, seed=1, verbose=True,
                   callback=logger, xl=xl, xu=xu)
    print(res.X, res.F, res.callback_data)
"""

from __future__ import annotations

from typing import Any, Optional

from optimization_tool.optimizers.base import BaseOptimizer, OptimizerResult
from optimization_tool.optimizers.bayesian import BayesianOptimizer
from optimization_tool.optimizers.pymoo_adapter import PymooOptimizer
from optimization_tool.optimizers.registry import (
    OPTIMIZER_REGISTRY,
    list_optimizers,
    validate_algorithm,
)

# Re-export
list_optimizers = list_optimizers


def _get_optimizer_instance(
    name: str,
    pop_size: int,
    n_obj: int,
    callback: Any = None,
    xl: Optional[Any] = None,
    xu: Optional[Any] = None,
) -> BaseOptimizer:
    """Factory: create the right optimizer for the given algorithm name."""
    entry = OPTIMIZER_REGISTRY.get(name.lower())
    if entry is None:
        raise ValueError(
            f"Unknown optimizer '{name}'. Available: {list_optimizers()}"
        )

    typ = entry["type"]

    if typ == "pymoo":
        return PymooOptimizer(name, pop_size, n_obj, callback, xl=xl, xu=xu)
    elif typ == "bayesian":
        return BayesianOptimizer(name, pop_size, n_obj, callback, xl=xl, xu=xu)
    elif typ == "custom":
        # Custom: entry has an "optimizer_class" key
        cls = entry["optimizer_class"]
        if not issubclass(cls, BaseOptimizer):
            raise TypeError(
                f"Custom optimizer '{name}' must subclass BaseOptimizer"
            )
        return cls(name, pop_size, n_obj, callback, xl=xl, xu=xu)
    else:
        raise ValueError(f"Unknown optimizer type '{typ}' for '{name}'")


def optimize(
    problem: Any,
    algorithm: str | BaseOptimizer,
    termination: tuple[str, int] = ("n_gen", 50),
    pop_size: int = 20,
    n_obj: int = 1,
    seed: int = 1,
    verbose: bool = False,
    callback: Any = None,
    xl: Optional[Any] = None,
    xu: Optional[Any] = None,
) -> OptimizerResult:
    """Unified optimisation entry point.

    Parameters
    ----------
    problem:
        A pymoo ``Problem`` instance (or compatible duck type).
    algorithm:
        Algorithm name (e.g. ``"nsga2"``, ``"bayes_gp"``) or a
        ``BaseOptimizer`` instance.
    termination:
        Tuple ``("n_gen", n_generations)``.  The number of generations
        is passed to the underlying optimizer.
    pop_size:
        Population / batch size.
    n_obj:
        Number of objectives.
    seed:
        Random seed.
    verbose:
        Print progress information.
    callback:
        A callable (or object with ``__call__``) invoked after each
        iteration.  For pymoo algorithms this is the standard
        ``OptimizationLogger``; for Bayesian methods progress is
        accumulated and written to ``callback.data`` at the end.
    xl, xu:
        Variable lower / upper bounds (required by some algorithms).

    Returns
    -------
    OptimizerResult with ``.X``, ``.F``, ``.callback_data``.
    """
    # Resolve termination
    if isinstance(termination, tuple) and termination[0] == "n_gen":
        n_gen = int(termination[1])
    elif hasattr(termination, "n_max_gen"):
        n_gen = int(termination.n_max_gen)
    else:
        # Fallback: try to extract max generations
        n_gen = 50

    # Already an instance?
    if isinstance(algorithm, BaseOptimizer):
        optimizer = algorithm
    else:
        # Validate + create
        validate_algorithm(algorithm, n_obj)
        optimizer = _get_optimizer_instance(
            algorithm, pop_size, n_obj, callback, xl=xl, xu=xu
        )

    return optimizer.optimize(problem, n_gen, seed=seed, verbose=verbose)


# Also expose the registry info for inspection
def get_optimizer_info(name: str) -> Optional[dict]:
    """Return the registry entry for an optimizer, or ``None``."""
    return OPTIMIZER_REGISTRY.get(name.lower())


__all__ = [
    "BaseOptimizer",
    "OptimizerResult",
    "list_optimizers",
    "optimize",
    "get_optimizer_info",
]