"""Open Project dialog — list and select existing projects."""

from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QPushButton, QListWidgetItem,
)
from PySide6.QtCore import Qt

from ..lang import tr
from ...project import ProjectInfo


class OpenProjectDialog(QDialog):
    """Dialog for selecting an existing project to open.

    On accept, :attr:`selected_name` contains the chosen project name.
    """

    def __init__(self, projects: list[ProjectInfo], parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("project_open_title"))
        self.setMinimumSize(420, 320)
        self.setModal(True)

        self.selected_name: Optional[str] = None
        self._projects = projects

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        layout.addWidget(QLabel(tr("project_open_list")))

        self.list_projects = QListWidget()
        self.list_projects.setAlternatingRowColors(True)
        for info in self._projects:
            item = QListWidgetItem(f"{info.name}  ({info.created})")
            item.setData(Qt.UserRole, info.name)
            self.list_projects.addItem(item)
        layout.addWidget(self.list_projects)

        # Double-click to open
        self.list_projects.itemDoubleClicked.connect(self._accept)

        layout.addSpacing(8)

        # ── Buttons ──
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_ok = QPushButton(tr("project_open_btn_ok"))
        self.btn_ok.clicked.connect(self._accept)
        btn_row.addWidget(self.btn_ok)
        self.btn_cancel = QPushButton(tr("project_open_btn_cancel"))
        self.btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_cancel)
        layout.addLayout(btn_row)

        # Select first item if available
        if self.list_projects.count() > 0:
            self.list_projects.setCurrentRow(0)

    def _accept(self):
        item = self.list_projects.currentItem()
        if item is None:
            return
        self.selected_name = item.data(Qt.UserRole)
        self.accept()