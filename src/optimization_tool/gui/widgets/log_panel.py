"""Log output panel — styled like Cadence CIW (Command Interpreter Window)."""

from PySide6.QtWidgets import QVBoxLayout, QWidget, QPlainTextEdit, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor

from ..lang import tr


# CIW-style color scheme
COLOR_INFO = QColor("#000000")       # black — normal output
COLOR_OK = QColor("#00aa00")         # green — success
COLOR_WARN = QColor("#ddaa00")       # yellow — warning
COLOR_ERROR = QColor("#cc0000")      # red — error
COLOR_DEBUG = QColor("#666666")      # gray — debug


class LogPanel(QWidget):
    """Log output widget styled like Cadence CIW."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self.title = QLabel()
        self.title.setStyleSheet("font-weight: bold; color: #1a3a5c; font-size: 12px;")
        layout.addWidget(self.title)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(10000)
        self.log.setStyleSheet("""
            QPlainTextEdit {
                background-color: #ffffff;
                border: 1px solid #999999;
                font-family: "Consolas", "Courier New", monospace;
                font-size: 12px;
                padding: 4px;
            }
        """)
        layout.addWidget(self.log)

        self.retranslate_ui()

    def retranslate_ui(self):
        """Update UI strings to current language."""
        self.title.setText(tr("log_title"))

    def _append(self, text: str, color: QColor):
        fmt = QTextCharFormat()
        fmt.setForeground(color)
        cursor = self.log.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text + "\n", fmt)
        self.log.setTextCursor(cursor)
        self.log.ensureCursorVisible()

    def info(self, text: str):
        self._append(text, COLOR_INFO)

    def ok(self, text: str):
        self._append(text, COLOR_OK)

    def warn(self, text: str):
        self._append(text, COLOR_WARN)

    def error(self, text: str):
        self._append(text, COLOR_ERROR)

    def debug(self, text: str):
        self._append(text, COLOR_DEBUG)

    def clear(self):
        self.log.clear()