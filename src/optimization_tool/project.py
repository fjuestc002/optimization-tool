"""Project directory management for optimization runs.

Provides a project-based archive system where each project is a named
directory under a configurable root path.  All optimization artifacts
(variables, specs, algorithm configs, results, history) are stored inside
the project folder in CSV/TXT format — IC-engineer-friendly, no JSON.

Project structure::

    {run_path}/
    ├── project_A/
    │   ├── project.txt                ← metadata (key=value)
    │   ├── _circuit_info/             ← reserved for circuit data (TBD)
    │   ├── I_scripts/                 ← shared circuit info
    │   │   ├── variables.csv          ←   variable list
    │   │   └── specs.csv              ←   objective specs
    │   ├── nsga2/                     ← algorithm run (reused when config unchanged)
    │   │   ├── config.txt             ←   algorithm config
    │   │   ├── results.csv            ←   best solutions (actual values + pass/fail)
    │   │   ├── history.csv            ←   per-generation history (appended)
    │   │   ├── convergence.png
    │   │   └── pareto.png
    │   ├── nsga2_20260822_153002/     ← new folder when config changes
    │   ├── project_all_results.csv    ← consolidated Pareto solutions
    │   └── project_all_history.csv    ← consolidated history
    └── project_B/ ...
"""

from __future__ import annotations

import csv
import os
import re
import shutil
import stat
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Tuple


# NOTE: Avoid importing from optimization_tool.optimization here to prevent
# circular imports (optimization.py imports ProjectRun from this module).
# All spec-parsing helpers are defined locally.


# ── Default root path ──────────────────────────────────────────────────────

_DEFAULT_ROOT = str(Path.home() / "optimization_tool" / "projects")


# ── SI suffix parsing (local copy, independent of optimization.py) ─────────

_SI_MULTIPLIERS: dict[str, float] = {
    "f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6, "µ": 1e-6,
    "m": 1e-3, "k": 1e3, "K": 1e3, "meg": 1e6, "Meg": 1e6, "MEG": 1e6,
    "M": 1e6, "g": 1e9, "G": 1e9, "t": 1e12, "T": 1e12,
}


def _parse_si_number(text: str) -> Optional[float]:
    """Convert a string with optional SI suffix to a float.

    Handles SPICE suffixes: f, p, n, u, m, k, meg, M, g, t
    and combined units: ns, mV, MHz, GHz, kOhm, V, dB, etc.
    """
    text = text.strip()
    if not text:
        return None
    # Try direct float conversion first
    try:
        return float(text)
    except ValueError:
        pass
    # Match number + optional alphabetic/unit suffix
    m = re.match(r'([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)\s*([a-zA-Z%µ_]+)', text)
    if m:
        num = float(m.group(1))
        suffix = m.group(2)
        if suffix in _SI_MULTIPLIERS:
            return num * _SI_MULTIPLIERS[suffix]
        # Suffix with physical unit — check first character
        first_char = suffix[0]
        if first_char in ('u', 'µ'):
            return num * 1e-6
        elif first_char == 'n':
            return num * 1e-9
        elif first_char == 'p':
            return num * 1e-12
        elif first_char == 'f':
            return num * 1e-15
        elif first_char == 'm':
            return num * 1e-3
        elif first_char in ('k', 'K'):
            return num * 1e3
        elif first_char == 'M':
            return num * 1e6
        elif first_char in ('g', 'G'):
            return num * 1e9
        elif first_char in ('t', 'T'):
            return num * 1e12
        elif suffix.lower() in ('v', 'a', 's', 'hz', 'f', 'h', 'ohm',
                                 'deg', 'db', 'w', 'rad', '%'):
            return num * 1.0
    return None


def _extract_spec_threshold(spec_str: str) -> Optional[float]:
    """Extract the numeric threshold from a spec string.

    Examples: ``'< 300p'`` → 3e-10, ``'> 1.5m'`` → 0.0015
    """
    s = spec_str.strip().lstrip('>≥<≤ ')
    try:
        result = _parse_si_number(s)
        if result is not None:
            return result
        return float(s)
    except (ValueError, TypeError):
        return None


