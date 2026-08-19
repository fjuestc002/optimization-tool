"""Application entry point — launch the PySide6 GUI."""

import sys

from PySide6.QtWidgets import QApplication

from .style import cadence_stylesheet
from .main_window import MainWindow


def launch_gui():
    """Create QApplication, apply Cadence style, show MainWindow, and run event loop."""
    app = QApplication(sys.argv)
    app.setApplicationName("DClaw 优化工具")
    app.setOrganizationName("DClaw")

    # Apply Cadence-inspired stylesheet
    app.setStyleSheet(cadence_stylesheet())

    # Create and show main window
    win = MainWindow()
    win.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(launch_gui())