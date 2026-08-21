"""Matplotlib plot canvas embedded in PySide6."""

from PySide6.QtWidgets import QVBoxLayout, QWidget, QLabel, QComboBox, QHBoxLayout
from PySide6.QtCore import Qt, Signal

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec

# ── Configure matplotlib for CJK text support ──────────────────────────────
import matplotlib.pyplot as plt
plt.rcParams["font.sans-serif"] = [
    "Microsoft YaHei", "SimHei", "DengXian", "DejaVu Sans",
]
plt.rcParams["axes.unicode_minus"] = False

from ..lang import tr


class PlotCanvas(FigureCanvasQTAgg):
    """Matplotlib canvas with 3-axis mosaic layout.

    Layout::
        ┌──────────────────────┐
        │     Convergence      │
        ├──────────┬───────────┤
        │  History │  Pareto   │
        │ (all pts)│  (front)  │
        └──────────┴───────────┘
    """

    def __init__(self, parent=None):
        self.fig = Figure(figsize=(8, 6.5), dpi=100, facecolor="#f0f0f0")
        # Mosaic: convergence (top full-width), history + pareto (bottom side-by-side)
        gs = GridSpec(2, 2, height_ratios=[1.3, 1], hspace=0.30, wspace=0.25,
                      left=0.09, right=0.97, top=0.93, bottom=0.08)
        self.ax_conv = self.fig.add_subplot(gs[0, :])   # convergence
        self.ax_hist = self.fig.add_subplot(gs[1, 0])   # all history
        self.ax_pareto = self.fig.add_subplot(gs[1, 1])  # pareto front

        self.axes = [self.ax_conv, self.ax_hist, self.ax_pareto]
        super().__init__(self.fig)
        self.setParent(parent)

    def clear_all(self):
        for ax in self.axes:
            ax.clear()

    def draw_plot(self):
        self.fig.tight_layout()
        self.draw()