def _parse_spec_info(spec_str: str) -> Tuple[int, Optional[float]]:
    """Extract (direction, threshold) from a spec string.

    Args:
        spec_str: e.g. ``'< 300p'``, ``'> 1.5m'``, ``'≤ 100n'``

    Returns:
        (direction, threshold):
            - direction = -1 for ``>``/``≥`` (maximize),
              +1 for ``<``/``≤`` (minimize)
            - threshold as a float, or None if unparseable
    """
    s = spec_str.strip()
    if s.startswith(">") or s.startswith("≥"):
        direction = -1
    elif s.startswith("<") or s.startswith("≤"):
        direction = +1
    else:
        direction = +1
    threshold = _extract_spec_threshold(spec_str)
    return direction, threshold


def denormalize_f(normalized: float, spec_str: str) -> float:
    """Convert a normalized objective value back to the actual simulation value.

    Formulas (consistent with ``_normalize_objectives`` in ``optimization.py``):

        ``>`` spec (maximize):  norm = (threshold - raw) / threshold
                                → raw = threshold * (1 - norm)

        ``<`` spec (minimize):  norm = (raw - threshold) / threshold
                                → raw = threshold * (1 + norm)

    Args:
        normalized: Normalized objective value (from pymoo).
        spec_str: Spec string, e.g. ``'< 300p'``.

    Returns:
        Actual (de-normalized) objective value.
    """
    direction, threshold = _parse_spec_info(spec_str)
    if threshold is not None and abs(threshold) > 1e-30:
        return threshold * (1.0 + direction * normalized)
    return normalized


def check_pass_fail(actual_values: list[float], spec_strs: list[str]) -> str:
    """Determine whether a design point passes all specs.

    Each objective's actual value is compared against its spec threshold.
    Returns ``'PASS'`` only when *every* objective meets its spec.

    Args:
        actual_values: De-normalized objective values (one per spec).
        spec_strs: Spec strings, e.g. ``['< 300p', '> 1.5m']``.

    Returns:
        ``'PASS'`` or ``'FAIL'``.
    """
    for actual, spec_str in zip(actual_values, spec_strs):
        direction, threshold = _parse_spec_info(spec_str)
        if threshold is None:
            continue
        if direction < 0:  # > spec — need actual >= threshold
            if actual < threshold * 0.9999:
                return "FAIL"
        else:               # < spec — need actual <= threshold
            if actual > threshold * 1.0001:
                return "FAIL"
    return "PASS"


# ── Config comparison ──────────────────────────────────────────────────────

_CONFIG_COMPARE_KEYS = [
    "algorithm", "generations", "population", "seed", "dry_run",
]


def compare_configs(cfg_a: dict, cfg_b: dict) -> bool:
    """Compare two config dictionaries on the relevant keys.

    Only keys listed in ``_CONFIG_COMPARE_KEYS`` are compared; extra keys
    are ignored.  Values are compared as strings to tolerate type differences.

    Returns:
        ``True`` if all relevant keys match.
    """
    for key in _CONFIG_COMPARE_KEYS:
        if str(cfg_a.get(key, "")) != str(cfg_b.get(key, "")):
            return False
    return True


# ── ProjectInfo ────────────────────────────────────────────────────────────

class ProjectInfo:
    """Lightweight metadata for a project."""

    def __init__(self, name: str, path: Path, created: str = "",
                 last_opened: str = "") -> None:
        self.name = name
        self.path = path
        self.created = created
        self.last_opened = last_opened


# ── ProjectManager ─────────────────────────────────────────────────────────

