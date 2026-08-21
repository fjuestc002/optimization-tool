import csv
from pathlib import Path
import numpy as np
import pytest

from optimization_tool.optimization import (
    normalize_value,
    parse_output_value,
    _parse_var_info,
    validate_variable_bounds,
    VariableBoundsError,
    _get_algorithm_category,
    _get_algorithms_for_problem,
    _validate_algorithm,
    _create_algorithm,
    run_optimization_loop,
    OptimizationLogger,
)
from optimization_tool.optimizers import list_optimizers, validate_algorithm
from optimization_tool.project import ProjectRun


def test_normalize_value():
    assert normalize_value("100") == 100.0
    assert normalize_value("1.5u") == 1.5e-6
    assert normalize_value("10n") == 10e-9
    assert normalize_value("200p") == 200e-12
    assert normalize_value("50f") == 50e-15
    assert normalize_value("3.3m") == 3.3e-3
    assert normalize_value("10k") == 10e3
    assert normalize_value("1M") == 1e6
    assert normalize_value("2.4G") == 2.4e9
    assert normalize_value("1e-9") == 1e-9


def test_parse_output_value():
    assert parse_output_value(1.23) == 1.23
    assert parse_output_value("4.56e-3") == 4.56e-3
    assert parse_output_value(None) is None
    assert parse_output_value("N/A") is None
    assert parse_output_value("output = 12.34 V") == 12.34


def test_parse_var_info_from_to():
    info = "{Inclusion List}3e-07{Inclusion List}{From/To}Auto:300n:10:1u{From/To}"
    val, raw, lo, hi = _parse_var_info(info)
    assert pytest.approx(val) == 3e-7
    assert pytest.approx(lo) == 300e-9
    assert pytest.approx(hi) == 1e-6


def test_parse_var_info_center_span():
    info = "{Inclusion List}500n{Inclusion List}{Center/Span}Auto:500n:10:200n{Center/Span}"
    val, raw, lo, hi = _parse_var_info(info)
    assert pytest.approx(val) == 500e-9
    assert pytest.approx(lo) == 400e-9  # center - span/2
    assert pytest.approx(hi) == 600e-9  # center + span/2


def test_validate_variable_bounds():
    # Valid bounds
    validate_variable_bounds("w1", 500e-9, 100e-9, 1e-6)

    # Min == Max => error
    with pytest.raises(VariableBoundsError):
        validate_variable_bounds("w1", 0.0, 0.0, 0.0)

    # Min > Max => error
    with pytest.raises(VariableBoundsError):
        validate_variable_bounds("w1", 500e-9, 1e-6, 100e-9)


def test_algorithms():
    assert _get_algorithm_category(1) == "single"
    assert _get_algorithm_category(2) == "multi"
    assert _get_algorithm_category(3) == "multi"
    assert _get_algorithm_category(5) == "many"

    single_algos = _get_algorithms_for_problem(1)
    assert "ga" in single_algos or "de" in single_algos

    multi_algos = _get_algorithms_for_problem(2)
    assert "nsga2" in multi_algos

    # Test validator
    _validate_algorithm("nsga2", 2)
    with pytest.raises(ValueError):
        _validate_algorithm("unknown_algorithm_xyz", 2)


class MockResult:
    def __init__(self, output: str):
        self.output = output


class MockVirtuosoClient:
    def __init__(self):
        self._var_info = {
            "wwp": "{Inclusion List}3e-07{Inclusion List}{From/To}Auto:300n:10:1u{From/To}",
            "wwn": "{Inclusion List}3e-07{Inclusion List}{From/To}Auto:300n:10:1u{From/To}",
        }

    @classmethod
    def from_env(cls):
        return cls()

    def execute_skill(self, skill: str):
        if 'maeGetSetup(?typeName "variables"' in skill:
            return MockResult('("wwp" "wwn")')
        if "maeGetSetup()" in skill:
            return MockResult("idigital_1010:test_inv3_maestro")
        if "maeGetVar" in skill:
            name = skill.split('"')[1]
            info = self._var_info.get(name, "0.0")
            return MockResult(info)
        return MockResult("")

    def download_file(self, remote_path: str, local_path: str):
        local = Path(local_path)
        local.parent.mkdir(parents=True, exist_ok=True)
        with open(local, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Name", "Weight", "Spec", "Type", "Value"])
            writer.writerow(["Delay", "1.0", "< 300p", "expr", "1.0e-09"])
            writer.writerow(["RiseTime", "1.0", "< 900p", "expr", "2.0e-09"])


def test_dry_run_optimization(monkeypatch, tmp_path):
    import optimization_tool.optimization as opt_mod
    monkeypatch.setattr(opt_mod, "_get_virtuoso_client_class", lambda: MockVirtuosoClient)

    res = run_optimization_loop(
        dry_run=True,
        generations=2,
        pop_size=4,
        seed=42,
        verbose=False,
        plot=False,
        project_dir=str(tmp_path / "test_proj"),
    )

    assert hasattr(res, "X")
    assert res.X is not None
    assert len(res.X) > 0
    assert hasattr(res, "F")
    assert res.F is not None
    assert res.F.shape[1] == 2  # 2 objectives

    # Verify project run files created
    runs_dir = tmp_path / "test_proj" / "runs"
    assert runs_dir.exists()
    run_folders = list(runs_dir.iterdir())
    assert len(run_folders) == 1
    assert (run_folders[0] / "config.json").exists()
    assert (run_folders[0] / "results.json").exists()

