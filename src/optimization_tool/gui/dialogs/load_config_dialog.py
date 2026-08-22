"""Load Config dialog — browse and select a config.txt file."""

from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog,
)

from ..lang import tr
from ...project import ProjectRun


class LoadConfigDialog(QDialog):
    """Dialog for loading a ``config.txt`` file from a previous run.

    On accept, :attr:`config` contains the parsed key-value pairs.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("load_config_title"))
        self.setMinimumWidth(500)
        self.setModal(True)

        self.config: Optional[dict[str, str]] = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # ── File path ──
        layout.addWidget(QLabel(tr("lbl_csv")))  # Reuse "CSV file path" label
        path_row = QHBoxLayout()
        self.edit_path = QLineEdit()
        self.edit_path.setPlaceholderText("Select a config.txt file...")
        path_row.addWidget(self.edit_path)
        self.btn_browse = QPushButton(tr("btn_browse"))
        self.btn_browse.clicked.connect(self._browse)
        path_row.addWidget(self.btn_browse)
        layout.addLayout(path_row)

        # ── Preview ──
        self.lbl_preview = QLabel()
        self.lbl_preview.setWordWrap(True)
        self.lbl_preview.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.lbl_preview)

        layout.addSpacing(8)

        # ── Buttons ──
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_ok = QPushButton(tr("project_open_btn_ok"))
        self.btn_ok.setEnabled(False)
        self.btn_ok.clicked.connect(self._accept)
        btn_row.addWidget(self.btn_ok)
        self.btn_cancel = QPushButton(tr("project_open_btn_cancel"))
        self.btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_cancel)
        layout.addLayout(btn_row)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, tr("load_config_title"), "",
            tr("load_config_filter"),
        )
        if path:
            self.edit_path.setText(path)
            cfg = ProjectRun.load_config_txt(Path(path))
            if cfg:
                self.config = cfg
                preview = "\n".join(f"{k} = {v}" for k, v in cfg.items())
                self.lbl_preview.setText(preview)
                self.btn_ok.setEnabled(True)
            else:
                self.lbl_preview.setText("(invalid or empty config file)")
                self.btn_ok.setEnabled(False)

    def _accept(self):
        if self.config is not None:
            self.accept()