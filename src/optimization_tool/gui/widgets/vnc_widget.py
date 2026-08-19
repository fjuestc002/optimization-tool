"""VNC display placeholder widget — reserved for Cadence GUI embedding."""

from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class VncWidget(QWidget):
    """VNC viewer placeholder.

    In Phase 5 this will embed a real VNC client (QVncWidget or noVNC in
    QWebEngineView). For now, it shows a reserved placeholder with a toggle.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._expanded = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Toggle header
        header = QHBoxLayout()
        self.btn_toggle = QPushButton("▶ VNC 视图 (Cadence GUI)")
        self.btn_toggle.setStyleSheet("""
            QPushButton {
                background-color: #d9d9d9; border: 1px solid #999999;
                text-align: left; padding: 4px 8px; font-weight: bold;
                color: #1a3a5c;
            }
            QPushButton:hover { background-color: #c0c0c0; }
        """)
        self.btn_toggle.setCheckable(True)
        self.btn_toggle.setChecked(False)
        header.addWidget(self.btn_toggle)
        layout.addLayout(header)

        # Placeholder frame
        self.frame = QFrame()
        self.frame.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        self.frame.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border: 1px solid #666666;
                border-radius: 4px;
            }
        """)
        self.frame.setMinimumHeight(150)

        f_layout = QVBoxLayout(self.frame)
        f_layout.setAlignment(Qt.AlignCenter)

        self.lbl_placeholder = QLabel("VNC 未连接\n\n连接后此处显示 Cadence GUI")
        self.lbl_placeholder.setAlignment(Qt.AlignCenter)
        self.lbl_placeholder.setStyleSheet("color: #888888; font-size: 13px;")
        self.lbl_placeholder.setFont(QFont("Consolas", 11))
        f_layout.addWidget(self.lbl_placeholder)

        self.frame.setVisible(False)
        layout.addWidget(self.frame)

        # Connect toggle
        self.btn_toggle.toggled.connect(self._on_toggle)

    def _on_toggle(self, checked: bool):
        self._expanded = checked
        self.frame.setVisible(checked)
        self.btn_toggle.setText(
            "▼ VNC 视图 (Cadence GUI)" if checked
            else "▶ VNC 视图 (Cadence GUI)"
        )

    def set_connected(self, connected: bool):
        """Update VNC connection status."""
        if connected:
            self.lbl_placeholder.setText("VNC 已连接\n\nCadence GUI 将显示在此区域")
            self.lbl_placeholder.setStyleSheet("color: #00aa00; font-size: 13px;")
        else:
            self.lbl_placeholder.setText("VNC 未连接\n\n连接后此处显示 Cadence GUI")
            self.lbl_placeholder.setStyleSheet("color: #888888; font-size: 13px;")