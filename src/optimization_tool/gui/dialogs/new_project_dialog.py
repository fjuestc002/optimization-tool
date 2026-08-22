"""New Project dialog — enter project name and select root path."""

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QMessageBox,
)
from PySide6.QtCore import Qt

from ..lang import tr


class NewProjectDialog(QDialog):
    """Dialog for creating a new project.

    The user enters a project name and optionally changes the root path.
    On accept, :attr:`project_name` and :attr:`root_path` are available.
    """

    def __init__(self, root_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("project_new_title"))
        self.setMinimumWidth(420)
        self.setModal(True)

        self._root_path = root_path
        self.project_name = ""
        self.selected_root = root_path

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # ── Project name ──
        layout.addWidget(QLabel(tr("project_new_name")))
        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("e.g. LDO_optimization")
        layout.addWidget(self.edit_name)

        # ── Root path ──
        layout.addWidget(QLabel(tr("project_new_root")))
        path_row = QHBoxLayout()
        self.edit_root = QLineEdit(self._root_path)
        self.edit_root.setReadOnly(True)
        path_row.addWidget(self.edit_root)
        self.btn_browse = QPushButton(tr("project_new_btn_browse"))
        self.btn_browse.clicked.connect(self._browse_root)
        path_row.addWidget(self.btn_browse)
        layout.addLayout(path_row)

        layout.addSpacing(8)

        # ── Buttons ──
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_ok = QPushButton(tr("project_new_btn_ok"))
        self.btn_ok.clicked.connect(self._accept)
        btn_row.addWidget(self.btn_ok)
        self.btn_cancel = QPushButton(tr("project_new_btn_cancel"))
        self.btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_cancel)
        layout.addLayout(btn_row)

        # Enter key triggers accept
        self.edit_name.returnPressed.connect(self._accept)

    def _browse_root(self):
        path = QFileDialog.getExistingDirectory(
            self, tr("project_new_btn_browse"), self.edit_root.text(),
        )
        if path:
            self.edit_root.setText(path)
            self.selected_root = path

    def _accept(self):
        name = self.edit_name.text().strip()
        if not name:
            QMessageBox.warning(self, tr("project_new_title"),
                                tr("msg_project_name_empty"))
            self.edit_name.setFocus()
            return
        self.project_name = name
        self.selected_root = self.edit_root.text().strip()
        self.accept()