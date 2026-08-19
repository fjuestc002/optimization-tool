"""Base classes for the optimizer abstraction layer.

Defines the abstract interface that all optimizers (pymoo, Bayesian, custom)
must implement, and a unified result container compatible with pymoo's return
value.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

import numpy as np


@dataclass
class OptimizerResult:
    """Unified optimization result, compatible with pymoo's ``minimize()`` return.

    Attributes:
        X: Decision variables of the best / Pareto-optimal solutions.
            Shape ``(n_solutions, n_vars)``.
        F: Objective values.  Shape ``(n_solutions, n_obj)``.
        callback_data: Per-iteration history dict with keys
            ``n_gen``, ``n_eval``, ``best_X``, ``best_F``, ``all_X``, ``all_F``.
    """

    X: Optional[np.ndarray] = None
    F: Optional[np.ndarray] = None
    callback_data: dict[str, Any] = field(default_factory=dict)


class BaseOptimizer(ABC):
    """Abstract base for all optimizers.

    Subclasses must implement :meth:`optimize` and return an :class:`OptimizerResult`.

    Parameters
    ----------
    name: Algorithm name (key in the registry).
    pop_size: Population / batch size.
    n_obj: Number of objectives.
    callback: Callable invoked after each iteration
        (pymoo-compatible signature: ``callback(algorithm)``).
    xl, xu: Variable lower / upper bounds (optional, used by some algorithms).
    """

    def __init__(
        self,
        name: str,
        pop_size: int = 20,
        n_obj: int = 1,
        callback: Optional[Callable] = None,
        xl: Optional[np.ndarray] = None,
        xu: Optional[np.ndarray] = None,
    ):
        self.name = name
        self.pop_size = pop_size
        self.n_obj = n_obj
        self.callback = callback
        self.xl = xl
        self.xu = xu

    @abstractmethod
    def optimize(
        self,
        problem: Any,
        n_gen: int,
        seed: int = 1,
        verbose: bool = False,
    ) -> OptimizerResult:
        """Run optimisation and return results.

        Parameters
        ----------
        problem: A pymoo ``Problem`` instance (or compatible duck type).
        n_gen: Number of generations / iterations.
        seed: Random seed.
        verbose: Print progress information.

        Returns
        -------
        OptimizerResult with ``.X``, ``.F``, ``.callback_data``.
        """
        ...