class ProjectManager:
    """Manages all projects under a configurable root path.

    Usage::

        pm = ProjectManager()
        proj = pm.create_project("my_opamp")
        pm.open_project("my_opamp")
        pm.close_project()
        pm.delete_project("old_project")
        for info in pm.list_projects():
            print(info.name)
    """

    def __init__(self, root_path: str | Path | None = None) -> None:
        self.root_path = Path(root_path).resolve() if root_path \
            else Path(_DEFAULT_ROOT).resolve()
        self.root_path.mkdir(parents=True, exist_ok=True)
        self.current_project: Optional["Project"] = None
        self._recent_file = self.root_path / "_recent.txt"

    # ── Project CRUD ───────────────────────────────────────────────────────

    def list_projects(self) -> list[ProjectInfo]:
        """Scan the root path and return all valid projects."""
        projects: list[ProjectInfo] = []
        if not self.root_path.exists():
            return projects
        for entry in sorted(self.root_path.iterdir()):
            if entry.is_dir() and not entry.name.startswith("_"):
                meta = self._read_metadata(entry)
                projects.append(ProjectInfo(
                    name=entry.name,
                    path=entry,
                    created=meta.get("created", ""),
                    last_opened=meta.get("last_opened", ""),
                ))
        return projects

    def create_project(self, name: str) -> "Project":
        """Create a new project folder with initial structure.

        Raises:
            FileExistsError: If a project with the same name already exists.
            ValueError: If the name is empty or contains invalid characters.
        """
        name = name.strip()
        if not name:
            raise ValueError("Project name cannot be empty.")
        if not _is_valid_name(name):
            raise ValueError(f"Project name contains invalid characters: {name!r}")

        proj_path = self.root_path / name
        if proj_path.exists():
            raise FileExistsError(f"Project already exists: {name}")

        # Create folder structure
        proj_path.mkdir(parents=True, exist_ok=False)
        (proj_path / "I_scripts").mkdir(parents=True, exist_ok=True)
        (proj_path / "_circuit_info").mkdir(parents=True, exist_ok=True)

        # Write project metadata
        now = datetime.now().isoformat(timespec="seconds")
        self._write_metadata(proj_path, {
            "name": name,
            "created": now,
            "last_opened": now,
            "run_count": "0",
        })

        return Project(proj_path)

    def open_project(self, name: str) -> "Project":
        """Open a project by name.

        Raises:
            FileNotFoundError: If the project does not exist.
        """
        proj_path = self.root_path / name
        if not proj_path.exists() or not proj_path.is_dir():
            raise FileNotFoundError(f"Project not found: {name}")

        # Update last_opened
        now = datetime.now().isoformat(timespec="seconds")
        self._write_metadata(proj_path, {"last_opened": now, "name": name})

        # Update recent list
        self._add_recent(name)

        self.current_project = Project(proj_path)
        return self.current_project

    def close_project(self) -> None:
        """Close the current project."""
        self.current_project = None

    def delete_project(self, name: str) -> None:
        """Move the project folder to the recycle bin (soft delete).

        Uses :func:`send2trash` if available, otherwise falls back to
        ``shutil.move`` to a ``_trash/`` folder under the root path.
        """
        proj_path = self.root_path / name
        if not proj_path.exists():
            raise FileNotFoundError(f"Project not found: {name}")

        # Try send2trash; fall back to local trash folder
        try:
            import send2trash
            send2trash.send2trash(str(proj_path))
        except ImportError:
            trash_dir = self.root_path / "_trash"
            trash_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest = trash_dir / f"{name}_{timestamp}"
            shutil.move(str(proj_path), str(dest))

        # Remove from recent list
        self._remove_recent(name)

        if self.current_project and self.current_project.name == name:
            self.current_project = None

    # ── Recent projects ────────────────────────────────────────────────────

    def get_recent_projects(self) -> list[str]:
        """Return list of recently opened project names (most recent first)."""
        if not self._recent_file.exists():
            return []
        names = self._recent_file.read_text(encoding="utf-8").strip().splitlines()
        return [n for n in names if n and (self.root_path / n).exists()]

    def _add_recent(self, name: str) -> None:
        recent = self.get_recent_projects()
        if name in recent:
            recent.remove(name)
        recent.insert(0, name)
        self._recent_file.write_text(
            "\n".join(recent[:20]), encoding="utf-8"
        )

    def _remove_recent(self, name: str) -> None:
        recent = self.get_recent_projects()
        if name in recent:
            recent.remove(name)
        self._recent_file.write_text(
            "\n".join(recent[:20]), encoding="utf-8"
        )

    # ── Root path ──────────────────────────────────────────────────────────

    def set_root_path(self, path: str | Path) -> None:
        """Change the project root path."""
        self.root_path = Path(path).resolve()
        self.root_path.mkdir(parents=True, exist_ok=True)

    # ── Metadata helpers ───────────────────────────────────────────────────

    @staticmethod
    def _metadata_path(proj_path: Path) -> Path:
        return proj_path / "project.txt"

    @staticmethod
    def _read_metadata(proj_path: Path) -> dict[str, str]:
        meta_path = proj_path / "project.txt"
        meta: dict[str, str] = {}
        if meta_path.exists():
            for line in meta_path.read_text(encoding="utf-8").splitlines():
                if "=" in line:
                    key, _, val = line.partition("=")
                    meta[key.strip()] = val.strip()
        # Ensure name field
        if "name" not in meta:
            meta["name"] = proj_path.name
        return meta

    @staticmethod
    def _write_metadata(proj_path: Path, updates: dict[str, str]) -> None:
        meta = ProjectManager._read_metadata(proj_path)
        meta.update({k: v for k, v in updates.items() if v is not None})
        lines = [f"{k}={v}" for k, v in meta.items()]
        (proj_path / "project.txt").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )


