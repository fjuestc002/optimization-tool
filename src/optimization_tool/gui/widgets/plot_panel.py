"""Matplotlib plot canvas embedded in PySide6."""

from PySide6.QtWidgets import QVBoxLayout, QWidget, QLabel, QComboBox, QHBoxLayout
from PySide6.QtCore import Qt

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

# ── Configure matplotlib for CJK text support ──────────────────────────────
import matplotlib.pyplot as plt
plt.rcParams["font.sans-serif"] = [
    "Microsoft YaHei", "SimHei", "DengXian", "DejaVu Sans",
]
plt.rcParams["axes.unicode_minus"] = False


class PlotCanvas(FigureCanvasQTAgg):
    """Matplotlib canvas embedded in Qt."""

    def __init__(self, parent=None, n_subplots: int = 1):
        self.fig = Figure(figsize=(6, 4), dpi=100, facecolor="#f0f0f0")
        self.fig.subplots_adjust(left=0.12, right=0.95, top=0.92, bottom=0.12)
        if n_subplots == 1:
            self.axes = [self.fig.add_subplot(111)]
        else:
            self.axes = self.fig.subplots(n_subplots, 1, sharex=False)
            if n_subplots == 2:
                self.fig.subplots_adjust(hspace=0.35)
        super().__init__(self.fig)
        self.setParent(parent)

    def clear_all(self):
        for ax in self.axes:
            ax.clear()

    def set_title(self, text: str, subplot: int = 0):
        self.axes[subplot].set_title(text, fontsize=11, fontweight="bold",
                                     color="#1a3a5c")

    def draw_plot(self):
        self.fig.tight_layout()
        self.draw()


class PlotPanel(QWidget):
    """Plot panel with view-switching toolbar (Convergence / Pareto / Both)."""

    MODES = ["收敛图 + Pareto 图", "收敛图", "Pareto 图"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Toolbar row
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        lbl = QLabel("图表视图:")
        lbl.setStyleSheet("font-weight: bold; color: #1a3a5c;")
        toolbar.addWidget(lbl)

        self.cb_mode = QComboBox()
        self.cb_mode.addItems(self.MODES)
        self.cb_mode.setCurrentIndex(0)
        toolbar.addWidget(self.cb_mode)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Canvas (dual subplots: convergence + pareto)
        self.canvas = PlotCanvas(self, n_subplots=2)
        self.canvas.axes[0].set_title("收敛曲线", fontsize=11, fontweight="bold", color="#1a3a5c")
        self.canvas.axes[1].set_title("Pareto 前沿", fontsize=11, fontweight="bold", color="#1a3a5c")
        self.canvas.axes[0].set_xlabel("代数")
        self.canvas.axes[0].set_ylabel("目标值")
        self.canvas.axes[1].set_xlabel("目标 1")
        self.canvas.axes[1].set_ylabel("目标 2")
        layout.addWidget(self.canvas)

    def update_convergence(self, n_gen: list, best_F: list, obj_names: list):
        """Update the convergence plot with new generation data."""
        ax = self.canvas.axes[0]
        ax.clear()
        if not n_gen or not best_F:
            ax.set_title("等待数据...", fontsize=11, fontweight="bold", color="#1a3a5c")
            self.canvas.draw_plot()
            return

        n_obj = len(best_F[0]) if best_F else 1
        arr = [[f[obj] for f in best_F] for obj in range(n_obj)]
        colors = ["#1a3a5c", "#cc3333", "#2a7a3a", "#ddaa00", "#6a4a9a"]
        for obj_idx in range(n_obj):
            color = colors[obj_idx % len(colors)]
            label = obj_names[obj_idx] if obj_idx < len(obj_names) else f"Obj{obj_idx}"
            ax.plot(n_gen, arr[obj_idx], "-o", color=color, label=label,
                    markersize=3, linewidth=1.5)

        ax.set_title("收敛曲线", fontsize=11, fontweight="bold", color="#1a3a5c")
        ax.set_xlabel("代数")
        ax.set_ylabel("目标值")
        ax.legend(fontsize=9)
        ax.grid(True, linestyle="--", alpha=0.3)
        self.canvas.draw_plot()

    def update_pareto(self, F: list, obj_names: list):
        """Update the Pareto front plot."""
        ax = self.canvas.axes[1]
        ax.clear()
        if not F or len(F[0]) < 2:
            # Single objective — show histogram or skip
            ax.set_title("Pareto 前沿 (多目标 ≥2 时显示)", fontsize=10, color="#666666")
            self.canvas.draw_plot()
            return

        f1 = [pt[0] for pt in F]
        f2 = [pt[1] for pt in F]
        ax.scatter(f1, f2, c="#4a7db4", s=30, alpha=0.8, edgecolors="#1a3a5c", linewidths=0.5)
        ax.set_title("Pareto 前沿", fontsize=11, fontweight="bold", color="#1a3a5c")
        ax.set_xlabel(obj_names[0] if len(obj_names) > 0 else "目标 1")
        ax.set_ylabel(obj_names[1] if len(obj_names) > 1 else "目标 2")
        ax.grid(True, linestyle="--", alpha=0.3)
        self.canvas.draw_plot()

    def clear_plots(self):
        self.canvas.clear_all()
        self.canvas.draw_plot()