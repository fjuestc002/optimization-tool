"""Parameter configuration panel — Cadence-style left sidebar."""

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QGroupBox, QHBoxLayout,
    QLabel, QPushButton, QSpinBox, QVBoxLayout, QWidget, QLineEdit,
    QFileDialog,
)
from PySide6.QtCore import Qt
from typing import Any, Optional

from ..lang import tr


class ParamsPanel(QWidget):
    """Left-side parameter panel for optimization configuration."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(300)
        self._current_project_name: Optional[str] = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        # ── Algorithm group ──
        self.grp_algo = QGroupBox()
        algol = QVBoxLayout(self.grp_algo)
        algol.setSpacing(6)

        self.lbl_algo = QLabel()
        algol.addWidget(self.lbl_algo)

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
        algol.addWidget(self.cb_algo)

        row_gen = QHBoxLayout()
        self.lbl_gen = QLabel()
        row_gen.addWidget(self.lbl_gen)
        self.spin_generations = QSpinBox()
        self.spin_generations.setRange(1, 9999)
        self.spin_generations.setValue(50)
        row_gen.addWidget(self.spin_generations)
        algol.addLayout(row_gen)

        row_pop = QHBoxLayout()
        self.lbl_pop = QLabel()
        row_pop.addWidget(self.lbl_pop)
        self.spin_population = QSpinBox()
        self.spin_population.setRange(2, 9999)
        self.spin_population.setValue(50)
        row_pop.addWidget(self.spin_population)
        algol.addLayout(row_pop)

        row_seed = QHBoxLayout()
        self.lbl_seed = QLabel()
        row_seed.addWidget(self.lbl_seed)
        self.spin_seed = QSpinBox()
        self.spin_seed.setRange(0, 999999)
        self.spin_seed.setValue(1)
        row_seed.addWidget(self.spin_seed)
        algol.addLayout(row_seed)

        layout.addWidget(self.grp_algo)

        # ── Run mode group ──
        self.grp_mode = QGroupBox()
        model = QVBoxLayout(self.grp_mode)
        model.setSpacing(6)

        self.chk_dry_run = QCheckBox()
        self.chk_dry_run.setChecked(True)
        self.chk_dry_run.toggled.connect(self._on_dry_run_toggled)
        model.addWidget(self.chk_dry_run)

        self.chk_plot = QCheckBox()
        self.chk_plot.setChecked(True)
        model.addWidget(self.chk_plot)

        self.chk_project = QCheckBox()
        model.addWidget(self.chk_project)

        self.chk_verbose = QCheckBox()
        model.addWidget(self.chk_verbose)

        layout.addWidget(self.grp_mode)

        # ── Project display ──
        self.grp_proj = QGroupBox()
        projl = QVBoxLayout(self.grp_proj)
        projl.setSpacing(4)

        self.lbl_project_name = QLabel()
        self.lbl_project_name.setStyleSheet("font-weight: bold; color: #E65100;")
        projl.addWidget(self.lbl_project_name)

        self.edit_project_dir = QLineEdit()
        self.edit_project_dir.setPlaceholderText(tr("proj_placeholder"))
        projl.addWidget(self.edit_project_dir)

        layout.addWidget(self.grp_proj)

        # ── Simulation settings (real-run mode) ──
        self.grp_sim = QGroupBox()
        siml = QVBoxLayout(self.grp_sim)
        siml.setSpacing(4)

        self.lbl_csv = QLabel()
        siml.addWidget(self.lbl_csv)

        csv_row = QHBoxLayout()
        self.edit_csv = QLineEdit()
        csv_row.addWidget(self.edit_csv)
        self.btn_browse_csv = QPushButton()
        self.btn_browse_csv.setFixedWidth(60)
        self.btn_browse_csv.clicked.connect(self._browse_csv)
        csv_row.addWidget(self.btn_browse_csv)
        siml.addLayout(csv_row)

        self.lbl_run_dir = QLabel()
        siml.addWidget(self.lbl_run_dir)

        self.edit_run_dir = QLineEdit()
        self.edit_run_dir.setPlaceholderText(tr("run_dir_placeholder"))
        siml.addWidget(self.edit_run_dir)

        layout.addWidget(self.grp_sim)

        # ── Action buttons ──
        layout.addSpacing(8)

        self.btn_start = QPushButton()
        self.btn_start.setObjectName("btnStart")
        self.btn_start.setMinimumHeight(36)
        layout.addWidget(self.btn_start)

        self.btn_stop = QPushButton()
        self.btn_stop.setObjectName("btnStop")
        self.btn_stop.setMinimumHeight(36)
        self.btn_stop.setEnabled(False)
        layout.addWidget(self.btn_stop)

        layout.addStretch()

        # ── Version info ──
        self.lbl_ver = QLabel()
        self.lbl_ver.setAlignment(Qt.AlignCenter)
        self.lbl_ver.setStyleSheet("color: #808080; font-size: 11px;")
        layout.addWidget(self.lbl_ver)

        # Apply initial translations
        self.retranslate_ui()

    def retranslate_ui(self):
        """Update all UI strings to the current language."""
        self.grp_algo.setTitle(tr("grp_algo"))
        self.lbl_algo.setText(tr("lbl_algo"))
        self.lbl_gen.setText(tr("lbl_generations"))
        self.lbl_pop.setText(tr("lbl_population"))
        self.lbl_seed.setText(tr("lbl_seed"))
        self.cb_algo.setToolTip(tr("algo_tooltip"))

        self.grp_mode.setTitle(tr("grp_mode"))
        self.chk_dry_run.setText(tr("chk_dry_run"))
        self.chk_plot.setText(tr("chk_plot"))
        self.chk_project.setText(tr("chk_project"))
        self.chk_verbose.setText(tr("chk_verbose"))

        self.grp_proj.setTitle(tr("grp_proj"))
        if self._current_project_name:
            self.lbl_project_name.setText(
                tr("project_status", name=self._current_project_name))
            self.lbl_project_name.setVisible(True)
        else:
            self.lbl_project_name.setText(tr("project_no_project"))
            self.lbl_project_name.setVisible(True)
        self.edit_project_dir.setPlaceholderText(tr("proj_placeholder"))

        self.grp_sim.setTitle(tr("grp_sim"))
        self.lbl_csv.setText(tr("lbl_csv"))
        self.edit_csv.setPlaceholderText(tr("csv_placeholder"))
        self.btn_browse_csv.setText(tr("btn_browse"))
        self.lbl_run_dir.setText(tr("lbl_run_dir"))
        self.edit_run_dir.setPlaceholderText(tr("run_dir_placeholder"))

        self.btn_start.setText(tr("btn_start"))
        self.btn_stop.setText(tr("btn_stop"))
        self.lbl_ver.setText(tr("version"))

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
            self, tr("btn_browse"), "",
            "CSV 文件 (*.csv);;所有文件 (*.*)",
        )
        if path:
            self.edit_csv.setText(path)

    def _on_dry_run_toggled(self, checked: bool):
        self.grp_sim.setEnabled(not checked)

    # ── Project integration ──

    def set_project(self, project: Any) -> None:
        """Display the current project name in the panel."""
        self._current_project_name = project.name
        self.lbl_project_name.setText(
            tr("project_status", name=project.name))
        self.lbl_project_name.setVisible(True)
        self.edit_project_dir.setText(str(project.path))
        # Auto-enable project checkbox when a project is open
        self.chk_project.setChecked(True)

    def clear_project(self) -> None:
        """Clear the project display."""
        self._current_project_name = None
        self.lbl_project_name.setText(tr("project_no_project"))
        self.edit_project_dir.clear()
        self.chk_project.setChecked(False)

    def restore_config(self, config: dict[str, str]) -> None:
        """Restore parameter panel state from a config dict.

        Args:
            config: Dict with keys like ``algorithm``, ``generations``, etc.
        """
        algo = config.get("algorithm", "")
        idx = self.cb_algo.findText(algo)
        if idx >= 0:
            self.cb_algo.setCurrentIndex(idx)

        try:
            self.spin_generations.setValue(int(config.get("generations", 50)))
        except (ValueError, TypeError):
            pass
        try:
            self.spin_population.setValue(int(config.get("population", 50)))
        except (ValueError, TypeError):
            pass
        try:
            self.spin_seed.setValue(int(config.get("seed", 1)))
        except (ValueError, TypeError):
            pass

        dry_run = config.get("dry_run", "True")
        self.chk_dry_run.setChecked(dry_run.lower() in ("true", "1", "yes"))

        plot = config.get("plot_enabled", "True")
        self.chk_plot.setChecked(plot.lower() in ("true", "1", "yes"))