# ── Project ────────────────────────────────────────────────────────────────

class Project:
    """A single optimization project — a named folder under the root path.

    Provides methods to read/write circuit scripts and manage algorithm runs.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).resolve()
        self.name = self.path.name
        self.scripts_path = self.path / "I_scripts"
        self.circuit_info_path = self.path / "_circuit_info"

    # ── Metadata ───────────────────────────────────────────────────────────

    def load_metadata(self) -> dict[str, str]:
        """Read project metadata from ``project.txt``."""
        return ProjectManager._read_metadata(self.path)

    def update_metadata(self, **updates: str) -> None:
        """Update project metadata fields."""
        ProjectManager._write_metadata(self.path, updates)

    # ── I_scripts — variables ──────────────────────────────────────────────

    def load_variables_csv(self) -> Optional[list[dict[str, float]]]:
        """Read variables from ``I_scripts/variables.csv``.

        Returns:
            List of dicts with keys ``name``, ``value``, ``min``, ``max``,
            or ``None`` if the file does not exist.
        """
        csv_path = self.scripts_path / "variables.csv"
        if not csv_path.exists():
            return None
        rows: list[dict[str, float]] = []
        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append({
                    "name": row.get("name", ""),
                    "value": float(row.get("value", 0)),
                    "min": float(row.get("min", 0)),
                    "max": float(row.get("max", 0)),
                })
        return rows

    def save_variables_csv(
        self,
        names: list[str],
        values: list[float],
        mins: list[float],
        maxs: list[float],
    ) -> Path:
        """Save variables to ``I_scripts/variables.csv``."""
        self.scripts_path.mkdir(parents=True, exist_ok=True)
        path = self.scripts_path / "variables.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["name", "value", "min", "max"])
            for n, v, lo, hi in zip(names, values, mins, maxs):
                w.writerow([n, v, lo, hi])
        return path

    # ── I_scripts — specs ──────────────────────────────────────────────────

    def load_specs_csv(self) -> Optional[list[dict[str, str]]]:
        """Read specs from ``I_scripts/specs.csv``.

        Returns:
            List of dicts with keys ``name``, ``weight``, ``spec``,
            or ``None`` if the file does not exist.
        """
        csv_path = self.scripts_path / "specs.csv"
        if not csv_path.exists():
            return None
        rows: list[dict[str, str]] = []
        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append({
                    "name": row.get("name", ""),
                    "weight": row.get("weight", "1.0"),
                    "spec": row.get("spec", ""),
                })
        return rows

    def save_specs_csv(
        self,
        names: list[str],
        weights: list[float],
        specs: list[str],
    ) -> Path:
        """Save specs to ``I_scripts/specs.csv``."""
        self.scripts_path.mkdir(parents=True, exist_ok=True)
        path = self.scripts_path / "specs.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["name", "weight", "spec"])
            for n, wt, s in zip(names, weights, specs):
                w.writerow([n, wt, s])
        return path

    # ── Algorithm run management ───────────────────────────────────────────

    def create_run(self, algo_name: str, config: dict) -> "ProjectRun":
        """Create or reuse an algorithm run folder.

        Decision logic:
          - If ``{project}/{algo_name}/`` exists **and** its config matches
            → reuse the folder (results overwritten, history appended).
          - If the folder exists but config differs
            → create ``{algo_name}_{timestamp}/``.
          - If the folder does not exist → create ``{algo_name}/``.

        Args:
            algo_name: Algorithm name, e.g. ``'nsga2'``, ``'bayes_gp'``.
            config: Configuration dict to compare/save.

        Returns:
            A :class:`ProjectRun` pointing to the target folder.
        """
        algo_dir = self.path / algo_name
        if algo_dir.exists():
            existing_cfg = ProjectRun.load_config_txt(algo_dir / "config.txt")
            if existing_cfg is not None and compare_configs(existing_cfg, config):
                return ProjectRun(self, algo_dir, reused=True)
            # Config differs → create timestamped folder
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            algo_dir = self.path / f"{algo_name}_{timestamp}"
            algo_dir.mkdir(parents=True, exist_ok=True)
            return ProjectRun(self, algo_dir, reused=False)
        else:
            algo_dir.mkdir(parents=True, exist_ok=True)
            return ProjectRun(self, algo_dir, reused=False)

    def list_runs(self) -> list[dict[str, Any]]:
        """List all algorithm run folders under this project.

        Returns:
            List of dicts with keys ``name``, ``path``, ``algo``, ``timestamp``.
        """
        runs: list[dict[str, Any]] = []
        for entry in sorted(self.path.iterdir()):
            if not entry.is_dir():
                continue
            if entry.name.startswith("_") or entry.name == "I_scripts":
                continue
            config = ProjectRun.load_config_txt(entry / "config.txt")
            algo = "unknown"
            timestamp = ""
            if config:
                algo = config.get("algorithm", "unknown")
                timestamp = config.get("timestamp", "")
            runs.append({
                "name": entry.name,
                "path": entry,
                "algo": algo,
                "timestamp": timestamp,
            })
        return runs

    # ── Summary files ──────────────────────────────────────────────────────

    def update_summary(self, run: "ProjectRun") -> None:
        """Update the project-level summary CSV files after a run.

        Appends (or replaces) rows from *run* into:
          - ``project_all_results.csv``
          - ``project_all_history.csv``

        If the run folder was reused (same config), previous summary entries
        for that folder are replaced rather than duplicated.
        """
        run_name = run.dir.name

        # ── Update results summary ──
        src_results = run.dir / "results.csv"
        if src_results.exists():
            dst = self.path / "project_all_results.csv"
            existing = _read_csv_rows(dst)
            # Filter out old entries for this run (if any)
            existing = [r for r in existing if r.get("run_folder", "") != run_name]
            # Read new rows
            new_rows = _read_csv_rows(src_results)
            # Add run_folder column if missing
            for row in new_rows:
                if "run_folder" not in row:
                    row["run_folder"] = run_name
            all_rows = existing + new_rows
            _write_csv_rows(dst, all_rows)

        # ── Update history summary ──
        src_history = run.dir / "history.csv"
        if src_history.exists():
            dst = self.path / "project_all_history.csv"
            existing = _read_csv_rows(dst)
            existing = [r for r in existing if r.get("run_folder", "") != run_name]
            new_rows = _read_csv_rows(src_history)
            for row in new_rows:
                if "run_folder" not in row:
                    row["run_folder"] = run_name
            all_rows = existing + new_rows
            _write_csv_rows(dst, all_rows)

        # Update run_count in metadata
        run_count = len(self.list_runs())
        self.update_metadata(run_count=str(run_count))


# ── ProjectRun ─────────────────────────────────────────────────────────────

class ProjectRun:
    """One optimization run within a project.

    Each run corresponds to a folder under the project directory, named
    either ``{algo_name}/`` (reused when config unchanged) or
    ``{algo_name}_{timestamp}/`` (new when config changes).
    """

    def __init__(self, project: Project, run_dir: Path, reused: bool = False) -> None:
        self.project = project
        self.dir = Path(run_dir).resolve()
        self.reused = reused
        self.algo_name = self.dir.name  # e.g. "nsga2" or "nsga2_20260822_143001"

    # ── Backward-compatible factory ────────────────────────────────────────

    @classmethod
    def create(cls, project_dir: str | Path, run_name: str | None = None) -> "ProjectRun":
        """Legacy factory: create a timestamped run under *project_dir/runs/*.

        .. deprecated::
            Use ``Project.create_run(algo_name, config)`` instead.
            This method exists only for backward compatibility with the
            existing ``optimization.py`` CLI code.
        """
        project_dir = Path(project_dir).resolve()
        runs_dir = project_dir / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        if run_name is None:
            run_name = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = runs_dir / run_name
        run_dir.mkdir(parents=True, exist_ok=True)
        # Wrap in a minimal Project so the instance works
        project = Project(project_dir)
        return cls(project, run_dir, reused=False)

    # ── Config ─────────────────────────────────────────────────────────────

    @staticmethod
    def load_config_txt(path: Path) -> Optional[dict[str, str]]:
        """Load a key=value config file, returning a dict or None."""
        if not path.exists():
            return None
        config: dict[str, str] = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if "=" in line:
                key, _, val = line.partition("=")
                config[key.strip()] = val.strip()
        return config if config else None

    def save_config_txt(self, config: dict[str, Any]) -> Path:
        """Save algorithm configuration as ``config.txt`` (key=value format).

        Args:
            config: Dict with keys like ``algorithm``, ``generations``, etc.
        """
        lines = [
            f"algorithm={config.get('algorithm', 'nsga2')}",
            f"generations={config.get('generations', 50)}",
            f"population={config.get('pop_size', config.get('population', 50))}",
            f"seed={config.get('seed', 1)}",
            f"dry_run={config.get('dry_run', True)}",
            f"plot_enabled={config.get('plot', config.get('plot_enabled', True))}",
            f"timestamp={datetime.now().isoformat(timespec='seconds')}",
        ]
        # Add any extra keys
        for key in ("csv_filename", "run_directory", "verbose"):
            if key in config:
                lines.append(f"{key}={config[key]}")
        path = self.dir / "config.txt"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    # ── Results (best solutions) ───────────────────────────────────────────

    def save_results_csv(
        self,
        X: list[list[float]],
        F: list[list[float]],          # normalized F values
        var_names: list[str],
        obj_names: list[str],
        specs: list[str],              # spec strings for denormalization
    ) -> Path:
        """Save the Pareto-optimal set as ``results.csv``.

        Critically, **F values are de-normalized** to actual simulation values
        before saving, and a ``pass_fail`` column is appended.

        Args:
            X: Variable values (actual, not normalized).
            F: Normalized objective values (to be denormalized).
            var_names: Variable names.
            obj_names: Objective names.
            specs: Spec strings, e.g. ``['< 300p', '> 1.5m']``.
        """
        path = self.dir / "results.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            # Build header
            header = ["run_folder", "algorithm"]
            header += [f"var_{v}" for v in var_names]
            header += [f"obj_{o}" for o in obj_names]
            header.append("pass_fail")
            w = csv.writer(f)
            w.writerow(header)

            for x_row, f_row in zip(X, F):
                # Denormalize F to get actual values
                actual_vals = []
                for norm_val, spec_str in zip(f_row, specs):
                    actual_vals.append(denormalize_f(norm_val, spec_str))
                # Determine pass/fail
                pf = check_pass_fail(actual_vals, specs)

                row = [self.algo_name, self.algo_name.split("_")[0]]
                row += [float(v) for v in x_row]
                row += actual_vals
                row.append(pf)
                w.writerow(row)

        return path

    # ── History (per-generation) ───────────────────────────────────────────

    def save_history_csv(
        self,
        n_gen: list[int],
        n_eval: list[int],
        best_X: list[list[float]],
        best_F: list[list[float]],     # normalized F values
        var_names: list[str],
        obj_names: list[str],
        specs: list[str],              # spec strings for denormalization
    ) -> Path:
        """Save per-generation history as ``history.csv``.

        If the run folder was **reused** (same config), new rows are
        *appended* to the existing file.  Otherwise a new file is created.

        F values are de-normalized to actual values; a ``pass_fail`` column
        is appended.
        """
        path = self.dir / "history.csv"
        header = ["run_folder", "algorithm", "generation", "evaluations"]
        header += [f"var_{v}" for v in var_names]
        header += [f"obj_{o}" for o in obj_names]
        header.append("pass_fail")

        # Determine write mode: append if reused file exists
        mode = "a" if (self.reused and path.exists()) else "w"
        file_exists = path.exists()

        with path.open(mode, newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            # Write header only for new files
            if mode == "w":
                w.writerow(header)

            for gen, ev, x_row, f_row in zip(n_gen, n_eval, best_X, best_F):
                actual_vals = []
                for norm_val, spec_str in zip(f_row, specs):
                    actual_vals.append(denormalize_f(norm_val, spec_str))
                pf = check_pass_fail(actual_vals, specs)

                row = [self.algo_name, self.algo_name.split("_")[0],
                       gen, ev]
                row += [float(v) for v in x_row]
                row += actual_vals
                row.append(pf)
                w.writerow(row)

        return path

    # ── Legacy compatibility: save_results, save_history, save_all ─────────

    def save_results(
        self,
        X: list[list[float]],
        F: list[list[float]],
        var_names: list[str],
        obj_names: list[str],
    ) -> Path:
        """Legacy-compatible save — delegates to ``save_results_csv``.

        Note: This method requires ``specs`` to be available via the
        project's ``I_scripts/specs.csv``.  If unavailable, F values are
        saved as-is (may be normalized).
        """
        specs = self._load_spec_strs()
        return self.save_results_csv(X, F, var_names, obj_names, specs)

    def save_history(
        self,
        n_gen: list[int],
        n_eval: list[int],
        best_X: list[list[float]],
        best_F: list[list[float]],
        var_names: list[str],
        obj_names: list[str],
    ) -> Path:
        """Legacy-compatible save — delegates to ``save_history_csv``."""
        specs = self._load_spec_strs()
        return self.save_history_csv(
            n_gen, n_eval, best_X, best_F, var_names, obj_names, specs
        )

    def save_all(
        self,
        res: Any,
        logger: Any,
        var_names: list[str],
        obj_names: list[str],
    ) -> None:
        """Save all artifacts from a completed optimization run.

        Args:
            res: Result object with ``.X`` and ``.F`` attributes.
            logger: ``OptimizationLogger`` with per-generation data.
            var_names: Variable names.
            obj_names: Objective names.
        """
        specs = self._load_spec_strs()

        # Results (Pareto set)
        if hasattr(res, "X") and res.X is not None:
            X_list = res.X.tolist() if hasattr(res.X, "tolist") else list(res.X)
            F_list = res.F.tolist() if hasattr(res.F, "tolist") else list(res.F)
            self.save_results_csv(X_list, F_list, var_names, obj_names, specs)

        # Per-generation history
        if logger is not None and logger.data.get("n_gen"):
            self.save_history_csv(
                logger.data["n_gen"],
                logger.data["n_eval"],
                [x.tolist() for x in logger.data["best_X"]],
                [f.tolist() for f in logger.data["best_F"]],
                var_names,
                obj_names,
                specs,
            )

    def _load_spec_strs(self) -> list[str]:
        """Load spec strings from the project's ``I_scripts/specs.csv``."""
        try:
            rows = self.project.load_specs_csv()
            if rows:
                specs = []
                for r in rows:
                    spec_val = r.get("spec", "")
                    if spec_val and str(spec_val).strip():
                        specs.append(str(spec_val).strip())
                if specs:
                    return specs
        except Exception:
            pass
        return []

    # ── Plot copying ───────────────────────────────────────────────────────

    def copy_plot(self, src: str | Path) -> Optional[Path]:
        """Copy a plot file into the run directory (if it exists)."""
        src = Path(src)
        if src.exists():
            dst = self.dir / src.name
            shutil.copy2(src, dst)
            return dst
        return None

    # ── Convenience: save config + variables + specs ───────────────────────

    def save_setup(
        self,
        config: dict,
        var_names: list[str],
        var_values: list[float],
        var_mins: list[float],
        var_maxs: list[float],
        spec_names: list[str],
        spec_weights: list[float],
        spec_strs: list[str],
    ) -> None:
        """Save all setup files (config + I_scripts) in one call.

        The config is saved to the run folder; variables and specs are also
        saved to the project's shared ``I_scripts/`` directory.
        """
        self.save_config_txt(config)
        self.project.save_variables_csv(var_names, var_values, var_mins, var_maxs)
        self.project.save_specs_csv(spec_names, spec_weights, spec_strs)


# ── Internal helpers ───────────────────────────────────────────────────────

def _is_valid_name(name: str) -> bool:
    """Check that *name* contains only safe filesystem characters."""
    import re
    return bool(re.match(r"^[a-zA-Z0-9_\-一-鿿]+$", name))


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    """Read all rows from a CSV file into a list of dicts."""
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def _write_csv_rows(path: Path, rows: list[dict[str, str]]) -> None:
    """Write a list of dicts to a CSV file, preserving header order."""
    if not rows:
        return
    header = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        w.writerows(rows)