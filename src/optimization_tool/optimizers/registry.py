"""Central optimizer registry.

Extends the original pymoo-only ``ALGORITHM_REGISTRY`` with Bayesian entries
(OpenBox), and provides helpers for lookup, validation, and listing.

Each entry::

    {
        "type": "pymoo" | "bayesian" | "custom",
        # pymoo-specific:
        "module": "pymoo.algorithms.moo.nsga2",
        "class": "NSGA2",
        # bayesian-specific:
        "surrogate": "gp" | "prf" | "lightgbm",
        "acquisition": "ei" | "ehvi" | "ts" | ...,
        # common:
        "categories": ["single"] | ["multi"] | ["many"],
    }
"""

from __future__ import annotations

from typing import Any, Optional

# ── Registry ──────────────────────────────────────────────────────────────────

OPTIMIZER_REGISTRY: dict[str, dict[str, Any]] = {
    # ── pymoo: single-objective ────────────────────────────────────────────────
    "ga": {
        "type": "pymoo",
        "module": "pymoo.algorithms.soo.nonconvex.ga",
        "class": "GA",
        "categories": ["single"],
    },
    "de": {
        "type": "pymoo",
        "module": "pymoo.algorithms.soo.nonconvex.de",
        "class": "DE",
        "categories": ["single"],
    },
    "pso": {
        "type": "pymoo",
        "module": "pymoo.algorithms.soo.nonconvex.pso",
        "class": "PSO",
        "categories": ["single"],
    },
    "cmaes": {
        "type": "pymoo",
        "module": "pymoo.algorithms.soo.nonconvex.cmaes",
        "class": "CMAES",
        "categories": ["single"],
    },
    # ── pymoo: multi-objective (2-3) ───────────────────────────────────────────
    "nsga2": {
        "type": "pymoo",
        "module": "pymoo.algorithms.moo.nsga2",
        "class": "NSGA2",
        "categories": ["multi"],
    },
    "spea2": {
        "type": "pymoo",
        "module": "pymoo.algorithms.moo.spea2",
        "class": "SPEA2",
        "categories": ["multi"],
    },
    # ── pymoo: multi + many-objective ──────────────────────────────────────────
    "nsga3": {
        "type": "pymoo",
        "module": "pymoo.algorithms.moo.nsga3",
        "class": "NSGA3",
        "categories": ["multi", "many"],
    },
    "moead": {
        "type": "pymoo",
        "module": "pymoo.algorithms.moo.moead",
        "class": "MOEAD",
        "categories": ["multi", "many"],
    },
    "rnsga3": {
        "type": "pymoo",
        "module": "pymoo.algorithms.moo.rnsga3",
        "class": "RNSGA3",
        "categories": ["multi", "many"],
    },
    # ── pymoo: many-objective ──────────────────────────────────────────────────
    "ctaea": {
        "type": "pymoo",
        "module": "pymoo.algorithms.moo.ctaea",
        "class": "CTAEA",
        "categories": ["many"],
    },
    # ── Bayesian: single-objective (scikit-optimize) ────────────────────────────
    "bayes_gp": {
        "type": "bayesian",
        "surrogate": "gp",
        "acquisition": "ei",
        "categories": ["single"],
        "description": "GP + EI — best sample efficiency for low-dim (<20)",
    },
    "bayes_rf": {
        "type": "bayesian",
        "surrogate": "prf",
        "acquisition": "ei",
        "categories": ["single"],
        "description": "Random Forest + EI — robust, handles higher dims",
    },
    "bayes_gbrt": {
        "type": "bayesian",
        "surrogate": "lightgbm",
        "acquisition": "ei",
        "categories": ["single"],
        "description": "LightGBM + EI (fast, good for many evals)",
    },
    # ── Bayesian: multi-objective ──────────────────────────────────────────────
    "bayes_mo": {
        "type": "bayesian",
        "surrogate": "gp",
        "acquisition": "parego",
        "categories": ["multi"],
        "description": "GP + ParEGO (multi-objective, random scalarisation)",
    },
    # ── Bayesian: high-dim friendly (RF-based) ────────────────────────────────
    "bayes_turbo": {
        "type": "bayesian",
        "surrogate": "prf",
        "acquisition": "ei",
        "use_turbo": True,
        "categories": ["single", "multi"],
        "description": "RF + EI (robust for higher dims, single/multi)",
    },
}


# ── Helpers ───────────────────────────────────────────────────────────────────


def _category_for_n_obj(n_obj: int) -> str:
    """Map number of objectives to a category string."""
    if n_obj == 1:
        return "single"
    elif n_obj <= 3:
        return "multi"
    else:
        return "many"


def list_optimizers(n_obj: Optional[int] = None) -> list[str]:
    """List available optimizers, optionally filtered by problem dimension.

    Parameters
    ----------
    n_obj: If given, only return optimizers suitable for that many objectives.

    Returns
    -------
    Sorted list of algorithm names.
    """
    if n_obj is None:
        return sorted(OPTIMIZER_REGISTRY)
    cat = _category_for_n_obj(n_obj)
    return sorted(
        name
        for name, info in OPTIMIZER_REGISTRY.items()
        if cat in info.get("categories", [])
    )


def validate_algorithm(name: str, n_obj: int) -> None:
    """Raise ``ValueError`` if *name* is unknown or unsuitable for *n_obj*."""
    name = name.lower()
    if name not in OPTIMIZER_REGISTRY:
        raise ValueError(
            f"Unknown optimizer '{name}'. Available: {list_optimizers()}"
        )
    cat = _category_for_n_obj(n_obj)
    info = OPTIMIZER_REGISTRY[name]
    if cat not in info.get("categories", []):
        suitable = list_optimizers(n_obj)
        raise ValueError(
            f"Optimizer '{name}' is not suitable for {n_obj}-objective problem "
            f"(category: {cat}). Choose from: {suitable}"
        )