"""Language / i18n support for the optimization GUI.

Usage:
    from .lang import tr, set_lang, get_lang

    # In widget code:
    label.setText(tr("convergence_title", "收敛曲线"))
"""

# ── Translation dictionary ──────────────────────────────────────────────────

_STRINGS = {
    "zh": {
        # ── Main window ──
        "window_title": "Prof. Fang Jian 优化工具 — Virtuoso + pymoo",
        "menu_file": "文件(&F)",
        "menu_opt": "优化(&O)",
        "menu_view": "视图(&V)",
        "menu_help": "帮助(&H)",
        "menu_lang": "语言(&L)",
        "act_new": "新建优化",
        "act_project_new": "新建项目",
        "act_project_open": "打开项目",
        "act_project_close": "关闭项目",
        "act_project_delete": "删除项目",
        "act_save_config": "保存配置",
        "act_load_config": "加载配置...",
        "act_exit": "退出(&X)",
        "act_start": "开始优化",
        "act_stop": "停止",
        "act_clear_log": "清除日志",
        "act_reset_plots": "重置图表",
        "act_about": "关于",
        "lang_zh": "中文",
        "lang_en": "English",
        "conn_status_disconnected": "● Virtuoso: 未连接",
        "conn_status_connected": "● Virtuoso: 已连接",
        "conn_btn_connect": "🔌 连接",
        "conn_btn_disconnect": "🔌 断开",
        "conn_connecting": "连接中...",
        "status_ready": "就绪",
        "status_running": "优化运行中",
        "status_done": "优化完成",
        "status_pause": "正在停止",
        "status_error": "错误",
        "status_gen": "代数: {n}",
        "status_eval": "评估: {n}",
        "status_best": "最佳: [{vals}]",
        "status_time": "耗时: {n}",

        # ── Params panel ──
        "grp_algo": "算法设置",
        "lbl_algo": "优化算法:",
        "lbl_generations": "代数:",
        "lbl_population": "种群:",
        "lbl_seed": "随机种子:",
        "grp_mode": "运行模式",
        "chk_dry_run": "Dry-Run 模式（无真实仿真）",
        "chk_plot": "生成实时图表",
        "chk_project": "启用项目存档",
        "chk_verbose": "详细日志输出",
        "grp_proj": "项目目录",
        "proj_placeholder": "留空 = 不存档",
        "grp_sim": "仿真设置（非 Dry-Run）",
        "lbl_csv": "CSV 文件路径:",
        "csv_placeholder": "outputs_xxx_maestro.csv",
        "btn_browse": "浏览...",
        "lbl_run_dir": "运行目录:",
        "run_dir_placeholder": ".",
        "btn_start": "▶ 开始优化",
        "btn_stop": "■ 停止",
        "version": "Prof. Fang Jian 优化工具 v0.1",
        "algo_tooltip": (
            "pymoo 进化算法 — NSGA2/3/SPEA2/MOEAD 适合多目标, GA/DE/PSO 适合单目标\n"
            "贝叶斯优化 — bayes_gp 样本效率高, bayes_rf 鲁棒, bayes_mo 多目标"
        ),

        # ── Plot panel ──
        "plot_view": "图表视图:",
        "mode_both": "收敛图 + Pareto 图",
        "mode_convergence": "收敛图",
        "mode_pareto": "Pareto 图",
        "convergence_title": "收敛曲线",
        "convergence_xlabel": "代数",
        "convergence_ylabel": "归一化目标值",
        "history_title": "全部历史",
        "pareto_title": "Pareto 前沿",
        "pareto_xlabel": "目标 1",
        "pareto_ylabel": "目标 2",

        # ── Results table ──
        "results_title": "Pareto 最优解集",
        "col_var": "变量: {n}",
        "col_obj": "目标: {n}",
        "col_action": "Action",
        "btn_select": "Backannotate to CDS",
        "btn_select_tooltip": "将 Pareto 最优解回传至 Virtuoso 电路",

        # ── Log panel ──
        "log_title": "日志输出 (CIW)",

        # ── VNC widget ──
        "vnc_title": "VNC 查看器",
        "vnc_launch_btn": "启动 VNC Viewer",
        "vnc_launch_hint": "启动外部 VNC Viewer，连接配置请在 VNC Viewer 中操作",
        "vnc_not_found": "未找到 VNC Viewer",
        "vnc_not_found_msg": "未找到 VNC Viewer (vncviewer.exe)。\n请安装 RealVNC Viewer 或将其所在目录加入系统 PATH。",
        "vnc_error_title": "启动失败",
        "vnc_launch_failed": "启动 VNC Viewer 失败:",

        # ── Messages ──
        "msg_not_connected": "未连接",
        "msg_connect_first": "请先连接 Virtuoso，再回传变量。",
        "msg_upload_ok": "已回传 {n} 个变量到电路",
        "msg_upload_fail": "回传失败: {exc}",
        "msg_circuit_updated": "电路参数已更新，可重新运行仿真。",
        "msg_no_virtuoso": "未连接 Virtuoso",
        "msg_confirm_dry": (
            "Virtuoso 未连接，非 Dry-Run 模式需要连接才能运行。\n"
            "是否继续？（仅限 Dry-Run 模式）"
        ),
        "msg_missing_csv": "缺少 CSV 文件",
        "msg_specify_csv": (
            "非 Dry-Run 模式需要指定 CSV 文件路径（仿真规格定义）。\n"
            "请在「仿真设置」中填写 CSV 文件路径。"
        ),
        "msg_opt_running": "优化正在后台运行...",
        "msg_opt_done": "优化完成",
        "msg_opt_aborted": "优化已中止",
        "msg_opt_stopped": "优化已停止",
        "msg_opt_error": "优化错误",
        "msg_opt_start": "初始化优化...",
        "msg_opt_ok": "优化完成 ✓  Pareto 解数: {n}",
        "msg_results_parse": "结果解析: {exc}",
        "msg_reset": "已重置 — 准备新优化",

        # ── Project management ──
        "project_status": "项目: {name}",
        "project_no_project": "未打开项目",

        # ── New Project Dialog ──
        "project_new_title": "新建项目",
        "project_new_name": "项目名称:",
        "project_new_root": "运行路径:",
        "project_new_btn_browse": "浏览...",
        "project_new_btn_ok": "创建",
        "project_new_btn_cancel": "取消",

        # ── Open Project Dialog ──
        "project_open_title": "打开项目",
        "project_open_list": "选择项目:",
        "project_open_btn_ok": "打开",
        "project_open_btn_cancel": "取消",

        # ── Delete Project ──
        "project_delete_title": "删除项目",
        "project_delete_confirm": "确认将项目「{name}」移入回收站？",
        "project_delete_path": "路径: {path}",
        "project_delete_btn_yes": "确认删除",
        "project_delete_btn_no": "取消",

        # ── Load Config Dialog ──
        "load_config_title": "加载配置",
        "load_config_filter": "配置文件 (*.txt);;所有文件 (*.*)",

        # ── Project messages ──
        "msg_project_created": "项目已创建: {name}",
        "msg_project_opened": "项目已打开: {name}",
        "msg_project_closed": "项目已关闭",
        "msg_project_deleted": "项目已移入回收站: {name}",
        "msg_project_name_empty": "项目名称不能为空",
        "msg_project_name_invalid": "项目名称包含非法字符",
        "msg_project_exists": "项目已存在: {name}",
        "msg_project_not_found": "未找到项目: {name}",
        "msg_config_saved": "配置已保存",
        "msg_config_loaded": "配置已加载",
        "msg_config_load_fail": "加载配置失败: {exc}",
    },

    "en": {
        # ── Main window ──
        "window_title": "Prof. Fang Jian Optimization Tool — Virtuoso + pymoo",
        "menu_file": "&File",
        "menu_opt": "&Optimization",
        "menu_view": "&View",
        "menu_help": "&Help",
        "menu_lang": "&Language",
        "act_new": "New Optimization",
        "act_project_new": "New Project",
        "act_project_open": "Open Project",
        "act_project_close": "Close Project",
        "act_project_delete": "Delete Project",
        "act_save_config": "Save Config",
        "act_load_config": "Load Config...",
        "act_exit": "E&xit",
        "act_start": "Start Optimization",
        "act_stop": "Stop",
        "act_clear_log": "Clear Log",
        "act_reset_plots": "Reset Plots",
        "act_about": "About",
        "lang_zh": "中文",
        "lang_en": "English",
        "conn_status_disconnected": "● Virtuoso: Disconnected",
        "conn_status_connected": "● Virtuoso: Connected",
        "conn_btn_connect": "🔌 Connect",
        "conn_btn_disconnect": "🔌 Disconnect",
        "conn_connecting": "Connecting...",
        "status_ready": "Ready",
        "status_running": "Optimizing...",
        "status_done": "Done",
        "status_pause": "Stopping...",
        "status_error": "Error",
        "status_gen": "Gen: {n}",
        "status_eval": "Eval: {n}",
        "status_best": "Best: [{vals}]",
        "status_time": "Time: {n}",

        # ── Params panel ──
        "grp_algo": "Algorithm",
        "lbl_algo": "Algorithm:",
        "lbl_generations": "Generations:",
        "lbl_population": "Population:",
        "lbl_seed": "Seed:",
        "grp_mode": "Run Mode",
        "chk_dry_run": "Dry-Run (no real simulation)",
        "chk_plot": "Live plots",
        "chk_project": "Archive project",
        "chk_verbose": "Verbose log",
        "grp_proj": "Project Directory",
        "proj_placeholder": "leave empty = no archive",
        "grp_sim": "Simulation (non-Dry-Run)",
        "lbl_csv": "CSV file path:",
        "csv_placeholder": "outputs_xxx_maestro.csv",
        "btn_browse": "Browse...",
        "lbl_run_dir": "Run directory:",
        "run_dir_placeholder": ".",
        "btn_start": "▶ Start",
        "btn_stop": "■ Stop",
        "version": "Prof. Fang Jian Opt Tool v0.1",
        "algo_tooltip": (
            "pymoo — NSGA2/3/SPEA2/MOEAD for multi-obj, GA/DE/PSO for single-obj\n"
            "Bayesian — bayes_gp sample-efficient, bayes_rf robust, bayes_mo multi-obj"
        ),

        # ── Plot panel ──
        "plot_view": "View:",
        "mode_both": "Convergence + Pareto",
        "mode_convergence": "Convergence",
        "mode_pareto": "Pareto",
        "convergence_title": "Convergence",
        "convergence_xlabel": "Generation",
        "convergence_ylabel": "Normalized Objective",
        "history_title": "All History",
        "pareto_title": "Pareto Front",
        "pareto_xlabel": "Objective 1",
        "pareto_ylabel": "Objective 2",

        # ── Results table ──
        "results_title": "Pareto Solutions",
        "col_var": "Var: {n}",
        "col_obj": "Obj: {n}",
        "col_action": "Action",
        "btn_select": "Backannotate to CDS",
        "btn_select_tooltip": "Send Pareto solution back to Virtuoso circuit",

        # ── Log panel ──
        "log_title": "Log (CIW)",

        # ── VNC widget ──
        "vnc_title": "VNC Viewer",
        "vnc_launch_btn": "Launch VNC Viewer",
        "vnc_launch_hint": "Launches external VNC Viewer.\nConfigure your connection inside VNC Viewer.",
        "vnc_not_found": "VNC Viewer Not Found",
        "vnc_not_found_msg": "Cannot find vncviewer.exe.\nInstall RealVNC Viewer or add its directory to your system PATH.",
        "vnc_error_title": "Launch Failed",
        "vnc_launch_failed": "Failed to launch VNC Viewer:",

        # ── Messages ──
        "msg_not_connected": "Not Connected",
        "msg_connect_first": "Please connect to Virtuoso first.",
        "msg_upload_ok": "Sent {n} variables back to circuit",
        "msg_upload_fail": "Send failed: {exc}",
        "msg_circuit_updated": "Circuit parameters updated. Ready to re-run simulation.",
        "msg_no_virtuoso": "Virtuoso Not Connected",
        "msg_confirm_dry": (
            "Virtuoso is not connected. Non-Dry-Run mode requires a connection.\n"
            "Continue anyway? (Dry-Run only)"
        ),
        "msg_missing_csv": "CSV File Missing",
        "msg_specify_csv": (
            "Non-Dry-Run mode requires a CSV file path.\n"
            "Please enter the CSV path in 'Simulation Settings'."
        ),
        "msg_opt_running": "Optimization running in background...",
        "msg_opt_done": "Optimization finished",
        "msg_opt_aborted": "Optimization aborted",
        "msg_opt_stopped": "Optimization stopped",
        "msg_opt_error": "Optimization Error",
        "msg_opt_start": "Initializing optimization...",
        "msg_opt_ok": "Done ✓  Pareto solutions: {n}",
        "msg_results_parse": "Result parse: {exc}",
        "msg_reset": "Reset — ready for new optimization",

        # ── Project management ──
        "project_status": "Project: {name}",
        "project_no_project": "No project open",

        # ── New Project Dialog ──
        "project_new_title": "New Project",
        "project_new_name": "Project Name:",
        "project_new_root": "Root Path:",
        "project_new_btn_browse": "Browse...",
        "project_new_btn_ok": "Create",
        "project_new_btn_cancel": "Cancel",

        # ── Open Project Dialog ──
        "project_open_title": "Open Project",
        "project_open_list": "Select a project:",
        "project_open_btn_ok": "Open",
        "project_open_btn_cancel": "Cancel",

        # ── Delete Project ──
        "project_delete_title": "Delete Project",
        "project_delete_confirm": "Move project '{name}' to recycle bin?",
        "project_delete_path": "Path: {path}",
        "project_delete_btn_yes": "Delete",
        "project_delete_btn_no": "Cancel",

        # ── Load Config Dialog ──
        "load_config_title": "Load Config",
        "load_config_filter": "Config files (*.txt);;All files (*.*)",

        # ── Project messages ──
        "msg_project_created": "Project created: {name}",
        "msg_project_opened": "Project opened: {name}",
        "msg_project_closed": "Project closed",
        "msg_project_deleted": "Project moved to recycle bin: {name}",
        "msg_project_name_empty": "Project name cannot be empty",
        "msg_project_name_invalid": "Project name contains invalid characters",
        "msg_project_exists": "Project already exists: {name}",
        "msg_project_not_found": "Project not found: {name}",
        "msg_config_saved": "Config saved",
        "msg_config_loaded": "Config loaded",
        "msg_config_load_fail": "Failed to load config: {exc}",
    },
}

# ── Current language state ──

_current_lang = "zh"

# ── Public API ──


def tr(key: str, default: str = "", **kwargs) -> str:
    """Translate a key to the current language.

    Args:
        key: Translation key.
        default: Fallback text if key is missing.
        **kwargs: Optional format arguments (e.g. n=5, exc="err").

    Returns:
        Translated string with format interpolation applied,
        or *default* if key is not found, or the key itself as last resort.
    """
    lang_dict = _STRINGS.get(_current_lang, {})
    val = lang_dict.get(key, default if default else key)
    if kwargs:
        try:
            val = val.format(**kwargs)
        except (KeyError, ValueError):
            pass
    return val


def set_lang(lang: str) -> None:
    """Switch the current language ('zh' or 'en')."""
    global _current_lang
    if lang in _STRINGS:
        _current_lang = lang


def get_lang() -> str:
    """Return the current language code ('zh' or 'en')."""
    return _current_lang


def get_available_langs() -> list:
    """Return list of available language codes."""
    return list(_STRINGS.keys())