class PlotPanel(QWidget):
    """Plot panel with convergence, all-history, and Pareto front views."""

    # 用户点击 Pareto 前沿上的点，发射 (var_names, x_values)
    pareto_point_selected = Signal(list, list)

    MODES = ["mode_both", "mode_convergence", "mode_pareto"]

    def __init__(self, parent=None):
        super().__init__(parent)
        # 存储用于点击选取的 Pareto 数据
        self._pareto_X = []
        self._pareto_F = []
        self._pareto_var_names = []
        self._pareto_obj_names = []
        # 当前 Pareto scatter 对象（用于 picker）
        self._pareto_scatter = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Toolbar row
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.lbl_view = QLabel()
        self.lbl_view.setStyleSheet("font-weight: bold; color: #1a3a5c;")
        toolbar.addWidget(self.lbl_view)

        self.cb_mode = QComboBox()
        self.cb_mode.addItems([tr(m) for m in self.MODES])
        self.cb_mode.setCurrentIndex(0)
        toolbar.addWidget(self.cb_mode)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Canvas (mosaic: convergence + history + pareto)
        self.canvas = PlotCanvas(self)
        self.canvas.ax_conv.set_title(tr("convergence_title"), fontsize=11, fontweight="bold", color="#1a3a5c")
        self.canvas.ax_hist.set_title(tr("history_title"), fontsize=11, fontweight="bold", color="#1a3a5c")
        self.canvas.ax_pareto.set_title(tr("pareto_title"), fontsize=11, fontweight="bold", color="#1a3a5c")
        self.canvas.ax_conv.set_xlabel(tr("convergence_xlabel"))
        self.canvas.ax_conv.set_ylabel(tr("convergence_ylabel"))
        self.canvas.ax_hist.set_xlabel(tr("pareto_xlabel"))
        self.canvas.ax_hist.set_ylabel(tr("pareto_ylabel"))
        self.canvas.ax_pareto.set_xlabel(tr("pareto_xlabel"))
        self.canvas.ax_pareto.set_ylabel(tr("pareto_ylabel"))
        layout.addWidget(self.canvas)

        # 连接 pick 事件
        self.canvas.fig.canvas.mpl_connect('pick_event', self._on_pareto_pick)

    def retranslate_ui(self):
        """Update all UI strings to the current language."""
        self.lbl_view.setText(tr("plot_view"))
        current_idx = self.cb_mode.currentIndex()
        self.cb_mode.clear()
        self.cb_mode.addItems([tr(m) for m in self.MODES])
        self.cb_mode.setCurrentIndex(min(current_idx, len(self.MODES) - 1))

        self.canvas.ax_conv.set_title(tr("convergence_title"), fontsize=11, fontweight="bold", color="#1a3a5c")
        self.canvas.ax_hist.set_title(tr("history_title"), fontsize=11, fontweight="bold", color="#1a3a5c")
        self.canvas.ax_pareto.set_title(tr("pareto_title"), fontsize=11, fontweight="bold", color="#1a3a5c")
        self.canvas.ax_conv.set_xlabel(tr("convergence_xlabel"))
        self.canvas.ax_conv.set_ylabel(tr("convergence_ylabel"))
        self.canvas.ax_hist.set_xlabel(tr("pareto_xlabel"))
        self.canvas.ax_hist.set_ylabel(tr("pareto_ylabel"))
        self.canvas.ax_pareto.set_xlabel(tr("pareto_xlabel"))
        self.canvas.ax_pareto.set_ylabel(tr("pareto_ylabel"))
        self.canvas.draw_plot()

    # ── Convergence plot ──

    def update_convergence(self, n_gen: list, best_F: list, obj_names: list):
        """Update the convergence plot with new generation data."""
        ax = self.canvas.ax_conv
        ax.clear()
        if not n_gen or not best_F:
            ax.set_title("等待数据..." if tr("convergence_title") == "收敛曲线" else "Waiting...",
                         fontsize=11, fontweight="bold", color="#1a3a5c")
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

        ax.set_title(tr("convergence_title"), fontsize=11, fontweight="bold", color="#1a3a5c")
        ax.set_xlabel(tr("convergence_xlabel"))
        ax.set_ylabel(tr("convergence_ylabel"))
        ax.legend(fontsize=9)
        ax.grid(True, linestyle="--", alpha=0.3)
        self.canvas.draw_plot()

    # ── All-history scatter ──

    def update_history(self, all_F: list, obj_names: list):
        """Update the all-history scatter plot (bottom-left).

        Args:
            all_F: 所有代所有个体的目标值，形状为 [[f1, f2], ...]
            obj_names: 目标名列表
        """
        ax = self.canvas.ax_hist
        ax.clear()
        if not all_F or len(all_F[0]) < 2:
            ax.set_title(tr("history_title"), fontsize=10, color="#666666")
            self.canvas.draw_plot()
            return

        f1 = [pt[0] for pt in all_F]
        f2 = [pt[1] for pt in all_F]
        ax.scatter(f1, f2, c="#191616FF", s=8, alpha=0.4, edgecolors="none")
        ax.set_title(tr("history_title"), fontsize=11, fontweight="bold", color="#1a3a5c")
        ax.set_xlabel(obj_names[0] if len(obj_names) > 0 else tr("pareto_xlabel"))
        ax.set_ylabel(obj_names[1] if len(obj_names) > 1 else tr("pareto_ylabel"))
        ax.grid(True, linestyle="--", alpha=0.3)
        # 保持正方形比例
        ax.set_aspect('equal', adjustable='datalim')
        self.canvas.draw_plot()

    # ── Pareto front + click selection ──

    def update_pareto(self, F: list, obj_names: list):
        """Update the Pareto front plot (intermediate updates, no picker)."""
        self._pareto_F = F
        self._pareto_obj_names = obj_names
        self._draw_pareto(picker_enabled=False)

    def set_pareto_data(self, X, F, var_names, obj_names):
        """Store final Pareto data and enable click selection.

        Args:
            X: Pareto 变量值矩阵 (n × n_vars)
            F: Pareto 目标值矩阵 (n × n_obj)
            var_names: 变量名列表
            obj_names: 目标名列表
        """
        self._pareto_X = X
        self._pareto_F = F
        self._pareto_var_names = var_names
        self._pareto_obj_names = obj_names
        self._draw_pareto(picker_enabled=True)

    def _draw_pareto(self, picker_enabled: bool = False):
        """Redraw the Pareto subplot, optionally enable picker."""
        ax = self.canvas.ax_pareto
        ax.clear()
        self._pareto_scatter = None
        F = self._pareto_F
        obj_names = self._pareto_obj_names

        if not F or len(F[0]) < 2:
            ax.set_title(tr("pareto_title") + " (multi-objective ≥2)",
                         fontsize=10, color="#666666")
            self.canvas.draw_plot()
            return

        f1 = [pt[0] for pt in F]
        f2 = [pt[1] for pt in F]
        scat = ax.scatter(f1, f2, c="#4a7db4", s=30, alpha=0.8,
                          edgecolors="#1a3a5c", linewidths=0.5)
        ax.set_title(tr("pareto_title"), fontsize=11, fontweight="bold", color="#1a3a5c")
        ax.set_xlabel(obj_names[0] if len(obj_names) > 0 else tr("pareto_xlabel"))
        ax.set_ylabel(obj_names[1] if len(obj_names) > 1 else tr("pareto_ylabel"))
        ax.grid(True, linestyle="--", alpha=0.3)
        # 保持正方形比例
        ax.set_aspect('equal', adjustable='datalim')

        if picker_enabled and len(F) > 0:
            scat.set_picker(True)
            self._pareto_scatter = scat

        self.canvas.draw_plot()

    def _on_pareto_pick(self, event):
        """Pareto 前沿点击事件：找到最近点并发射信号。"""
        if event.artist is not self._pareto_scatter:
            return
        if not self._pareto_X or not self._pareto_var_names:
            return

        ind = event.ind[0]  # 点击的点的索引
        if ind >= len(self._pareto_X):
            return

        x_vals = list(self._pareto_X[ind])
        self.pareto_point_selected.emit(self._pareto_var_names, x_vals)

    def clear_plots(self):
        self.canvas.clear_all()
        self.canvas.draw_plot()
        self._pareto_X = []
        self._pareto_F = []
        self._pareto_var_names = []
        self._pareto_obj_names = []
        self._pareto_scatter = None