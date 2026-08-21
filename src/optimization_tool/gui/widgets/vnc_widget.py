"""VNC Viewer launcher — launches external RealVNC Viewer.

This widget does NOT embed a VNC client. It simply launches the user's
installed RealVNC Viewer (vncviewer.exe) as a separate process.
Connection configuration is entirely up to the user inside VNC Viewer.

This widget does NOT affect the optimizer in any way — if VNC Viewer
is not installed or fails to launch, the rest of the tool continues
to work normally.
"""

import subprocess
import shutil
from pathlib import Path

from PySide6.QtWidgets import (
    QHBoxLayout, QPushButton, QWidget, QMessageBox,
)

from ..lang import tr


class VncWidget(QWidget):
    """Compact VNC launch button, designed for the connection bar."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.btn_launch = QPushButton("🖥 " + tr("vnc_launch_btn"))
        self.btn_launch.clicked.connect(self._launch_vnc)
        layout.addWidget(self.btn_launch)

    # ── Public API ──

    def retranslate_ui(self):
        """Update UI strings to current language."""
        self.btn_launch.setText("🖥 " + tr("vnc_launch_btn"))

    # ── VNC launch ──

    def _launch_vnc(self):
        """Launch RealVNC Viewer as an external process."""
        exe = self._find_vncviewer()
        if exe is None:
            QMessageBox.warning(
                self,
                tr("vnc_not_found"),
                tr("vnc_not_found_msg"),
            )
            return

        try:
            subprocess.Popen([str(exe)], shell=False)
        except Exception as exc:
            QMessageBox.warning(
                self,
                tr("vnc_error_title"),
                f"{tr('vnc_launch_failed')}\n{exc}",
            )

    @staticmethod
    def _find_vncviewer() -> Path | None:
        """Locate vncviewer.exe on the system.

        Search order:
          1. ``shutil.which("vncviewer")`` — PATH lookup
          2. Common RealVNC install paths
        """
        # 1. PATH lookup
        found = shutil.which("vncviewer") or shutil.which("vncviewer.exe")
        if found:
            return Path(found)

        # 2. Common install locations
        candidates = [
            "C:/Program Files/RealVNC/VNC Viewer/vncviewer.exe",
            "C:/Program Files (x86)/RealVNC/VNC Viewer/vncviewer.exe",
        ]
        for p in candidates:
            path = Path(p)
            if path.exists():
                return path

        return None