"""Pareto results table widget."""

from PySide6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QLabel
from PySide6.QtCore import Qt


class ResultsTable(QWidget):
    """Table displaying Pareto-optimal solutions."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        title = QLabel("Pareto 最优解集")
        title.setStyleSheet("font-weight: bold; color: #1a3a5c; font-size: 12px;")
        layout.addWidget(title)

        self.table = QTableWidget(0, 0)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

    def set_data(self, var_names: list, obj_names: list,
                 X: list, F: list):
        """Populate the table with Pareto results."""
        n_cols = len(var_names) + len(obj_names)
        self.table.setColumnCount(n_cols)
        self.table.setRowCount(len(X) if X else 0)

        # Headers
        headers = [f"变量: {n}" for n in var_names] + [f"目标: {n}" for n in obj_names]
        self.table.setHorizontalHeaderLabels(headers)

        # Data
        for i, (x, f) in enumerate(zip(X, F)):
            for j, val in enumerate(x):
                item = QTableWidgetItem(f"{val:.6g}")
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(i, j, item)
            for j, val in enumerate(f):
                col = len(var_names) + j
                item = QTableWidgetItem(f"{val:.6g}")
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(i, col, item)

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.resizeColumnsToContents()

    def clear_data(self):
        self.table.setRowCount(0)
        self.table.setColumnCount(0)