"""CLI entry point for optimization-tool.

Delegates to :func:`optimization_tool.optimization.main` which provides the
full CLI with ``--dry-run``, ``--generations``, ``--population``, ``--plot``,
``--no-plot``, ``--plot-dir``, etc.
"""

from __future__ import annotations

import sys

from optimization_tool.optimization import main


if __name__ == "__main__":
    raise SystemExit(main())