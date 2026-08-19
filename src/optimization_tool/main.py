"""Entry point for optimization-tool.

CLI mode: delegates to :func:`optimization_tool.optimization.main` which provides
the full CLI with ``--dry-run``, ``--generations``, ``--population``, etc.

GUI mode: launches the PySide6 desktop application with ``--gui``.
"""

from __future__ import annotations

import sys


def main() -> int:
    """Dispatch to CLI or GUI entry point based on ``--gui`` flag."""
    if "--gui" in sys.argv:
        sys.argv.remove("--gui")
        from optimization_tool.gui.app import launch_gui
        return launch_gui()
    from optimization_tool.optimization import main as _cli_main
    return _cli_main()


if __name__ == "__main__":
    raise SystemExit(main())