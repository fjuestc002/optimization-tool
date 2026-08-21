"""Optimization harness connecting Virtuoso <-> pymoo.

This module provides a consolidated workflow for:
  - reading optimization variables from Virtuoso,
  - downloading and parsing Maestro CSV outputs,
  - running a pymoo optimization loop,
  - writing variable candidates back to Virtuoso,
  - running simulation and collecting objective values.
"""

from __future__ import annotations

import os
import argparse
import re
from pathlib import Path
from typing import Any, List, Optional, Tuple

import numpy as np
import pandas as pd

from optimization_tool.optimizers import (
    list_optimizers,
    optimize as unified_optimize,
    validate_algorithm,
)
from optimization_tool.optimizers.registry import OPTIMIZER_REGISTRY
from optimization_tool.optimizers.pymoo_adapter import _create_pymoo_algorithm
from optimization_tool.optimizers.base import OptimizerResult
from optimization_tool.project import ProjectRun

VirtuosoClient = None


# ── Algorithm registry (re-exported from optimizers package) ──────────────────

# Kept as a reference for backward compatibility; the authoritative registry
# is in optimization_tool.optimizers.registry.OPTIMIZER_REGISTRY.
ALGORITHM_REGISTRY: dict[str, dict] = {k: v for k, v in OPTIMIZER_REGISTRY.items() if v["type"] == "pymoo"}


def _get_algorithm_category(n_obj: int) -> str:
    """Map number of objectives to algorithm category."""
    if n_obj == 1:
        return "single"
    elif n_obj <= 3:
        return "multi"
    else:
        return "many"


def _get_algorithms_for_problem(n_obj: int) -> list[str]:
    """List pymoo algorithm names suitable for a problem with n_obj objectives."""
    category = _get_algorithm_category(n_obj)
    return sorted(name for name, info in ALGORITHM_REGISTRY.items()
                  if category in info.get("categories", []))


def _validate_algorithm(name: str, n_obj: int) -> None:
    """Validate that an algorithm is suitable for the given number of objectives.

    Delegates to the shared validator in the optimizers package.
    """
    validate_algorithm(name, n_obj)


