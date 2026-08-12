"""Optimization harness connecting Virtuoso <-> pymoo.

This module provides a consolidated workflow for:
  - reading optimization variables from Virtuoso,
  - downloading and parsing Maestro CSV outputs,
  - running a pymoo optimization loop,
  - writing variable candidates back to Virtuoso,
  - running simulation and collecting objective values.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any, List, Optional, Tuple

import numpy as np
import pandas as pd

VirtuosoClient = None


def _get_virtuoso_client_class() -> Any:
    global VirtuosoClient
    if VirtuosoClient is None:
        try:
            from virtuoso_bridge import VirtuosoClient as _VirtuosoClient

            VirtuosoClient = _VirtuosoClient
        except Exception as exc:
            raise ImportError(
                "Missing required dependency 'virtuoso_bridge'. "
                "Install it in the current Python environment or activate the correct environment."
            ) from exc
    return VirtuosoClient


def normalize_value(text: str) -> float:
    text = text.strip()
    if not text:
        return 0.0
    text = text.replace("n", "e-9").replace("u", "e-6").replace("m", "e-3")
    return float(text)


def parse_output_value(value: Any) -> Optional[float]:
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    try:
        return float(text)
    except ValueError:
        pass

    match = re.search(r"[-+]?[0-9]*\.?[0-9]+(?:e[-+]?[0-9]+)?", text)
    if match:
        return float(match.group(0))
    return None


# ── Exceptions ───────────────────────────────────────────────────────────────


class VariableBoundsError(Exception):
    """Raised when variable min/max bounds from Virtuoso are invalid.

    This typically means the Virtuoso variable has no optimization range
    defined (e.g. Single Run mode without From/To), or the SKILL output
    format changed and parsing failed.
    """
    pass


# ── Variable info parsing ────────────────────────────────────────────────────


def _parse_var_info(info: str) -> Tuple[float, str, float, float]:
    """Parse ``maeGetVar`` SKILL output into (value, raw_value, min, max).

    Expected Virtuoso output format::

        {Inclusion List}3e-07{Inclusion List}{From/To}Auto:300n:10:1u{From/To}

    The ``{From/To}`` segment is colon-delimited:
    ``<step_type>:<from_value>:<steps>:<to_value>``

    Returns:
        Tuple of (numeric_value, raw_string, min, max).
        Returns (0.0, "0.0", 0.0, 0.0) on parse failure.
    """
    # 1. Current value — between {Inclusion List} tags
    m_val = re.search(r"\{Inclusion List\}([^\{]+)\{Inclusion List\}", info)
    if m_val:
        raw_val = m_val.group(1).strip()
    else:
        # Fallback: generic } value { pattern
        m_val = re.search(r"\}\s*([^\{\s]+)\s*\{", info)
        raw_val = m_val.group(1).strip() if m_val else "0.0"

    try:
        num_val = normalize_value(raw_val)
    except Exception:
        num_val = 0.0

    # 2. From/To range — between {From/To} tags
    #    Format: {From/To}Auto:from_value:steps:to_value{From/To}
    m_range = re.search(r"\{From/To\}([^}]+)\{From/To\}", info)
    var_min = 0.0
    var_max = 0.0
    if m_range:
        parts = m_range.group(1).split(":")
        if len(parts) >= 4:
            # Auto:from:steps:to
            try:
                var_min = normalize_value(parts[1])  # From
                var_max = normalize_value(parts[3])  # To
            except Exception:
                pass
        elif len(parts) >= 3:
            # Fallback: Auto:from:to (3 parts)
            try:
                var_min = normalize_value(parts[1])
                var_max = normalize_value(parts[2])
            except Exception:
                pass
        # Safety: ensure min <= max even if Virtuoso returns them reversed
        if var_min > var_max:
            var_min, var_max = var_max, var_min

    return num_val, raw_val, var_min, var_max


def validate_variable_bounds(
    name: str, value: float, var_min: float, var_max: float
) -> None:
    """Check that a variable's bounds are valid for optimization.

    Raises :class:`VariableBoundsError` if:
    - min or max is 0 (no range defined in Virtuoso)
    - min > max (inverted range, should not happen after parsing fix)
    - current value is outside [min, max]
    """
    if var_min == 0.0 and var_max == 0.0:
        raise VariableBoundsError(
            f"Variable '{name}' has no optimization range (min=0, max=0). "
            "In Virtuoso Maestro, switch to a mode that supports From/To "
            "bounds (e.g. From/To with explicit values), or define the "
            "range in the variable settings."
        )
    if var_min <= 0.0 or var_max <= 0.0:
        raise VariableBoundsError(
            f"Variable '{name}' has invalid range: min={var_min}, max={var_max}. "
            "Both bounds must be positive."
        )
    if var_min > var_max:
        raise VariableBoundsError(
            f"Variable '{name}' has inverted range: min={var_min} > max={var_max}. "
            "This indicates a parsing error — please report the raw "
            "maeGetVar output."
        )
    if value < var_min or value > var_max:
        raise VariableBoundsError(
            f"Variable '{name}' current value {value} is outside "
            f"[{var_min}, {var_max}]."
        )


def fetch_variables(client: Any) -> Tuple[List[str], np.ndarray, np.ndarray, np.ndarray]:
    result = client.execute_skill('maeGetSetup(?typeName "variables" ?enabled t)')
    content = result.output.strip().strip("()")
    names = [t.strip('"') for t in content.split() if t.strip()]

    values: List[float] = []
    mins: List[float] = []
    maxs: List[float] = []

    for name in names:
        info = client.execute_skill(f'maeGetVar("{name}")').output
        num_val, _raw, var_min, var_max = _parse_var_info(info)
        values.append(num_val)
        mins.append(var_min)
        maxs.append(var_max)

    return names, np.array(values, dtype=float), np.array(mins, dtype=float), np.array(maxs, dtype=float)


def _extract_raw_value(info: str) -> str:
    """Extract the raw value string (with units like 'n', 'u', 'm') from maeGetVar output."""
    m_val = re.search(r"\{Inclusion List\}([^\{]+)\{Inclusion List\}", info)
    if m_val:
        return m_val.group(1).strip()
    m_val = re.search(r"\}\s*([^\{\s]+)\s*\{", info)
    if m_val:
        return m_val.group(1).strip()
    nums = re.findall(r"[-+]?[0-9]*\.?[0-9]+(?:e[-+]?[0-9]+)?", info)
    return nums[0] if nums else "0.0"


def fetch_variables_with_units(
    client: Any,
) -> Tuple[List[str], List[str], np.ndarray, np.ndarray, np.ndarray]:
    """Fetch variable names, raw string values (with units), and bounds.

    Like :func:`fetch_variables` but also returns the raw value strings
    (e.g. ``"400n"``, ``"1.2u"``) so callers can preserve Virtuoso unit
    prefixes when writing values back with :func:`mae_set_var_str`.

    Returns:
        Tuple of (names, raw_values, numeric_values, mins, maxs).
    """
    result = client.execute_skill('maeGetSetup(?typeName "variables" ?enabled t)')
    content = result.output.strip().strip("()")
    names = [t.strip('"') for t in content.split() if t.strip()]

    raw_values: List[str] = []
    values: List[float] = []
    mins: List[float] = []
    maxs: List[float] = []

    for name in names:
        info = client.execute_skill(f'maeGetVar("{name}")').output
        num_val, raw_val, var_min, var_max = _parse_var_info(info)
        raw_values.append(raw_val)
        values.append(num_val)
        mins.append(var_min)
        maxs.append(var_max)

    return (
        names,
        raw_values,
        np.array(values, dtype=float),
        np.array(mins, dtype=float),
        np.array(maxs, dtype=float),
    )


def get_current_test_name(client: Any) -> str:
    result = client.execute_skill("maeGetSetup()")
    return result.output


def download_and_parse_specs(
    client: Any,
    run_directory: str,
    current_test_output: str,
    local_dir: Optional[Path] = None,
) -> tuple[List[str], np.ndarray, List[str], Path]:
    if local_dir is None:
        local_dir = Path.cwd()
    parts = current_test_output.split(":")
    lib_name = parts[0][2:] if parts and len(parts) > 0 else "unknown"
    cell_name = parts[1] if len(parts) > 1 else "unknown"
    filename = f"outputs_{lib_name}_{cell_name}_maestro.csv"
    local_path = local_dir / filename
    remote_path = Path(run_directory) / filename
    client.download_file(str(remote_path), str(local_path))

    df = pd.read_csv(local_path)
    expr_df = df[df["Type"] == "expr"]
    names = expr_df["Name"].astype(str).tolist()
    weights = expr_df["Weight"].astype(float).to_numpy()
    specs = expr_df["Spec"].astype(str).tolist()
    return names, weights, specs, local_path


def read_specs_from_csv(path: Path) -> tuple[List[str], np.ndarray, List[str]]:
    df = pd.read_csv(path)
    expr_df = df[df["Type"] == "expr"]
    names = expr_df["Name"].astype(str).tolist()
    weights = expr_df["Weight"].astype(float).to_numpy()
    specs = expr_df["Spec"].astype(str).tolist()
    return names, weights, specs


def mae_set_var(client: Any, name: str, value: float) -> Any:
    skill = f'maeSetVar("{name}" {value})'
    return client.execute_skill(skill)


def mae_set_var_str(client: Any, name: str, raw_value: str) -> Any:
    """Set a variable in Virtuoso using the raw value string (preserving units).

    Use this when you want to keep Virtuoso's engineering-unit prefixes
    (e.g. ``"400n"``, ``"1.2u"``, ``"3m"``) instead of converting to a
    plain float, which would lose the unit information.

    Args:
        client: VirtuosoClient instance
        name: Variable name
        raw_value: Raw value string (e.g. ``"400n"``, not ``4e-7``)

    Example:
        >>> mae_set_var_str(client, "Ibias", "400n")
        # Sends: maeSetVar("Ibias" 400n)  — preserves the nano unit
    """
    skill = f'maeSetVar("{name}" {raw_value})'
    return client.execute_skill(skill)


def run_simulation_and_wait(client: Any, timeout: int = 600) -> Any:
    """Run simulation and wait for completion using callback-based approach.

    Uses client.maestro.run_and_wait() which registers a SKILL callback
    that writes a marker file when done. Python polls the marker via SSH
    every 2 seconds, keeping the SKILL channel free during the wait.

    Args:
        client: VirtuosoClient instance
        timeout: Max wait time in seconds (default 600s = 10 minutes)

    Returns:
        VirtuosoResult or tuple (history, status)
    """
    return client.maestro.run_and_wait(timeout=timeout)


def read_simulation_output_csv(
    client: Any,
    run_directory: str,
    current_test_output: str,
    local_dir: Optional[Path] = None,
) -> Path:
    client.execute_skill("maeExportOutputView()")
    if local_dir is None:
        local_dir = Path.cwd()
    parts = current_test_output.split(":")
    lib_name = parts[0][2:] if parts and len(parts) > 0 else "unknown"
    cell_name = parts[1] if len(parts) > 1 else "unknown"
    filename = f"outputs_{lib_name}_{cell_name}_maestro.csv"
    local_path = local_dir / filename
    remote_path = Path(run_directory) / filename
    client.download_file(str(remote_path), str(local_path))
    return local_path


def extract_objectives_from_output_csv(df: pd.DataFrame, n_obj: int) -> np.ndarray:
    if "Value" in df.columns:
        values = [parse_output_value(v) for v in df["Value"].tolist()]
        values = [v for v in values if v is not None]
        if len(values) >= n_obj:
            return np.array(values[:n_obj], dtype=float)

    if "Result" in df.columns:
        values = [parse_output_value(v) for v in df["Result"].tolist()]
        values = [v for v in values if v is not None]
        if len(values) >= n_obj:
            return np.array(values[:n_obj], dtype=float)

    if "Output" in df.columns and "Type" in df.columns:
        expr_df = df[df["Type"] == "expr"]
        values = [parse_output_value(v) for v in expr_df["Output"].tolist()]
        values = [v for v in values if v is not None]
        if len(values) >= n_obj:
            return np.array(values[:n_obj], dtype=float)

    return np.full(n_obj, 1e9, dtype=float)


def evaluate_candidate(
    client: Any,
    var_names: List[str],
    x: np.ndarray,
    run_directory: str,
    current_test_output: str,
    csv_path: Optional[Path] = None,
    dry_run: bool = False,
    n_obj: int = 1,
) -> np.ndarray:
    if dry_run:
        if csv_path is not None and csv_path.exists():
            df = pd.read_csv(csv_path)
            values = extract_objectives_from_output_csv(df, n_obj)
            if np.all(values < 1e9):
                return values

        norm_val = float(np.linalg.norm(x))
        fake_obj = np.full(n_obj, norm_val, dtype=float)
        fake_obj[: min(n_obj, x.size)] = np.abs(x[: min(n_obj, x.size)])
        return fake_obj

    for name, val in zip(var_names, x.tolist()):
        mae_set_var(client, name, float(val))

    run_simulation_and_wait(client)
    out_csv = read_simulation_output_csv(client, run_directory, current_test_output)
    df = pd.read_csv(out_csv)
    return extract_objectives_from_output_csv(df, n_obj)


# ── Optimization callback (per-generation logging) ──────────────────────────


class OptimizationLogger:
    """Logs per-generation variable values and objective values during optimization.

    Usage (pymoo 0.6.x)::

        logger = OptimizationLogger(var_names, obj_names)
        algorithm = NSGA2(pop_size=..., callback=logger)
        minimize(problem, algorithm, ...)

    After optimization, ``logger.data`` contains per-generation history
    for plotting.
    """

    def __init__(self, var_names: List[str], obj_names: List[str]):
        self.var_names = var_names
        self.obj_names = obj_names
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
        if not self.is_initialized:
            self.is_initialized = True
        self._log(algorithm)

    def _log(self, algorithm: Any) -> None:
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

        # Terminal display
        print(f"\n{'='*60}")
        print(f"  Generation {gen}  |  Evaluations: {algorithm.evaluator.n_eval}")
        print(f"{'='*60}")
        print("  Variables:")
        for i, name in enumerate(self.var_names):
            print(f"    {name}: {best_X[i]:.6e}")
        print("  Objectives:")
        for i, name in enumerate(self.obj_names):
            print(f"    {name}: {best_F[i]:.6e}")
        print(f"  Best sum: {best_F.sum():.6e}")


# ── Visualization ────────────────────────────────────────────────────────────


def plot_optimization_results(
    logger: OptimizationLogger,
    obj_names: List[str],
    save_dir: str = ".",
    show: bool = True,
) -> None:
    """Generate and optionally display convergence / parameter / Pareto plots.

    Creates:
        - ``<save_dir>/convergence.png`` — objective convergence + parameter evolution
        - ``<save_dir>/pareto.png`` — Pareto front (multi-objective only)

    Args:
        logger: OptimizationLogger with per-generation data.
        obj_names: Names of objective functions.
        save_dir: Directory to save plots (created if missing).
        show: If True, display plots interactively via ``plt.show()``.
    """
    import matplotlib
    matplotlib.use("TkAgg")  # interactive backend for Windows display
    import matplotlib.pyplot as plt

    data = logger.data
    save_path = Path(save_dir)
    save_path.mkdir(parents=True, exist_ok=True)

    # ── 1. Convergence + Parameter evolution ──
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # 1a. Objective convergence
    ax = axes[0]
    for i, name in enumerate(obj_names):
        values = [f[i] for f in data["best_F"]]
        ax.plot(data["n_gen"], values, marker="o", label=name)
    ax.set_xlabel("Generation")
    ax.set_ylabel("Objective Value")
    ax.set_title("Objective Convergence")
    ax.legend()
    ax.grid(True)

    # 1b. Parameter evolution
    ax = axes[1]
    for i, name in enumerate(logger.var_names):
        values = [x[i] for x in data["best_X"]]
        ax.plot(data["n_gen"], values, marker="o", label=name)
    ax.set_xlabel("Generation")
    ax.set_ylabel("Variable Value")
    ax.set_title("Parameter Evolution")
    ax.legend()
    ax.grid(True)

    plt.tight_layout()
    plt.savefig(str(save_path / "convergence.png"), dpi=150)
    print(f"  [plot] saved → {save_path / 'convergence.png'}")

    # ── 2. Pareto front (multi-objective only) ──
    if len(obj_names) >= 2:
        try:
            _plot_pareto(data, obj_names, save_path, logger)
        except Exception as exc:
            print(f"  [plot] Pareto front skipped — {type(exc).__name__}: {exc}")

    # ── Display on screen ──
    if show:
        print("  [plot] displaying on screen (close all windows to continue)...")
        plt.show()
    else:
        plt.close("all")


def _plot_pareto(
    data: dict,
    obj_names: List[str],
    save_path: Path,
    logger: OptimizationLogger,
) -> None:
    """Generate Pareto front plot (2D or 3D)."""
    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt

    if not data["all_F"]:
        print("  [plot] no Pareto data to plot")
        return

    fig = plt.figure(figsize=(9, 7))
    F_all = np.concatenate(data["all_F"], axis=0)
    n_obj = len(obj_names)

    if n_obj == 2:
        ax = fig.add_subplot(111)
        if len(F_all) > 0:
            ax.scatter(F_all[:, 0], F_all[:, 1], alpha=0.15, label="All evaluated")
        F_last = data["all_F"][-1]
        ax.scatter(F_last[:, 0], F_last[:, 1], color="red", s=40, label=f"Gen {data['n_gen'][-1]}")
        ax.set_xlabel(obj_names[0])
        ax.set_ylabel(obj_names[1])
        ax.set_title("Pareto Front")
        ax.legend()
        ax.grid(True)
    elif n_obj >= 3:
        try:
            ax = fig.add_subplot(111, projection="3d")
            if len(F_all) > 0:
                ax.scatter(F_all[:, 0], F_all[:, 1], F_all[:, 2], alpha=0.15)
            F_last = data["all_F"][-1]
            ax.scatter(F_last[:, 0], F_last[:, 1], F_last[:, 2], color="red", s=40)
            ax.set_xlabel(obj_names[0])
            ax.set_ylabel(obj_names[1])
            ax.set_zlabel(obj_names[2])
            ax.set_title("Pareto Front")
        except Exception as exc:
            print(f"  [plot] 3D Pareto not available ({exc}), falling back to 2D scatter matrix")
            plt.close(fig)
            _plot_pareto_2d_matrix(data, obj_names, save_path)
            return

    plt.tight_layout()
    plt.savefig(str(save_path / "pareto.png"), dpi=150)
    print(f"  [plot] saved → {save_path / 'pareto.png'}")


def _plot_pareto_2d_matrix(
    data: dict,
    obj_names: List[str],
    save_path: Path,
) -> None:
    """Fallback: pairwise 2D scatter matrix for multi-objective Pareto."""
    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt

    n = len(obj_names)
    F_all = np.concatenate(data["all_F"], axis=0)

    fig, axes = plt.subplots(n, n, figsize=(4 * n, 4 * n))
    for i in range(n):
        for j in range(n):
            ax = axes[i, j] if n > 1 else axes
            if i == j:
                ax.hist(F_all[:, i], bins=20, alpha=0.5)
                ax.set_xlabel(obj_names[i])
                ax.set_ylabel("Count")
            else:
                ax.scatter(F_all[:, j], F_all[:, i], alpha=0.15, s=5)
                ax.set_xlabel(obj_names[j])
                ax.set_ylabel(obj_names[i])
            ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(str(save_path / "pareto.png"), dpi=150)
    print(f"  [plot] saved → {save_path / 'pareto.png'} (2D scatter matrix)")


def run_optimization_loop(
    run_directory: str = ".",
    csv_filename: Optional[str] = None,
    generations: int = 50,
    pop_size: int = 50,
    dry_run: bool = True,
    seed: int = 1,
    local_download_dir: Optional[Path] = None,
    verbose: bool = False,
    plot: bool = True,
    plot_dir: str = ".",
    show: bool = True,
) -> Any:
    from pymoo.algorithms.moo.nsga2 import NSGA2
    from pymoo.core.problem import Problem
    from pymoo.optimize import minimize
    from pymoo.termination import get_termination

    VirtuosoClientClass = _get_virtuoso_client_class()
    client = VirtuosoClientClass.from_env()
    current_test = get_current_test_name(client)

    var_names, vals, mins, maxs = fetch_variables(client)
    # Validate all bounds before starting optimization
    for n, v, lo, hi in zip(var_names, vals.tolist(), mins.tolist(), maxs.tolist()):
        validate_variable_bounds(n, float(v), float(lo), float(hi))

    xl = np.minimum(mins, maxs)
    xu = np.maximum(mins, maxs)

    if csv_filename is None:
        names, weights, specs, csv_path = download_and_parse_specs(
            client, run_directory, current_test, local_dir=local_download_dir
        )
    else:
        csv_path = Path(csv_filename)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
        names, weights, specs = read_specs_from_csv(csv_path)

    n_obj = max(1, len(names))

    # Per-generation logging
    obj_names = names
    logger = OptimizationLogger(var_names, obj_names)

    class VirtuosoProblem(Problem):
        def __init__(self) -> None:
            super().__init__(n_var=len(var_names), n_obj=n_obj, n_constr=0, xl=xl, xu=xu)
            self.client = client
            self.var_names = var_names
            self.run_directory = run_directory
            self.current_test_output = current_test
            self.csv_path = csv_path
            self.dry_run = dry_run

        def _evaluate(self, x, out, *args, **kwargs) -> None:
            n = x.shape[0]
            F = np.zeros((n, self.n_obj))
            for i in range(n):
                try:
                    vals = evaluate_candidate(
                        self.client,
                        self.var_names,
                        x[i, :],
                        self.run_directory,
                        self.current_test_output,
                        csv_path=self.csv_path,
                        dry_run=self.dry_run,
                        n_obj=self.n_obj,
                    )
                except Exception:
                    print("Error evaluating candidate:", i)
                    print("candidate x:", x[i, :])
                    print("dry_run:", self.dry_run)
                    raise

                if vals is None:
                    raise ValueError("evaluate_candidate returned None")
                vals = np.asarray(vals, dtype=float)
                if vals.ndim != 1:
                    raise ValueError(f"Objective vector must be 1D, got shape {vals.shape}")
                if vals.size < self.n_obj:
                    arr = np.ones(self.n_obj, dtype=float) * 1e9
                    arr[: vals.size] = vals
                    F[i, :] = arr
                else:
                    F[i, :] = vals[: self.n_obj]
            out["F"] = F

    problem = VirtuosoProblem()
    algorithm = NSGA2(pop_size=pop_size, callback=logger)
    termination = get_termination("n_gen", generations)

    if verbose:
        print("run_optimization_loop: n_obj=", n_obj, "pop_size=", pop_size, "generations=", generations, "dry_run=", dry_run)
        print("variables=", var_names)
        print("lower bounds=", xl)
        print("upper bounds=", xu)
        print("specs=", specs)

    res = minimize(problem, algorithm, termination, seed=seed, verbose=verbose,
                   copy_algorithm=False)
    logger.data["n_gen"] = logger.data["n_gen"]  # ensure latest
    res.callback_data = logger.data

    # Generate plots (default on)
    if plot:
        try:
            plot_optimization_results(logger, obj_names, save_dir=plot_dir, show=show)
        except Exception as exc:
            print(f"  [plot] warning: failed to generate plots — {exc}")

    return res


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Virtuoso <-> pymoo optimization.")
    parser.add_argument("--run-directory", default=".", help="Remote Virtuoso run directory")
    parser.add_argument("--csv-filename", default=None, help="Local CSV file to use instead of downloading")
    parser.add_argument("--generations", type=int, default=10, help="Number of optimization generations")
    parser.add_argument("--population", type=int, default=20, help="Population size")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", default=True, help="Run in dry-run mode (no real simulation)")
    parser.add_argument("--real-run", dest="dry_run", action="store_false", help="Run actual Virtuoso simulation")
    parser.add_argument("--download-dir", default=None, help="Local directory for downloaded CSV files")
    parser.add_argument("--seed", type=int, default=1, help="Random seed")
    parser.add_argument("--quiet", action="store_true", help="Suppress verbose output")
    parser.add_argument("--no-plot", dest="plot", action="store_false", help="Disable visualization plots (default: on)")
    parser.set_defaults(plot=True)
    parser.add_argument("--plot-dir", default=".", help="Directory to save plot images")
    args = parser.parse_args()

    download_dir = Path(args.download_dir).expanduser() if args.download_dir else None
    res = run_optimization_loop(
        run_directory=args.run_directory,
        csv_filename=args.csv_filename,
        generations=args.generations,
        pop_size=args.population,
        dry_run=args.dry_run,
        seed=args.seed,
        local_download_dir=download_dir,
        verbose=not args.quiet,
        plot=args.plot,
        plot_dir=args.plot_dir,
    )

    print("Optimization finished")
    if hasattr(res, "X") and res.X is not None:
        print("Pareto count:", len(res.X))
        print("Pareto objectives shape:", res.F.shape if hasattr(res, "F") else "N/A")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())