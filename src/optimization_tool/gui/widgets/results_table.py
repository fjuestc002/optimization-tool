"""Pareto results table widget."""

import csv
from pathlib import Path
from typing import List, Optional

from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QHeaderView, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget, QLabel,
)
from PySide6.QtCore import Qt, Signal

from ..lang import tr


def _extract_spec_info(spec_str: str) -> tuple:
    """从 spec 字符串提取方向和阈值。

    返回 (direction, threshold)，其中 direction = -1 表示 > 类，+1 表示 < 类。
    """
    s = spec_str.strip()
    if s.startswith('>') or s.startswith('≥'):
        direction = -1
    elif s.startswith('<') or s.startswith('≤'):
        direction = +1
    else:
        direction = 1
    # 提取数值部分
    num_part = s.lstrip('>≥<≤ ')
    try:
        # 处理 SI 单位后缀 (n, u, m, p, k 等)
        text = num_part.strip().lower()
        if text.endswith('n'):
            threshold = float(text[:-1]) * 1e-9
        elif text.endswith('u'):
            threshold = float(text[:-1]) * 1e-6
        elif text.endswith('m'):
            threshold = float(text[:-1]) * 1e-3
        elif text.endswith('p'):
            threshold = float(text[:-1]) * 1e-12
        elif text.endswith('k'):
            threshold = float(text[:-1]) * 1e3
        elif text.endswith('meg'):
            threshold = float(text[:-3]) * 1e6
        elif text.endswith('g'):
            threshold = float(text[:-1]) * 1e9
        else:
            threshold = float(text)
    except (ValueError, AttributeError):
        threshold = None
    return direction, threshold


def denormalize_f(normalized: float, spec_str: str) -> float:
    """将归一化的 pymoo 目标值还原为实际仿真值。

    公式：
      > 类: normalized = (threshold - raw) / threshold  →  raw = threshold * (1 - normalized)
      < 类: normalized = (raw - threshold) / threshold  →  raw = threshold * (1 + normalized)
    """
    direction, threshold = _extract_spec_info(spec_str)
    if threshold is not None and abs(threshold) > 1e-30:
        return threshold * (1.0 + direction * normalized)
    return normalized


class ResultsTable(QWidget):
    """Table displaying Pareto-optimal solutions with selection and save support."""

    # 发射信号: (var_names, x_values) — 用户选中某行要回传电路
    solution_selected = Signal(list, list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._var_names = []
        self._obj_names = []
        self._X = []
        self._F = []
        self._specs = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # 标题行 + 保存按钮
        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        self._title = QLabel()
        self._title.setStyleSheet("font-weight: bold; color: #1a3a5c; font-size: 12px;")
        header_row.addWidget(self._title)

        header_row.addStretch()

        self._btn_save = QPushButton("💾 Save CSV")
        self._btn_save.setFixedWidth(100)
        self._btn_save.setToolTip("将 Pareto 最优解集保存为 CSV 文件")
        self._btn_save.clicked.connect(self._save_to_csv)
        self._btn_save.setEnabled(False)
        header_row.addWidget(self._btn_save)

        layout.addLayout(header_row)

        self.table = QTableWidget(0, 0)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

        self.retranslate_ui()

    def retranslate_ui(self):
        """Update UI strings to current language."""
        self._title.setText(tr("results_title"))
        # 表头和数据按钮在下一次 set_data 时自动更新

    def set_data(self, var_names: list, obj_names: list,
                 X: list, F: list, specs: Optional[List[str]] = None):
        """Populate the table with Pareto results.

        Args:
            var_names: 变量名列表
            obj_names: 目标名列表
            X: 变量值矩阵 (n_solutions × n_vars)
            F: 归一化目标值矩阵 (n_solutions × n_objs)
            specs: 可选的 spec 字符串列表，用于反归一化显示实际值
        """
        self._var_names = list(var_names)
        self._obj_names = list(obj_names)
        self._X = [list(row) for row in X] if X else []
        self._F = [list(row) for row in F] if F else []
        self._specs = list(specs) if specs else []

        # 数据列 + 1 个操作按钮列
        n_data_cols = len(var_names) + len(obj_names)
        n_cols = n_data_cols + 1
        self.table.setColumnCount(n_cols)
        self.table.setRowCount(len(X) if X else 0)

        # Headers
        headers = (
            [tr("col_var", n=n) for n in var_names]
            + [tr("col_obj", n=n) for n in obj_names]
            + [tr("col_action")]
        )
        self.table.setHorizontalHeaderLabels(headers)

        # Data
        for i, (x, f) in enumerate(zip(X, F)):
            for j, val in enumerate(x):
                item = QTableWidgetItem(f"{val:.6g}")
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(i, j, item)
            for j, val in enumerate(f):
                col = len(var_names) + j
                # 反归一化：如果提供了 specs，还原为实际仿真值
                display_val = val
                if specs is not None and j < len(specs):
                    raw = denormalize_f(val, specs[j])
                    display_val = raw
                item = QTableWidgetItem(f"{display_val:.6g}")
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(i, col, item)

            # 操作按钮列
            btn_col = n_data_cols
            btn = QPushButton(tr("btn_select"))
            btn.setToolTip(tr("btn_select_tooltip"))
            btn.setFixedWidth(130)
            # 用 lambda 捕获当前行索引
            btn.clicked.connect(lambda checked, row=i: self._on_select_clicked(row))
            self.table.setCellWidget(i, btn_col, btn)

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.resizeColumnsToContents()

        # 有数据时启用保存按钮
        self._btn_save.setEnabled(len(self._X) > 0)

    def _on_select_clicked(self, row: int):
        """用户点击 Backannotate to CDS 按钮。"""
        if row < len(self._X) and self._var_names:
            x_vals = self._X[row]
            self.solution_selected.emit(self._var_names, x_vals)

    def _save_to_csv(self):
        """将当前 Pareto 解集保存为 CSV 文件。"""
        if not self._X or not self._var_names:
            return

        fpath, _ = QFileDialog.getSaveFileName(
            self, "Save Pareto Results",
            str(Path.cwd() / "pareto_results.csv"),
            "CSV Files (*.csv);;All Files (*.*)",
        )
        if not fpath:
            return

        try:
            # 构建列名: 变量 + 目标(实际值) + 目标(归一化)
            all_headers = (
                [f"var_{n}" for n in self._var_names]
                + [f"obj_{n}" for n in self._obj_names]
                + [f"obj_{n}_norm" for n in self._obj_names]
            )
            with open(fpath, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(all_headers)
                for i in range(len(self._X)):
                    row = []
                    # 变量值
                    row.extend(self._X[i])
                    # 目标实际值
                    for j in range(len(self._obj_names)):
                        if j < len(self._specs):
                            raw = denormalize_f(self._F[i][j], self._specs[j])
                        else:
                            raw = self._F[i][j]
                        row.append(raw)
                    # 目标归一化值
                    row.extend(self._F[i])
                    writer.writerow(row)

            self._btn_save.setText("✅ Saved")
            self._btn_save.setToolTip(str(fpath))
        except Exception as exc:
            self._btn_save.setText("❌ Error")
            self._btn_save.setToolTip(str(exc))

    def clear_data(self):
        self.table.setRowCount(0)
        self.table.setColumnCount(0)
        self._var_names = []
        self._obj_names = []
        self._X = []
        self._F = []
        self._specs = []
        self._btn_save.setEnabled(False)
        self._btn_save.setText("💾 Save CSV")