def _create_algorithm(
    name: str,
    pop_size: int,
    n_obj: int,
    callback: Any,
    xl: Optional[np.ndarray] = None,
    xu: Optional[np.ndarray] = None,
) -> Any:
    """Create a pymoo algorithm instance by name.

    Delegates to the shared factory in the optimizers package.
    """
    return _create_pymoo_algorithm(name, pop_size, n_obj, callback, xl=xl, xu=xu)


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
    """Convert a Virtuoso value string (with optional SI suffix) to a float.

    Supports SPICE suffixes: f (1e-15), p (1e-12), n (1e-9), u (1e-6),
    m (1e-3), k (1e3), meg (1e6), M (1e6), g (1e9).
    """
    text = text.strip()
    if not text:
        return 0.0

    # Try direct float conversion first (handles "1e-9", "0.5", etc.)
    try:
        return float(text)
    except ValueError:
        pass

    # Match number + optional alphabetic suffix
    m = re.match(r'([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)\s*([a-zA-Z]+)', text)
    if m:
        num = float(m.group(1))
        suffix = m.group(2)  # case-sensitive: "M" != "m"
        multiplier = {
            'f': 1e-15, 'p': 1e-12, 'n': 1e-9, 'u': 1e-6,'G': 1e9,
            'm': 1e-3, 'k': 1e3, 'meg': 1e6, 'M': 1e6, 'g': 1e9,
        }.get(suffix)
        if multiplier is not None:
            return num * multiplier

    raise ValueError(f"Cannot normalize value: {text}")


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

    # 2. Range — between {From/To} or {Center/Span} tags
    #    From/To: {From/To}Auto:from_value:steps:to_value{From/To}
    #    Center/Span: {Center/Span}Auto:center:steps:span{Center/Span}
    m_from_to = re.search(r"\{From/To\}([^}]+)\{From/To\}", info)
    m_center_span = re.search(r"\{Center/Span\}([^}]+)\{Center/Span\}", info)

    var_min = 0.0
    var_max = 0.0

    if m_from_to:
        parts = m_from_to.group(1).split(":")
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

    elif m_center_span:
        # Center/Span mode: Auto:center:steps:span
        parts = m_center_span.group(1).split(":")
        if len(parts) >= 4:
            try:
                center = normalize_value(parts[1])
                span = normalize_value(parts[3])
                var_min = center - span / 2.0
                var_max = center + span / 2.0
            except Exception:
                pass
        elif len(parts) >= 3:
            try:
                center = normalize_value(parts[1])
                span = normalize_value(parts[2])
                var_min = center - span / 2.0
                var_max = center + span / 2.0
            except Exception:
                pass

    # Safety: ensure min <= max even if Virtuoso returns them reversed
    if var_min > var_max:
        var_min, var_max = var_max, var_min

    # Clamp negative bounds to 0 (Center/Span may produce negative From)
    if var_min < 0.0:
        var_min = 0.0

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
    if var_min < 0.0 or var_max <= 0.0:
        raise VariableBoundsError(
            f"Variable '{name}' has invalid range: min={var_min}, max={var_max}. "
            "Both bounds must be non-negative (max > 0)."
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
    return result.output.strip()


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
    filename = f"outputs_{lib_name}_{cell_name}_maestro_setup.csv"
    local_path = local_dir / filename
    remote_path = Path(run_directory) / filename
#    remote_path = run_directory / filename
#    remote_path = f"/home/colon/Desktop/project1010drv/{filename}"
    print(f"[DEBUG_path_1.1] remote_path = {Path(run_directory)}")
    print(f"[DEBUG_path_1.2] remote_path = {remote_path}")

    if os.path.exists(local_path):
        os.remove(local_path)
        print("[DEBUG]文件已成功删除, for read new spec")
    client.download_file(remote_path.as_posix(), str(local_path))
    print(str(remote_path), str(local_path))
    df = pd.read_csv(local_path)
    print(df["Spec"])
 #   expr_df = df[df["Type"] == "expr"]
 #   expr_df = df[(df["Type"] == "expr") & (df["Spec"].notna()) & (df["Spec"] != " ")]
    expr_df = df[
        (df["Type"] == "expr") &
        (df["Spec"].notna()) &
        (df["Spec"].str.strip() != "")
    ]
    print(expr_df)
    names = expr_df["Name"].astype(str).tolist()
    weights = expr_df["Weight"].astype(float).to_numpy()
    specs = expr_df["Spec"].astype(str).tolist()
    return names, weights, specs, local_path


def read_specs_from_csv(path: Path) -> tuple[List[str], np.ndarray, List[str]]:
    df = pd.read_csv(path)
    expr_df = df[
        (df["Type"] == "expr") &
        (df["Spec"].notna()) &
        (df["Spec"].str.strip() != "")
        ]
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
    """Run simulation and wait for completion using Maestro callback-based approach.

    Uses client.maestro.run_and_wait() which registers a SKILL callback
    that writes a marker file when done. Python polls the marker via SSH
    every 2 seconds, keeping the SKILL channel free during the wait.

    Detects ADE Explorer and gives a clear error — this tool requires Maestro.

    Args:
        client: VirtuosoClient instance
        timeout: Max wait time in seconds (default 600s = 10 minutes)

    Returns:
        tuple (history, status)
    """
    _check_not_explorer(client)
    return client.maestro.run_and_wait(timeout=timeout)


def _check_not_explorer(client: Any) -> None:
    """Check the current window is ADE Maestro, not Explorer."""
    try:
        result = client.execute_skill(
            'let((s) s = car(errset(sevSession(hiGetCurrentWindow()))) if(s then "t" else "nil"))'
        )
        if result.output.strip().strip('"') == "t":
            raise RuntimeError(
                "检测到 ADE Explorer 窗口。本工具需要 ADE Maestro。\n"
                "请在 Maestro 中创建或打开 testbench，然后重试。\n"
                "提示: 在 Library Manager 中可以用 File → New → Cell View →\n"
                "Maestro 创建 Maestro view，或者用 ADE Explorer 的\n"
                "Session → Migrate to Maestro 迁移现有测试。"
            )
    except RuntimeError:
        raise
    except Exception:
        pass  # Best-effort check; proceed if detection fails


def read_simulation_output_csv(
    client: Any,
    run_directory: str,
    current_test_output: str,
    local_dir: Optional[Path] = None,
) -> pd.DataFrame:   # 返回 DataFrame，而不是 Path
    if local_dir is None:
        local_dir = Path.cwd()
    parts = current_test_output.split(":")
    lib_name = parts[0][2:] if parts and len(parts) > 0 else "unknown"
    cell_name = parts[1] if len(parts) > 1 else "unknown"
    filename = f"outputs_{lib_name}_{cell_name}_maestro.csv"
    local_path = local_dir / filename
    remote_path = Path(run_directory) / filename
#    remote_path = f"/home/colon/Desktop/project1010drv/{filename}"
    print(f"[DEBUG_path_2.1] remote_path = {Path(run_directory)}")
    print(f"[DEBUG_path_2.2] remote_path = {remote_path}")
    # 使用 as_posix() 确保 SKILL 命令中的路径使用正斜杠，避免反斜杠被 SKILL 转义
    client.maestro.export_output_view(remote_path.as_posix())
    client.download_file(remote_path.as_posix(), str(local_path))

    # 自动检测表头行
    header_row = find_header_row(local_path)
    print(f"[INFO] 检测到结果CSV表头在第 {header_row} 行")

    # 读取 CSV，跳过元数据行
    df = pd.read_csv(local_path, skiprows=header_row)
    # 统一列名为小写，去除首尾空格
    df.columns = df.columns.str.strip().str.lower()
    print(f"[INFO] 列名（小写）: {df.columns.tolist()}")

    return df   # 返回 DataFrame


def extract_objectives_from_output_csv(df: pd.DataFrame, n_obj: int, specs: Optional[List[str]] = None) -> np.ndarray:
    df.columns = df.columns.str.strip().str.lower()
    print(f"[DEBUG] n_obj={n_obj}, specs={specs}")
    print(f"[DEBUG] columns: {df.columns.tolist()}")
    if "spec" in df.columns:
        mask = df["spec"].notna() & (df["spec"].astype(str).str.strip() != "")
        valid_rows = df[mask]
        print(f"[DEBUG] valid_rows length={len(valid_rows)}")
        print(f"[DEBUG] valid_rows head:\n{valid_rows[['test','spec','min','max']].head()}")
        if len(valid_rows) >= n_obj:
            spec_list = specs if (specs is not None and len(specs)>=n_obj) else valid_rows["spec"].iloc[:n_obj].astype(str).tolist()
            print(f"[DEBUG] spec_list={spec_list}")
            col_to_use = []
            directions = []  # -1 = 要最大化(>类spec, 需取反), +1 = 要最小化(<类spec)
            for s in spec_list:
                s = s.strip()
                if s.startswith('>') or s.startswith('≥'):
                    col_to_use.append("min")
                    directions.append(-1)
                elif s.startswith('<') or s.startswith('≤'):
                    col_to_use.append("max")
                    directions.append(+1)
                else:
                    col_to_use.append("min")
                    directions.append(+1)
            print(f"[DEBUG] col_to_use={col_to_use}")
            print(f"[DEBUG] directions={directions}  # -1=最大化(取反后pymoo最小化), +1=最小化(原值)")
            corrected_vals = []
            for i in range(n_obj):
                col = col_to_use[i]
                if col in df.columns:
                    val = valid_rows[col].iloc[i]
                    parsed = parse_output_value(val)
                    print(f"[DEBUG] i={i}, col={col}, raw='{val}', parsed={parsed}")
                    if parsed is not None:
                        # 方向修正：pymoo 默认最小化，对 > 类 spec 取反以实现最大化
                        corrected = parsed * directions[i]
                        print(f"[DEBUG]   → direction={directions[i]}, corrected={corrected}")
                        corrected_vals.append(corrected)
                    else:
                        corrected_vals.append(1e9)
                else:
                    print(f"[DEBUG] col {col} not in columns!")
                    corrected_vals.append(1e9)
            print(f"[DEBUG] corrected_vals={corrected_vals}")
            if not any(v >= 1e9 for v in corrected_vals):
                # 归一化：按 spec 阈值做参考，使各目标量级一致
                normalized = _normalize_objectives(corrected_vals, spec_list, directions)
                print(f"[DEBUG] normalized={normalized}")
                return np.array(normalized, dtype=float)
            else:
                print("[DEBUG] some values are 1e9, will fallback to penalty")
        else:
            print("[DEBUG] valid_rows count < n_obj")
    else:
        print("[DEBUG] 'spec' column not found")

    print("[DEBUG] returning penalty 1e9")
    return np.full(n_obj, 1e9, dtype=float)


def _extract_spec_threshold(spec_str: str) -> Optional[float]:
    """从 spec 字符串（如 '> 60', '< 300p'）中提取数值阈值。"""
    s = spec_str.strip().lstrip('>≥<≤ ')
    try:
        return normalize_value(s)
    except Exception:
        return None


def _normalize_objectives(values: List[float], specs: List[str], directions: List[int]) -> List[float]:
    """归一化目标值，使各目标量级一致且 0 表示刚好达标。

    对于 > 类 spec（要最大化）：obj = (threshold - raw) / |threshold|
    对于 < 类 spec（要最小化）：obj = (raw - threshold) / |threshold|

    结果：0 = 刚好达标，负值 = 超出指标（更好），正值 = 违规（更差）。
    """
    normalized = []
    for val, spec_str, d in zip(values, specs, directions):
        raw_val = val * d  # 还原原始值（因为 val = raw * direction）
        threshold = _extract_spec_threshold(spec_str)
        if threshold is not None and abs(threshold) > 1e-30:
            if d == -1:  # > 类：要最大化
                obj = (threshold - raw_val) / abs(threshold)
            else:          # < 类：要最小化
                obj = (raw_val - threshold) / abs(threshold)
            normalized.append(obj)
        else:
            # 无法提取阈值，返回已修正方向的值
            normalized.append(val)
    return normalized


def evaluate_candidate(
    client: Any,
    var_names: List[str],
    x: np.ndarray,
    run_directory: str,
    current_test_output: str,
    csv_path: Optional[Path] = None,
    dry_run: bool = False,
    n_obj: int = 1,
    specs: Optional[List[str]] = None,     # 新增

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
 #   out_csv = read_simulation_output_csv(client, run_directory, current_test_output)
#   print(f"out {out_csv}")
#    df = pd.read_csv(out_csv)
    df = read_simulation_output_csv(client, run_directory, current_test_output)
    print(f"df  {df}")
    return extract_objectives_from_output_csv(df, n_obj, specs)
#    return extract_objectives_from_output_csv(df, n_obj, specs)


def find_header_row(file_path: Path) -> int:
    with open(file_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            # 检测包含关键列名的行（可根据实际情况调整）
            if 'Test' in line and 'Output' in line and 'Spec' in line and 'Weight' in line:
                return i
    return 0

# ── Optimization callback (per-generation logging) ──────────────────────────



class OptimizationLogger:
    """Logs per-generation variable values and objective values during optimization.

    Usage (pymoo 0.6.x)::

        logger = OptimizationLogger(var_names, obj_names)
        algorithm = NSGA2(pop_size=..., callback=logger)
        minimize(problem, algorithm, ...)

    After optimization, ``logger.data`` contains per-generation history
    for plotting.

    Parameters
    ----------
    var_names: Names of decision variables.
    obj_names: Names of objective functions.
    progress_callback: Optional callable invoked each generation with
        ``(gen, n_eval, best_X, best_F, all_X, all_F)`` for real-time
        progress reporting (e.g. GUI signal emission).
    """

    def __init__(
        self,
        var_names: List[str],
        obj_names: List[str],
        progress_callback: Optional[callable] = None,
    ):
        self.var_names = var_names
        self.obj_names = obj_names
        self.progress_callback = progress_callback
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
        print(f"[DEBUG_2] best_idx= {best_idx};;best_F={best_F}")

        self.data["n_gen"].append(gen)
        self.data["n_eval"].append(algorithm.evaluator.n_eval)
        self.data["best_X"].append(best_X.copy())
        self.data["best_F"].append(best_F.copy())
        self.data["all_X"].append(X.copy())
        self.data["all_F"].append(F.copy())
        print(f"[DEBUG_3] self.data  {self.data["all_F"]}")


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

        # Real-time progress callback (for GUI / worker)
        if self.progress_callback is not None:
            self.progress_callback(
                gen=gen,
                n_eval=algorithm.evaluator.n_eval,
                best_X=best_X,
                best_F=best_F,
                all_X=X,
                all_F=F,
                obj_names=self.obj_names,
            )


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

    # CJK font support
    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei", "SimHei", "DengXian", "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False

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

###########################################################################################
#       real done
#
##########################################################################################

def run_optimization_loop(
    run_directory: str = ".",
    csv_filename: Optional[str] = None,
    generations: int = 10,
    pop_size: int = 5,
    dry_run: bool = True,
    seed: int = 1,
    local_download_dir: Optional[Path] = None,
    verbose: bool = False,
    plot: bool = True,
    plot_dir: str = ".",
    show: bool = True,
    algo: str = "nsga2",
    project_dir: Optional[str] = None,
    progress_callback: Optional[callable] = None,
) -> Any:
    from pymoo.core.problem import Problem

    VirtuosoClientClass = _get_virtuoso_client_class()
    print(f"[DEBUG] Using VirtuosoClientClass: {VirtuosoClientClass}")
    client = VirtuosoClientClass.from_env()
    print(f"[DEBUG] client: {client}")
    current_test = get_current_test_name(client)
    print(f"[DEBUG] current_test: {current_test}")
#    runDIR=client.execute_skill("getWorkingDir() ")
#    run_directory=runDIR.output.strip()
    runDIR = client.execute_skill("getWorkingDir()")
    run_directory = runDIR.output.strip().strip('"')   # 关键修改：去掉引号
    print(f"[DEBUG] run_directory (cleaned): {run_directory}")
#    print(f"[DEBUG] run_directory: {run_directory}")
    var_names, vals, mins, maxs = fetch_variables(client)
    # Validate all bounds before starting optimization
    for n, v, lo, hi in zip(var_names, vals.tolist(), mins.tolist(), maxs.tolist()):
        validate_variable_bounds(n, float(v), float(lo), float(hi))

    xl = np.minimum(mins, maxs)
    xu = np.maximum(mins, maxs)

#    if csv_filename is None:
    names, weights, specs, csv_path = download_and_parse_specs(
        client, run_directory, current_test, local_dir=local_download_dir
        )
#    else:
#        csv_path = Path(csv_filename)
#        if not csv_path.exists():
#            raise FileNotFoundError(f"CSV file not found: {csv_path}")
    names, weights, specs = read_specs_from_csv(csv_path)

    n_obj = max(1, len(names))

    # Per-generation logging
    obj_names = names
    logger = OptimizationLogger(var_names, obj_names, progress_callback=progress_callback)

    # Initialize project run (if --project-dir specified)
    project_run = None
    if project_dir:
        project_run = ProjectRun.create(project_dir)
        project_run.save_config(
            variables=var_names,
            objectives=obj_names,
            algo=algo,
            generations=generations,
            pop_size=pop_size,
            dry_run=dry_run,
            seed=seed,
        )
        project_run.save_variables_csv(var_names, vals.tolist(), mins.tolist(), maxs.tolist())
        project_run.save_specs_csv(names, weights.tolist(), specs)
        print(f"  [project] artifacts → {project_run.dir}")

    class VirtuosoProblem(Problem):
        def __init__(self, stop_event=None, specs=None) -> None:   # 新增 specs 参数
            
            # 2 inequality constraints per variable: x >= xl and x <= xu
            super().__init__(
                n_var=len(var_names), 
                n_obj=n_obj, 
                n_constr=2 * len(var_names), 
                xl=xl, 
                xu=xu
                )
            self.client = client
            self.var_names = var_names
            self.run_directory = run_directory
            self.current_test_output = current_test
            self.csv_path = csv_path
            self.dry_run = dry_run
            self.stop_event = stop_event
            self.specs = specs if specs is not None else []   # 保存 specs

        def _evaluate(self, x, out, *args, **kwargs) -> None:
            n = x.shape[0]
            F = np.zeros((n, self.n_obj))
            G = np.zeros((n, 2 * self.n_var))
            for i in range(n):
                # Check abort signal between each evaluation (faster stop)
                if self.stop_event and self.stop_event():
                    raise KeyboardInterrupt("优化已中止")
                # Variable bounds constraints (G <= 0 means feasible)
                for j in range(self.n_var):
                    G[i, 2 * j] = self.xl[j] - x[i, j]       # violated if x[j] < xl[j]
                    G[i, 2 * j + 1] = x[i, j] - self.xu[j]   # violated if x[j] > xu[j]
                #
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
                        specs=self.specs,   # 新增这一行
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
            out["G"] = G

    problem = VirtuosoProblem(specs=specs)
    # Validate and run via unified optimizer (pymoo or Bayesian)
    res = unified_optimize(
        problem,
        algo,
        termination=("n_gen", generations),
        pop_size=pop_size,
        n_obj=n_obj,
        seed=seed,
        verbose=verbose,
        callback=logger,
        xl=xl,
        xu=xu,
    )

    # Ensure callback_data is populated (for plotting / archiving)
    if not hasattr(res, 'callback_data') or not res.callback_data:
        res.callback_data = logger.data

    # Always include var_names / obj_names / specs for the GUI results table
    if res.callback_data:
        res.callback_data["var_names"] = var_names
        res.callback_data["obj_names"] = obj_names
        res.callback_data["specs"] = specs

    # Generate plots (default on)
    if plot:
        try:
            plot_optimization_results(logger, obj_names, save_dir=plot_dir, show=show)
        except Exception as exc:
            print(f"  [plot] warning: failed to generate plots — {exc}")

    # Save project artifacts (if --project-dir specified)
    if project_run is not None:
        try:
            project_run.save_all(res, logger, var_names, obj_names)
            project_run.copy_plot(Path(plot_dir) / "convergence.png")
            project_run.copy_plot(Path(plot_dir) / "pareto.png")
            print(f"  [project] results saved → {project_run.dir}")
        except Exception as exc:
            print(f"  [project] warning: failed to save artifacts — {exc}")

    return res

############################################################################################
#                     main
############################################################################################
def main() -> int:
    parser = argparse.ArgumentParser(description="Run Virtuoso <-> pymoo optimization.")
    parser.add_argument("--run-directory", default=".", help="Remote Virtuoso run directory")
    parser.add_argument("--csv-filename", default=None, help="Local CSV file to use instead of downloading")
    parser.add_argument("--generations", type=int, default=10, help="Number of optimization generations")
    parser.add_argument("--population", type=int, default=20, help="Population size")
    parser.add_argument("--algo", default="nsga2",
                        help="Optimization algorithm. See --list-algos for available options. (default: nsga2)")
    parser.add_argument("--list-algos", action="store_true",
                        help="List available algorithms by category and exit")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", default=True,
                        help="Run in dry-run mode (no real simulation)")
    parser.add_argument("--real-run", dest="dry_run", action="store_false",
                        help="Run actual Virtuoso simulation")
    parser.add_argument("--download-dir", default=None, help="Local directory for downloaded CSV files")
    parser.add_argument("--seed", type=int, default=1, help="Random seed")
    parser.add_argument("--quiet", action="store_true", help="Suppress verbose output")
    parser.add_argument("--no-plot", dest="plot", action="store_false", help="Disable visualization plots (default: on)")
    parser.set_defaults(plot=True)
    parser.add_argument("--plot-dir", default=".", help="Directory to save plot images")
    parser.add_argument("--project-dir", default=None, help="Project directory for archiving run artifacts (auto-created)")
    args = parser.parse_args()

    # Handle --list-algos (no connection needed)
    if args.list_algos:
        from optimization_tool.optimizers import list_optimizers as list_all

        print("Available optimizers:\n")
        for n_obj_desc, category in [("1 (single-objective)", "single"),
                                      ("2-3 (multi-objective)", "multi"),
                                      ("4+ (many-objective)", "many")]:
            algos = sorted(name for name, info in OPTIMIZER_REGISTRY.items()
                           if category in info.get("categories", []))
            # Show type tag
            tagged = []
            for a in algos:
                info = OPTIMIZER_REGISTRY[a]
                tag = "[pymoo]" if info["type"] == "pymoo" else "[bayes]"
                desc = info.get("description", "")
                tagged.append(f"{tag} {a}{' — ' + desc if desc else ''}")
            print(f"  n_obj={n_obj_desc}:")
            for t in tagged:
                print(f"    {t}")
            print()
        print("(Algorithm availability depends on the number of objectives in your CSV spec.)")
        return 0

    download_dir = Path(args.download_dir).expanduser() if args.download_dir else None
    project_dir = args.project_dir
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
        algo=args.algo,
        project_dir=project_dir,
    )

    print("Optimization finished")
    if hasattr(res, "X") and res.X is not None:
        print("Pareto count:", len(res.X))
        print("Pareto objectives shape:", res.F.shape if hasattr(res, "F") else "N/A")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
