"""Parameter configuration panel — Cadence-style left sidebar."""

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QGroupBox, QHBoxLayout,
    QLabel, QPushButton, QSpinBox, QVBoxLayout, QWidget, QLineEdit,
    QFileDialog,
)
from PySide6.QtCore import Qt


class ParamsPanel(QWidget):
    """Left-side parameter panel for optimization configuration."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(300)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        # ── Algorithm group ──
        grp_algo = QGroupBox("算法设置")
        algol = QVBoxLayout(grp_algo)
        algol.setSpacing(6)

        algol.addWidget(QLabel("优化算法:"))
        self.cb_algo = QComboBox()
        self.cb_algo.addItems([
            "nsga2", "nsga3", "spea2", "moead", "ctaea",
            "ga", "de", "pso", "cmaes",
        ])
        self.cb_algo.insertSeparator(9)
        self.cb_algo.addItems([
            "bayes_gp", "bayes_rf", "bayes_gbrt",
            "bayes_mo", "bayes_turbo",
        ])
        self.cb_algo.setToolTip(
            "pymoo 进化算法 — NSGA2/3/SPEA2/MOEAD 适合多目标, GA/DE/PSO 适合单目标\n"
            "贝叶斯优化 — bayes_gp 样本效率高, bayes_rf 鲁棒, bayes_mo 多目标"
        )
        algol.addWidget(self.cb_algo)

        row_gen = QHBoxLayout()
        row_gen.addWidget(QLabel("代数:"))
        self.spin_generations = QSpinBox()
        self.spin_generations.setRange(1, 9999)
        self.spin_generations.setValue(50)
        row_gen.addWidget(self.spin_generations)
        algol.addLayout(row_gen)

        row_pop = QHBoxLayout()
        row_pop.addWidget(QLabel("种群:"))
        self.spin_population = QSpinBox()
        self.spin_population.setRange(2, 9999)
        self.spin_population.setValue(50)
        row_pop.addWidget(self.spin_population)
        algol.addLayout(row_pop)

        row_seed = QHBoxLayout()
        row_seed.addWidget(QLabel("随机种子:"))
        self.spin_seed = QSpinBox()
        self.spin_seed.setRange(0, 999999)
        self.spin_seed.setValue(1)
        row_seed.addWidget(self.spin_seed)
        algol.addLayout(row_seed)

        layout.addWidget(grp_algo)

        # ── Run mode group ──
        grp_mode = QGroupBox("运行模式")
        model = QVBoxLayout(grp_mode)
        model.setSpacing(6)

        self.chk_dry_run = QCheckBox("Dry-Run 模式（无真实仿真）")
        self.chk_dry_run.setChecked(True)
        self.chk_dry_run.toggled.connect(self._on_dry_run_toggled)
        model.addWidget(self.chk_dry_run)

        self.chk_plot = QCheckBox("生成实时图表")
        self.chk_plot.setChecked(True)
        model.addWidget(self.chk_plot)

        self.chk_project = QCheckBox("启用项目存档")
        model.addWidget(self.chk_project)

        self.chk_verbose = QCheckBox("详细日志输出")
        model.addWidget(self.chk_verbose)

        layout.addWidget(grp_mode)

        # ── Project directory ──
        grp_proj = QGroupBox("项目目录")
        projl = QVBoxLayout(grp_proj)
        projl.setSpacing(4)

        self.edit_project_dir = QLineEdit()
        self.edit_project_dir.setPlaceholderText("留空 = 不存档")
        projl.addWidget(self.edit_project_dir)

        layout.addWidget(grp_proj)

        # ── Simulation settings (real-run mode) ──
        self.grp_sim = QGroupBox("仿真设置（非 Dry-Run）")
        siml = QVBoxLayout(self.grp_sim)
        siml.setSpacing(4)

        siml.addWidget(QLabel("CSV 文件路径:"))
        csv_row = QHBoxLayout()
        self.edit_csv = QLineEdit()
        self.edit_csv.setPlaceholderText("outputs_xxx_maestro.csv")
        csv_row.addWidget(self.edit_csv)
        self.btn_browse_csv = QPushButton("浏览...")
        self.btn_browse_csv.setFixedWidth(60)
        self.btn_browse_csv.clicked.connect(self._browse_csv)
        csv_row.addWidget(self.btn_browse_csv)
        siml.addLayout(csv_row)

        siml.addWidget(QLabel("运行目录:"))
        self.edit_run_dir = QLineEdit()
        self.edit_run_dir.setPlaceholderText(".")
        siml.addWidget(self.edit_run_dir)

        layout.addWidget(self.grp_sim)

        # ── Action buttons ──
        layout.addSpacing(8)

        self.btn_start = QPushButton("▶ 开始优化")
        self.btn_start.setObjectName("btnStart")
        self.btn_start.setMinimumHeight(36)
        layout.addWidget(self.btn_start)

        self.btn_stop = QPushButton("■ 停止")
        self.btn_stop.setObjectName("btnStop")
        self.btn_stop.setMinimumHeight(36)
        self.btn_stop.setEnabled(False)
        layout.addWidget(self.btn_stop)

        layout.addStretch()

        # ── Version info ──
        lbl_ver = QLabel("Prof. Fang Jian 优化工具 v0.1")
        lbl_ver.setAlignment(Qt.AlignCenter)
        lbl_ver.setStyleSheet("color: #808080; font-size: 11px;")
        layout.addWidget(lbl_ver)

    # ── Getters for parameter values ──

    @property
    def algo(self) -> str:
        return self.cb_algo.currentText()

    @property
    def generations(self) -> int:
        return self.spin_generations.value()

    @property
    def population(self) -> int:
        return self.spin_population.value()

    @property
    def seed(self) -> int:
        return self.spin_seed.value()

    @property
    def dry_run(self) -> bool:
        return self.chk_dry_run.isChecked()

    @property
    def plot_enabled(self) -> bool:
        return self.chk_plot.isChecked()

    @property
    def project_enabled(self) -> bool:
        return self.chk_project.isChecked()

    @property
    def verbose(self) -> bool:
        return self.chk_verbose.isChecked()

    @property
    def project_dir(self) -> str:
        return self.edit_project_dir.text().strip()

    @property
    def csv_filename(self) -> str:
        return self.edit_csv.text().strip()

    @property
    def run_directory(self) -> str:
        return self.edit_run_dir.text().strip() or "."

    def _browse_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 CSV 文件", "",
            "CSV 文件 (*.csv);;所有文件 (*.*)",
        )
        if path:
            self.edit_csv.setText(path)

    def _on_dry_run_toggled(self, checked: bool):
        """Enable/disable simulation settings based on dry-run mode."""
        self.grp_sim.setEnabled(not checked)