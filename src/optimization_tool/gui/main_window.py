"""Main window — Cadence-inspired single-page layout with connection bar,
parameter panel, plots, results table, VNC area, and CIW-style log."""

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QGroupBox, QHBoxLayout, QLabel,
    QMainWindow, QMenuBar, QMessageBox, QPushButton, QSizePolicy,
    QSplitter, QSpinBox, QStatusBar, QToolBar, QVBoxLayout, QWidget,
    QLineEdit,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QFont, QActionGroup

from .widgets import ParamsPanel, PlotPanel, ResultsTable, LogPanel, VncWidget
from .workers import OptimizationWorker, OptimizationWorkerSignals
from .lang import tr, set_lang, get_lang, get_available_langs
from .dialogs import NewProjectDialog, OpenProjectDialog, LoadConfigDialog
from ..project import ProjectManager, Project


class MainWindow(QMainWindow):
    """Main application window with Cadence Virtuoso-inspired layout."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("window_title"))
        self.resize(1400, 900)

        self._worker = None
        self._is_connected = False
        self._plot_history = {"n_gen": [], "best_F": [], "all_F": [], "obj_names": None}

        # Project management
        self._project_manager = ProjectManager()
        self._current_project: Optional[Project] = None

        self._build_menubar()
        self._build_connection_bar()
        self._build_central()
        self._build_statusbar()

    # ── Menu bar ──

    def _build_menubar(self):
        mb = self.menuBar()
        self._menu_actions = {}

        # 文件
        self._menu_file = mb.addMenu(tr("menu_file"))
        self._act_new = QAction(tr("act_new"), self)
        self._act_new.triggered.connect(self._on_new_optimization)
        self._menu_file.addAction(self._act_new)
        self._menu_file.addSeparator()

        # ── Project submenu ──
        self._act_project_new = QAction(tr("act_project_new"), self)
        self._act_project_new.triggered.connect(self._on_project_new)
        self._menu_file.addAction(self._act_project_new)

        self._act_project_open = QAction(tr("act_project_open"), self)
        self._act_project_open.triggered.connect(self._on_project_open)
        self._menu_file.addAction(self._act_project_open)

        self._act_project_close = QAction(tr("act_project_close"), self)
        self._act_project_close.triggered.connect(self._on_project_close)
        self._act_project_close.setEnabled(False)
        self._menu_file.addAction(self._act_project_close)

        self._act_project_delete = QAction(tr("act_project_delete"), self)
        self._act_project_delete.triggered.connect(self._on_project_delete)
        self._menu_file.addAction(self._act_project_delete)

        self._menu_file.addSeparator()

        # ── Config save/load ──
        self._act_save_config = QAction(tr("act_save_config"), self)
        self._act_save_config.triggered.connect(self._on_save_config)
        self._act_save_config.setEnabled(False)
        self._menu_file.addAction(self._act_save_config)

        self._act_load_config = QAction(tr("act_load_config"), self)
        self._act_load_config.triggered.connect(self._on_load_config)
        self._menu_file.addAction(self._act_load_config)

        self._menu_file.addSeparator()
        self._act_exit = QAction(tr("act_exit"), self)
        self._act_exit.triggered.connect(self.close)
        self._menu_file.addAction(self._act_exit)

        # 优化
        self._menu_opt = mb.addMenu(tr("menu_opt"))
        self._act_start = QAction(tr("act_start"), self)
        self._act_start.triggered.connect(self._on_start)
        self._menu_opt.addAction(self._act_start)
        self._act_stop_act = QAction(tr("act_stop"), self)
        self._act_stop_act.triggered.connect(self._on_stop)
        self._menu_opt.addAction(self._act_stop_act)

        # 视图
        self._menu_view = mb.addMenu(tr("menu_view"))
        self._act_clear = QAction(tr("act_clear_log"), self)
        self._act_clear.triggered.connect(self._on_clear_log)
        self._menu_view.addAction(self._act_clear)
        self._act_reset = QAction(tr("act_reset_plots"), self)
        self._act_reset.triggered.connect(self._on_reset_plots)
        self._menu_view.addAction(self._act_reset)

        # 语言
        self._menu_lang = mb.addMenu(tr("menu_lang"))
        self._lang_group = QActionGroup(self)
        self._lang_group.setExclusive(True)
        self._lang_actions = {}
        for code in get_available_langs():
            label = tr(f"lang_{code}")
            act = QAction(label, self, checkable=True)
            act.setData(code)
            act.setChecked(code == get_lang())
            self._lang_group.addAction(act)
            self._menu_lang.addAction(act)
            self._lang_actions[code] = act
        self._lang_group.triggered.connect(self._on_language_changed)

        # 帮助
        self._menu_help = mb.addMenu(tr("menu_help"))
        self._act_about = QAction(tr("act_about"), self)
        self._act_about.triggered.connect(self._on_about)
        self._menu_help.addAction(self._act_about)

    # ── Connection toolbar ──

    def _build_connection_bar(self):
        bar = QToolBar(tr("menu_view"), self)
        bar.setMovable(False)
        bar.setIconSize(QSize(16, 16))
        self.addToolBar(Qt.TopToolBarArea, bar)

        # Status indicator
        self.lbl_conn_status = QLabel(tr("conn_status_disconnected"))
        self.lbl_conn_status.setObjectName("statusDisconnected")
        self.lbl_conn_status.setStyleSheet("font-weight: bold; font-size: 12px; padding: 2px 8px;")
        bar.addWidget(self.lbl_conn_status)

        bar.addSeparator()

        # Connection button (SSH + VNC combined)
        self.btn_connect = QPushButton(tr("conn_btn_connect"))
        self.btn_connect.setObjectName("btnConnect")
        self.btn_connect.setToolTip(tr("conn_btn_connect"))
        self.btn_connect.clicked.connect(self._on_toggle_connection)
        bar.addWidget(self.btn_connect)

        bar.addSeparator()

        # VNC launch button
        self.vnc = VncWidget()
        bar.addWidget(self.vnc)

        bar.addSeparator()

        # Spacer to push connection info to the right
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        bar.addWidget(spacer)

        # Remote info
        self.lbl_remote = QLabel("远程: 192.168.253.10")
        self.lbl_remote.setStyleSheet("color: #666666; font-size: 11px; padding: 2px 8px;")
        bar.addWidget(self.lbl_remote)

    # ── Central widget: single-page layout ──

    def _build_central(self):
        central = QWidget()
        self.setCentralWidget(central)

        hsplit = QSplitter(Qt.Horizontal, central)

        # ── Left: Parameter panel ──
        self.params = ParamsPanel()
        hsplit.addWidget(self.params)

        # ── Right: Vertical splitter with plots, table, log ──
        right_split = QSplitter(Qt.Vertical)

        # Plot area (convergence + pareto)
        self.plot = PlotPanel()
        right_split.addWidget(self.plot)

        # Results table
        self.results = ResultsTable()
        right_split.addWidget(self.results)

        # Log panel (CIW style)
        self.log = LogPanel()
        right_split.addWidget(self.log)

        # Set initial proportions: plot 40%, table 25%, log 35%
        right_split.setSizes([400, 250, 350])

        hsplit.addWidget(right_split)
        hsplit.setSizes([300, 1100])

        # Main layout
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(hsplit)

        # Connect signals
        self.params.btn_start.clicked.connect(self._on_start)
        self.params.btn_stop.clicked.connect(self._on_stop)
        self.results.solution_selected.connect(self._on_solution_selected)
        self.plot.pareto_point_selected.connect(self._on_solution_selected)

    # ─ Status bar ──

    _STATUS_COLORS = {
        "ready":   "#4CAF50",
        "waiting": "#2196F3",
        "running": "#FF9800",
        "done":    "#8BC34A",
        "pause":   "#9C27B0",
        "error":   "#F44336",
    }

    def _build_statusbar(self):
        sb = self.statusBar()

        # Project status label (leftmost)
        self.lbl_project = QLabel()
        self.lbl_project.setStyleSheet("padding: 1px 8px; font-size: 11px; color: #E65100;")
        sb.addWidget(self.lbl_project)
        self._update_project_label()

        # Separator
        sep0 = QFrame()
        sep0.setFrameShape(QFrame.VLine)
        sep0.setStyleSheet("color: #aaaaaa;")
        sb.addWidget(sep0)

        # Status indicator (colored square + label)
        status_frame = QHBoxLayout()
        status_frame.setContentsMargins(4, 0, 8, 0)
        status_frame.setSpacing(4)

        self.lbl_status_indicator = QLabel()
        self.lbl_status_indicator.setFixedSize(14, 14)
        self.lbl_status_indicator.setStyleSheet(
            f"background-color: {self._STATUS_COLORS['ready']}; border: 1px solid #333;"
        )
        status_frame.addWidget(self.lbl_status_indicator)

        self.lbl_status_text = QLabel(tr("status_ready"))
        self.lbl_status_text.setStyleSheet("font-size: 11px; padding: 1px 4px;")
        status_frame.addWidget(self.lbl_status_text)

        status_widget = QWidget()
        status_widget.setLayout(status_frame)
        sb.addWidget(status_widget)

        # Separator widget
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color: #aaaaaa;")
        sb.addWidget(sep)

        self.lbl_status_gen = QLabel(tr("status_gen", n="—"))
        self.lbl_status_eval = QLabel(tr("status_eval", n="—"))
        self.lbl_status_best = QLabel(tr("status_best", vals="—"))
        self.lbl_status_time = QLabel(tr("status_time", n="—"))

        for lbl in [self.lbl_status_gen, self.lbl_status_eval,
                     self.lbl_status_best, self.lbl_status_time]:
            lbl.setStyleSheet("padding: 1px 12px; font-size: 12px;")
            sb.addPermanentWidget(lbl)

    # ── Language switching ──

    def _on_language_changed(self, act: QAction):
        """Switch UI language."""
        code = act.data()
        if code == get_lang():
            return
        set_lang(code)
        self.retranslate_ui()

    def retranslate_ui(self):
        """Update all UI strings to current language."""
        # Window title
        if self._current_project:
            self.setWindowTitle(tr("window_title") + " — " +
                                tr("project_status", name=self._current_project.name))
        else:
            self.setWindowTitle(tr("window_title"))

        # Menu bar
        self._menu_file.setTitle(tr("menu_file"))
        self._menu_opt.setTitle(tr("menu_opt"))
        self._menu_view.setTitle(tr("menu_view"))
        self._menu_help.setTitle(tr("menu_help"))
        self._menu_lang.setTitle(tr("menu_lang"))
        self._act_new.setText(tr("act_new"))
        self._act_project_new.setText(tr("act_project_new"))
        self._act_project_open.setText(tr("act_project_open"))
        self._act_project_close.setText(tr("act_project_close"))
        self._act_project_delete.setText(tr("act_project_delete"))
        self._act_save_config.setText(tr("act_save_config"))
        self._act_load_config.setText(tr("act_load_config"))
        self._act_exit.setText(tr("act_exit"))
        self._act_start.setText(tr("act_start"))
        self._act_stop_act.setText(tr("act_stop"))
        self._act_clear.setText(tr("act_clear_log"))
        self._act_reset.setText(tr("act_reset_plots"))
        self._act_about.setText(tr("act_about"))
        for code, act in self._lang_actions.items():
            act.setText(tr(f"lang_{code}"))

        # Connection bar
        if self._is_connected:
            self.lbl_conn_status.setText(tr("conn_status_connected"))
        else:
            self.lbl_conn_status.setText(tr("conn_status_disconnected"))
        if hasattr(self, 'btn_connect'):
            if self._is_connected:
                self.btn_connect.setText(tr("conn_btn_disconnect"))
            else:
                self.btn_connect.setText(tr("conn_btn_connect"))

        # Status bar
        self.lbl_status_text.setText(tr("status_ready"))
        self._update_project_label()

        # Child widgets
        self.params.retranslate_ui()
        self.plot.retranslate_ui()
        self.results.retranslate_ui()
        self.log.retranslate_ui()
        self.vnc.retranslate_ui()

    def set_status(self, state: str, text: str = ""):
        """Update the status indicator color and text.

        Args:
            state: One of 'ready', 'waiting', 'running', 'done', 'pause', 'error'
            text: Optional status text to display next to the indicator
        """
        color = self._STATUS_COLORS.get(state, "#808080")
        self.lbl_status_indicator.setStyleSheet(
            f"background-color: {color}; border: 1px solid #333;"
        )
        if text:
            self.lbl_status_text.setText(text)
        else:
            key = f"status_{state}"
            self.lbl_status_text.setText(tr(key, state.capitalize()))

    # ── Connection logic ──

    def _on_toggle_connection(self):
        if self._is_connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        self.log.info("正在连接 Virtuoso (SSH)...")
        self.btn_connect.setEnabled(False)
        self.btn_connect.setText(tr("conn_connecting"))

        try:
            from virtuoso_bridge import VirtuosoClient
            client = VirtuosoClient.from_env()
            # Test connection
            result = client.execute_skill('maeGetSetup()')
            test_name = result.output.strip()
            self.log.ok(f"Virtuoso 已连接 — 当前测试: {test_name[:60]}")

            self._is_connected = True
            self.lbl_conn_status.setText(tr("conn_status_connected"))
            self.lbl_conn_status.setObjectName("statusConnected")
            self.lbl_conn_status.style().unpolish(self.lbl_conn_status)
            self.lbl_conn_status.style().polish(self.lbl_conn_status)
            self.btn_connect.setText(tr("conn_btn_disconnect"))

            # Store client for later use
            self._virtuoso_client = client

            # Auto-enable start button
            self.params.btn_start.setEnabled(True)

        except Exception as exc:
            self.log.error(f"连接失败: {exc}")
            self.lbl_conn_status.setText("● Virtuoso: 失败")
            self.lbl_conn_status.setObjectName("statusDisconnected")
            self.lbl_conn_status.style().unpolish(self.lbl_conn_status)
            self.lbl_conn_status.style().polish(self.lbl_conn_status)
            QMessageBox.warning(self, "连接失败", f"无法连接到 Virtuoso:\n{exc}")
        finally:
            self.btn_connect.setEnabled(True)

    def _disconnect(self):
        self._is_connected = False
        self._virtuoso_client = None
        self.lbl_conn_status.setText(tr("conn_status_disconnected"))
        self.lbl_conn_status.setObjectName("statusDisconnected")
        self.lbl_conn_status.style().unpolish(self.lbl_conn_status)
        self.lbl_conn_status.style().polish(self.lbl_conn_status)
        self.btn_connect.setText(tr("conn_btn_connect"))
        self.params.btn_start.setEnabled(False)
        self.log.info("已断开 Virtuoso 连接")

    # ── Project management ──

    def _update_project_label(self):
        """Update the project status label in the status bar."""
        if self._current_project:
            self.lbl_project.setText(tr("project_status", name=self._current_project.name))
            self.lbl_project.setVisible(True)
        else:
            self.lbl_project.setText(tr("project_no_project"))
            self.lbl_project.setVisible(True)

    def _on_project_new(self):
        """Open the New Project dialog and create a project."""
        dlg = NewProjectDialog(str(self._project_manager.root_path), self)
        if dlg.exec():
            name = dlg.project_name
            root = dlg.selected_root
            try:
                # Update root path if changed
                self._project_manager.set_root_path(root)
                proj = self._project_manager.create_project(name)
                self._current_project = proj
                self._project_manager.current_project = proj
                self._update_project_label()
                self._act_project_close.setEnabled(True)
                self._act_save_config.setEnabled(True)
                # Update params panel
                self.params.set_project(proj)
                # Auto-set run directory to project path
                self.params.edit_run_dir.setText(str(proj.path))
                self.log.ok(tr("msg_project_created", name=name))
            except FileExistsError:
                QMessageBox.warning(self, tr("project_new_title"),
                                    tr("msg_project_exists", name=name))
            except ValueError as exc:
                QMessageBox.warning(self, tr("project_new_title"), str(exc))

    def _on_project_open(self):
        """Open the Project list dialog and open a project."""
        projects = self._project_manager.list_projects()
        if not projects:
            QMessageBox.information(self, tr("project_open_title"),
                                    "No projects found. Create one first.")
            return
        dlg = OpenProjectDialog(projects, self)
        if dlg.exec():
            name = dlg.selected_name
            try:
                proj = self._project_manager.open_project(name)
                self._current_project = proj
                self._update_project_label()
                self._act_project_close.setEnabled(True)
                self._act_save_config.setEnabled(True)
                self.params.set_project(proj)
                # Auto-set CSV path to project's specs.csv if it exists
                specs_csv = proj.path / "I_scripts" / "specs.csv"
                if specs_csv.exists():
                    self.params.edit_csv.setText(str(specs_csv))
                # Auto-set run directory to project path
                self.params.edit_run_dir.setText(str(proj.path))
                self.log.ok(tr("msg_project_opened", name=name))
            except FileNotFoundError as exc:
                QMessageBox.warning(self, tr("project_open_title"), str(exc))

    def _on_project_close(self):
        """Close the current project."""
        if self._current_project:
            name = self._current_project.name
            self._project_manager.close_project()
            self._current_project = None
            self.params.clear_project()
            # Clear auto-set paths
            self.params.edit_csv.clear()
            self.params.edit_run_dir.clear()
            self._update_project_label()
            self._act_project_close.setEnabled(False)
            self._act_save_config.setEnabled(False)
            self.log.info(tr("msg_project_closed"))

    def _on_project_delete(self):
        """Delete the current (or selected) project."""
        if not self._current_project:
            QMessageBox.information(self, tr("project_delete_title"),
                                    "No project is currently open.")
            return

        name = self._current_project.name
        path = str(self._current_project.path)
        ret = QMessageBox.question(
            self, tr("project_delete_title"),
            tr("project_delete_confirm", name=name) + "\n" +
            tr("project_delete_path", path=path),
            QMessageBox.Yes | QMessageBox.No,
        )
        if ret != QMessageBox.Yes:
            return

        try:
            self._project_manager.delete_project(name)
            self._current_project = None
            self.params.clear_project()
            self._update_project_label()
            self._act_project_close.setEnabled(False)
            self._act_save_config.setEnabled(False)
            self.log.info(tr("msg_project_deleted", name=name))
        except Exception as exc:
            QMessageBox.critical(self, tr("project_delete_title"), str(exc))

    def _on_save_config(self):
        """Save the current parameter panel configuration to the project."""
        if not self._current_project:
            return
        config = self._build_config_dict()
        cfg_path = self._current_project.path / "config.txt"
        lines = [f"{k}={v}" for k, v in config.items()]
        cfg_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.log.info(tr("msg_config_saved"))

    def _on_load_config(self):
        """Load a config.txt from a previous run and restore params."""
        dlg = LoadConfigDialog(self)
        if dlg.exec() and dlg.config:
            cfg = dlg.config
            try:
                self.params.restore_config(cfg)
                self.log.info(tr("msg_config_loaded"))
            except Exception as exc:
                self.log.error(tr("msg_config_load_fail", exc=str(exc)))

    def _build_config_dict(self) -> dict:
        """Build a configuration dict from the current params panel state."""
        return {
            "algorithm": self.params.algo,
            "generations": str(self.params.generations),
            "population": str(self.params.population),
            "seed": str(self.params.seed),
            "dry_run": str(self.params.dry_run),
            "plot_enabled": str(self.params.plot_enabled),
            "verbose": str(self.params.verbose),
        }

    # ── Optimization control ──

    def _on_start(self):
        if not self._is_connected and not self.params.dry_run:
            ret = QMessageBox.question(
                self, tr("msg_no_virtuoso"),
                tr("msg_confirm_dry"),
                QMessageBox.Yes | QMessageBox.No,
            )
            if ret != QMessageBox.Yes:
                return

        if not self.params.dry_run and not self.params.csv_filename:
            QMessageBox.warning(
                self, tr("msg_missing_csv"),
                tr("msg_specify_csv"),
            )
            return

        self.params.btn_start.setEnabled(False)
        self.params.btn_stop.setEnabled(True)
        self.params.cb_algo.setEnabled(False)
        self.params.spin_generations.setEnabled(False)
        self.params.spin_population.setEnabled(False)
        self.params.spin_seed.setEnabled(False)

        self.set_status("running", tr("status_running"))

        self.log.info("=" * 50)
        self.log.info(tr("msg_opt_start"))

        # Clear previous results
        self.results.clear_data()
        self.plot.clear_plots()
        self._plot_history = {"n_gen": [], "best_F": [], "all_F": [], "obj_names": None}

        # Build parameters
        kwargs = {
            "generations": self.params.generations,
            "pop_size": self.params.population,
            "dry_run": self.params.dry_run,
            "seed": self.params.seed,
            "algo": self.params.algo,
            "verbose": self.params.verbose,
            "plot": self.params.plot_enabled,
            "plot_dir": ".",
            "show": False,
        }
        if not self.params.dry_run:
            csv_path = self.params.csv_filename
            if csv_path:
                kwargs["csv_filename"] = csv_path
            kwargs["run_directory"] = self.params.run_directory

        # Project integration: if a project is open, auto-save results
        if self._current_project is not None:
            kwargs["project_obj"] = self._current_project
            # Also save config to the project
            self._on_save_config()
        elif self.params.project_enabled:
            proj = self.params.project_dir or "optimization_project"
            kwargs["project_dir"] = proj

        self._worker = OptimizationWorker()
        self._worker.configure(**kwargs)
        self._worker.signals.log.connect(self._on_worker_log)
        self._worker.signals.progress.connect(self._on_worker_progress)
        self._worker.signals.plot_update.connect(self._on_worker_plot_update)
        self._worker.signals.finished.connect(self._on_worker_finished)
        self._worker.signals.error.connect(self._on_worker_error)
        self._worker.start()

        self.log.info(tr("msg_opt_running"))

    def _on_stop(self):
        if self._worker and self._worker.isRunning():
            self._worker.abort()
            self.set_status("pause", tr("status_pause"))
            self.log.warn(tr("msg_opt_stopped"))

    def _on_worker_log(self, message: str, level: str):
        getattr(self.log, level, self.log.info)(message)

    def _on_worker_progress(self, gen: int, n_eval: int, best_F: list, best_X: list):
        # Update status bar
        self.lbl_status_gen.setText(tr("status_gen", n=str(gen)))
        self.lbl_status_eval.setText(tr("status_eval", n=str(n_eval)))
        if best_F:
            best_str = ", ".join(f"{v:.4g}" for v in best_F)
            self.lbl_status_best.setText(tr("status_best", vals=best_str))

    def _on_worker_plot_update(self, data: dict):
        """Update convergence + Pareto plots from worker callback data.

        The worker emits per-generation data (single gen per call), so
        we accumulate on the GUI side to build a growing curve.
        """
        n_gen = data.get("n_gen", [])
        best_F = data.get("best_F", [])
        all_F = data.get("all_F", [])
        obj_names = data.get("obj_names", None)

        # Store obj_names for later use
        if obj_names is not None:
            self._plot_history["obj_names"] = obj_names

        # Accumulate — worker sends [gen], [best_F], [all_F] as single-element lists
        self._plot_history["n_gen"].extend(n_gen)
        self._plot_history["best_F"].extend(best_F)
        self._plot_history["all_F"].extend(all_F)

        # Get accumulated data
        acc_gen = self._plot_history["n_gen"]
        acc_best_F = self._plot_history["best_F"]
        acc_all_F = self._plot_history["all_F"]
        obj_names = self._plot_history["obj_names"]

        # Update convergence plot
        if acc_gen and acc_best_F:
            n_obj = len(acc_best_F[0]) if acc_best_F else 1
            if obj_names is None:
                obj_names = [f"Obj{i+1}" for i in range(n_obj)]
            self.plot.update_convergence(acc_gen, acc_best_F, obj_names)

        # Update Pareto plot (multi-objective: each F entry has ≥2 values)
        if len(acc_all_F) > 0 and isinstance(acc_all_F[-1], (list, tuple)) and len(acc_all_F[-1]) >= 2:
            F_all = []
            for gen_f in acc_all_F:
                F_all.extend(gen_f)
            if obj_names is None:
                obj_names = ["Obj1", "Obj2"]
            self.plot.update_pareto(F_all, obj_names[:2])
            self.plot.update_history(F_all, obj_names[:2])

    def _on_worker_finished(self, result):
        self._finish_optimization()
        self.set_status("done", tr("msg_opt_done"))
        if result is not None:
            try:
                # Extract Pareto results
                cb = getattr(result, "callback_data", {}) or {}
                X = result.X.tolist() if hasattr(result.X, "tolist") else list(result.X or [])
                F = result.F.tolist() if hasattr(result.F, "tolist") else list(result.F or [])

                var_names = cb.get("var_names", [])
                obj_names = cb.get("obj_names", [])
                specs = cb.get("specs", [])

                # Update results table (with spec-aware de-normalization)
                self.results.set_data(var_names, obj_names, X, F, specs=specs)

                # Update Pareto plot (skip if single-objective)
                if len(F) > 0 and len(F[0]) >= 2:
                    p_names = obj_names if len(obj_names) >= 2 else ["Obj1", "Obj2"]
                    self.plot.update_pareto(F, p_names)
                    # 存储 Pareto 变量数据以支持点击选取
                    if X and var_names:
                        self.plot.set_pareto_data(X, F, var_names, p_names)
                else:
                    self.plot.update_pareto(F, ["Obj1", "Obj2"])

                # Update all-history scatter
                acc_all_F = self._plot_history.get("all_F", [])
                if acc_all_F:
                    flat = []
                    for gen_f in acc_all_F:
                        flat.extend(gen_f)
                    h_names = obj_names if len(obj_names) >= 2 else ["Obj1", "Obj2"]
                    self.plot.update_history(flat, h_names)

                self.log.ok(tr("msg_opt_ok", n=str(len(F) if F else 0)))

            except Exception as exc:
                self.log.warn(tr("msg_results_parse", exc=str(exc)))

    def _on_worker_error(self, message: str):
        self._finish_optimization()
        self.set_status("error", tr("status_error"))
        QMessageBox.critical(self, tr("msg_opt_error"), message)

    def _finish_optimization(self):
        self.params.btn_start.setEnabled(True)
        self.params.btn_stop.setEnabled(False)
        self.params.cb_algo.setEnabled(True)
        self.params.spin_generations.setEnabled(True)
        self.params.spin_population.setEnabled(True)
        self.params.spin_seed.setEnabled(True)

    # ── Selection → circuit ──

    def _on_solution_selected(self, var_names: list, x_vals: list):
        """将用户选中的 Pareto 解写回 Virtuoso 电路。"""
        if not self._is_connected or not hasattr(self, '_virtuoso_client'):
            QMessageBox.warning(self, tr("msg_not_connected"),
                                tr("msg_connect_first"))
            return

        client = self._virtuoso_client
        try:
            for name, val in zip(var_names, x_vals):
                client.execute_skill(f'maeSetVar("{name}" {val})')
            self.log.ok(tr("msg_upload_ok", n=str(len(var_names))))
            for n, v in zip(var_names, x_vals):
                self.log.info(f"  {n} = {v:.6e}")
            # 刷新仿真视图
            client.execute_skill("maeUpdateOutputView()")
            self.log.info(tr("msg_circuit_updated"))
        except Exception as exc:
            self.log.error(tr("msg_upload_fail", exc=str(exc)))

    # ── Menu actions ──

    def _on_new_optimization(self):
        self.results.clear_data()
        self.plot.clear_plots()
        self.log.clear()
        self._plot_history = {"n_gen": [], "best_F": [], "all_F": [], "obj_names": None}
        self.lbl_status_gen.setText(tr("status_gen", n="—"))
        self.lbl_status_eval.setText(tr("status_eval", n="—"))
        self.lbl_status_best.setText(tr("status_best", vals="—"))
        self.lbl_status_time.setText(tr("status_time", n="—"))
        self.set_status("ready", tr("status_ready"))
        self.log.info(tr("msg_reset"))

    def _on_clear_log(self):
        self.log.clear()

    def _on_reset_plots(self):
        self.plot.clear_plots()

    def _on_about(self):
        QMessageBox.about(
            self, tr("act_about"),
            "基于 pymoo 进化算法 + Virtuoso Maestro<br>"
            "用于模拟 IC 电路设计的多目标优化。<br><br>"
            "引擎: pymoo (GA/NSGA2/DE/PSO/CMAES/...)<br>"
            "后端: Cadence Virtuoso / Spectre<br>"
            "连接: virtuoso-bridge (SSH)",
        )