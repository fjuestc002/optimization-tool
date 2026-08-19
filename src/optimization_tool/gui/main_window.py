"""Main window — Cadence-inspired single-page layout with connection bar,
parameter panel, plots, results table, VNC area, and CIW-style log."""

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QGroupBox, QHBoxLayout, QLabel,
    QMainWindow, QMenuBar, QMessageBox, QPushButton, QSizePolicy,
    QSplitter, QSpinBox, QStatusBar, QToolBar, QVBoxLayout, QWidget,
    QLineEdit,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QFont

from .widgets import ParamsPanel, PlotPanel, ResultsTable, LogPanel, VncWidget
from .workers import OptimizationWorker, OptimizationWorkerSignals


class MainWindow(QMainWindow):
    """Main application window with Cadence Virtuoso-inspired layout."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Prof. Fang Jian 优化工具 — Virtuoso + pymoo")
        self.resize(1400, 900)

        self._worker = None
        self._is_connected = False
        self._vnc_connected = False
        self._plot_history = {"n_gen": [], "best_F": [], "all_F": [], "obj_names": None}

        self._build_menubar()
        self._build_connection_bar()
        self._build_central()
        self._build_statusbar()

    # ── Menu bar ──

    def _build_menubar(self):
        mb = self.menuBar()

        # 文件
        menu_file = mb.addMenu("文件(&F)")
        act_new = QAction("新建优化", self)
        act_new.triggered.connect(self._on_new_optimization)
        menu_file.addAction(act_new)
        menu_file.addSeparator()
        act_exit = QAction("退出(&X)", self)
        act_exit.triggered.connect(self.close)
        menu_file.addAction(act_exit)

        # 优化
        menu_opt = mb.addMenu("优化(&O)")
        act_start = QAction("开始优化", self)
        act_start.triggered.connect(self._on_start)
        menu_opt.addAction(act_start)
        act_stop = QAction("停止", self)
        act_stop.triggered.connect(self._on_stop)
        menu_opt.addAction(act_stop)

        # 视图
        menu_view = mb.addMenu("视图(&V)")
        act_clear = QAction("清除日志", self)
        act_clear.triggered.connect(self._on_clear_log)
        menu_view.addAction(act_clear)
        act_reset = QAction("重置图表", self)
        act_reset.triggered.connect(self._on_reset_plots)
        menu_view.addAction(act_reset)

        # 帮助
        menu_help = mb.addMenu("帮助(&H)")
        act_about = QAction("关于", self)
        act_about.triggered.connect(self._on_about)
        menu_help.addAction(act_about)

    # ── Connection toolbar ──

    def _build_connection_bar(self):
        bar = QToolBar("连接", self)
        bar.setMovable(False)
        bar.setIconSize(QSize(16, 16))
        self.addToolBar(Qt.TopToolBarArea, bar)

        # Status indicator
        self.lbl_conn_status = QLabel("● Virtuoso: 未连接")
        self.lbl_conn_status.setObjectName("statusDisconnected")
        self.lbl_conn_status.setStyleSheet("font-weight: bold; font-size: 12px; padding: 2px 8px;")
        bar.addWidget(self.lbl_conn_status)

        bar.addSeparator()

        # Connection button (SSH + VNC combined)
        self.btn_connect = QPushButton("🔌 连接")
        self.btn_connect.setObjectName("btnConnect")
        self.btn_connect.setToolTip("点击连接 Virtuoso (SSH) + VNC")
        self.btn_connect.clicked.connect(self._on_toggle_connection)
        bar.addWidget(self.btn_connect)

        bar.addSeparator()

        # VNC status label
        self.lbl_vnc_status = QLabel("VNC: 未连接")
        self.lbl_vnc_status.setStyleSheet("color: #808080; font-size: 12px; padding: 2px 8px;")
        bar.addWidget(self.lbl_vnc_status)

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

        # ── Right: Vertical splitter with plots, table, VNC, log ──
        right_split = QSplitter(Qt.Vertical)

        # Plot area (convergence + pareto)
        self.plot = PlotPanel()
        right_split.addWidget(self.plot)

        # Results table
        self.results = ResultsTable()
        right_split.addWidget(self.results)

        # VNC area (collapsible)
        self.vnc = VncWidget()
        right_split.addWidget(self.vnc)

        # Log panel (CIW style)
        self.log = LogPanel()
        right_split.addWidget(self.log)

        # Set initial proportions: plot 35%, table 20%, VNC 15%, log 30%
        right_split.setSizes([350, 200, 150, 300])

        hsplit.addWidget(right_split)
        hsplit.setSizes([300, 1100])

        # Main layout
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(hsplit)

        # Connect signals
        self.params.btn_start.clicked.connect(self._on_start)
        self.params.btn_stop.clicked.connect(self._on_stop)

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

        self.lbl_status_text = QLabel("就绪")
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

        self.lbl_status_gen = QLabel("代数: —")
        self.lbl_status_eval = QLabel("评估: —")
        self.lbl_status_best = QLabel("最佳: —")
        self.lbl_status_time = QLabel("耗时: —")

        for lbl in [self.lbl_status_gen, self.lbl_status_eval,
                     self.lbl_status_best, self.lbl_status_time]:
            lbl.setStyleSheet("padding: 1px 12px; font-size: 12px;")
            sb.addPermanentWidget(lbl)

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
            self.lbl_status_text.setText(state.capitalize())

    # ── Connection logic ──

    def _on_toggle_connection(self):
        if self._is_connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        self.log.info("正在连接 Virtuoso (SSH)...")
        self.btn_connect.setEnabled(False)
        self.btn_connect.setText("连接中...")

        try:
            from virtuoso_bridge import VirtuosoClient
            client = VirtuosoClient.from_env()
            # Test connection
            result = client.execute_skill('maeGetSetup()')
            test_name = result.output.strip()
            self.log.ok(f"Virtuoso 已连接 — 当前测试: {test_name[:60]}")

            self._is_connected = True
            self.lbl_conn_status.setText("● Virtuoso: 已连接")
            self.lbl_conn_status.setObjectName("statusConnected")
            self.lbl_conn_status.style().unpolish(self.lbl_conn_status)
            self.lbl_conn_status.style().polish(self.lbl_conn_status)
            self.btn_connect.setText("🔌 断开")

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
        self.lbl_conn_status.setText("● Virtuoso: 未连接")
        self.lbl_conn_status.setObjectName("statusDisconnected")
        self.lbl_conn_status.style().unpolish(self.lbl_conn_status)
        self.lbl_conn_status.style().polish(self.lbl_conn_status)
        self.btn_connect.setText("🔌 连接")
        self.params.btn_start.setEnabled(False)
        self.log.info("已断开 Virtuoso 连接")

    # ── Optimization control ──

    def _on_start(self):
        if not self._is_connected and not self.params.dry_run:
            ret = QMessageBox.question(
                self, "未连接 Virtuoso",
                "Virtuoso 未连接，非 Dry-Run 模式需要连接才能运行。\n"
                "是否继续？（仅限 Dry-Run 模式）",
                QMessageBox.Yes | QMessageBox.No,
            )
            if ret != QMessageBox.Yes:
                return

        if not self.params.dry_run and not self.params.csv_filename:
            QMessageBox.warning(
                self, "缺少 CSV 文件",
                "非 Dry-Run 模式需要指定 CSV 文件路径（仿真规格定义）。\n"
                "请在「仿真设置」中填写 CSV 文件路径。",
            )
            return

 #       if not self.params.dry_run and self.params.csv_filename:
 #           from pathlib import Path
 #           if not Path(self.params.csv_filename).exists():
 #               QMessageBox.warning(
 #                   self, "CSV 文件不存在",
 #                   f"指定的 CSV 文件不存在:\n{self.params.csv_filename}\n\n"
 #                   "请检查路径是否正确，或先通过 Maestro 导出 CSV 文件。",
 #               )
 #               return

        self.params.btn_start.setEnabled(False)
        self.params.btn_stop.setEnabled(True)
        self.params.cb_algo.setEnabled(False)
        self.params.spin_generations.setEnabled(False)
        self.params.spin_population.setEnabled(False)
        self.params.spin_seed.setEnabled(False)

        self.set_status("running", "优化运行中")

        self.log.info("=" * 50)
        self.log.info("初始化优化...")

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
        if self.params.project_enabled:
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

        self.log.info("优化正在后台运行...")

    def _on_stop(self):
        if self._worker and self._worker.isRunning():
            self._worker.abort()
            self.set_status("pause", "正在停止")
            self.log.warn("正在停止优化...")
            # Don't disable stop button yet — wait for actual finish

    def _on_worker_log(self, message: str, level: str):
        getattr(self.log, level, self.log.info)(message)

    def _on_worker_progress(self, gen: int, n_eval: int, best_F: list, best_X: list):
        # Update status bar
        self.lbl_status_gen.setText(f"代数: {gen}")
        self.lbl_status_eval.setText(f"评估: {n_eval}")
        if best_F:
            best_str = ", ".join(f"{v:.4g}" for v in best_F)
            self.lbl_status_best.setText(f"最佳: [{best_str}]")

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

    def _on_worker_finished(self, result):
        self._finish_optimization()
        self.set_status("done", "优化完成")
        if result is not None:
            try:
                # Extract Pareto results
                cb = getattr(result, "callback_data", {}) or {}
                X = result.X.tolist() if hasattr(result.X, "tolist") else list(result.X or [])
                F = result.F.tolist() if hasattr(result.F, "tolist") else list(result.F or [])

                var_names = cb.get("var_names", [])
                obj_names = cb.get("obj_names", [])

                # Update results table
                self.results.set_data(var_names, obj_names, X, F)

                # Update Pareto plot (skip if single-objective)
                if len(F) > 0 and len(F[0]) >= 2:
                    p_names = obj_names if len(obj_names) >= 2 else ["Obj1", "Obj2"]
                    self.plot.update_pareto(F, p_names)
                else:
                    self.plot.update_pareto(F, ["Obj1", "Obj2"])

                self.log.ok(f"优化完成 — 解数: {len(F)}, 目标: {len(F[0]) if F else 0}")

            except Exception as exc:
                self.log.warn(f"结果解析: {exc}")

    def _on_worker_error(self, message: str):
        self._finish_optimization()
        self.set_status("error", "错误")
        QMessageBox.critical(self, "优化错误", message)

    def _finish_optimization(self):
        self.params.btn_start.setEnabled(True)
        self.params.btn_stop.setEnabled(False)
        self.params.cb_algo.setEnabled(True)
        self.params.spin_generations.setEnabled(True)
        self.params.spin_population.setEnabled(True)
        self.params.spin_seed.setEnabled(True)

    # ── Menu actions ──

    def _on_new_optimization(self):
        self.results.clear_data()
        self.plot.clear_plots()
        self.log.clear()
        self._plot_history = {"n_gen": [], "best_F": [], "all_F": [], "obj_names": None}
        self.lbl_status_gen.setText("代数: —")
        self.lbl_status_eval.setText("评估: —")
        self.lbl_status_best.setText("最佳: —")
        self.lbl_status_time.setText("耗时: —")
        self.set_status("ready", "就绪")
        self.log.info("已重置 — 准备新优化")

    def _on_clear_log(self):
        self.log.clear()

    def _on_reset_plots(self):
        self.plot.clear_plots()

    def _on_about(self):
        QMessageBox.about(
#            self, "关于 DClaw 优化工具",
#            "<b>DClaw 优化工具</b> v0.1<br><br>"
            "基于 pymoo 进化算法 + Virtuoso Maestro<br>"
#            "用于模拟 IC 电路设计的多目标优化。<br><br>"
#            "引擎: pymoo (GA/NSGA2/DE/PSO/CMAES/...)<br>"
#            "后端: Cadence Virtuoso / Spectre<br>"
#            "连接: virtuoso-bridge (SSH)<br><br>"
#            "杭州点壹下通讯科技有限公司"
        )