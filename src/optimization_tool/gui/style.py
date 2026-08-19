"""Cadence-inspired stylesheet for the optimization GUI."""

# Cadence Virtuoso classic color palette
CADENCE_COLORS = {
    "window_bg": "#f0f0f0",
    "panel_bg": "#d9d9d9",
    "dark_blue": "#1a3a5c",
    "medium_blue": "#2a5a8c",
    "accent_blue": "#4a7db4",
    "light_blue": "#6a9fd4",
    "border": "#999999",
    "dark_border": "#666666",
    "light_border": "#cccccc",
    "text": "#000000",
    "text_light": "#ffffff",
    "disabled": "#808080",
    "input_bg": "#ffffff",
    "selection_bg": "#4a7db4",
    "selection_fg": "#ffffff",
    "status_green": "#00aa00",
    "status_yellow": "#ddaa00",
    "status_red": "#cc0000",
    "button_face": "#d5d5d5",
    "button_highlight": "#ffffff",
    "button_shadow": "#808080",
    "tooltip_bg": "#ffffcc",
    "highlight_bg": "#ffff99",
}


def cadence_stylesheet() -> str:
    """Return a complete QSS stylesheet mimicking Cadence Virtuoso classic theme."""
    C = CADENCE_COLORS
    return f"""
    /* ── Global defaults ── */
    QWidget {{
        background-color: {C['window_bg']};
        color: {C['text']};
        font-family: "Microsoft YaHei", "Noto Sans CJK SC", "Arial", sans-serif;
        font-size: 13px;
    }}

    /* ── Main window ── */
    QMainWindow {{
        background-color: {C['window_bg']};
    }}

    /* ── Menu bar ── */
    QMenuBar {{
        background-color: {C['panel_bg']};
        border-bottom: 1px solid {C['border']};
        padding: 2px 0;
    }}
    QMenuBar::item {{
        padding: 4px 12px;
        background: transparent;
    }}
    QMenuBar::item:selected {{
        background-color: {C['accent_blue']};
        color: {C['text_light']};
        border-radius: 3px;
    }}
    QMenu {{
        background-color: {C['panel_bg']};
        border: 1px solid {C['border']};
    }}
    QMenu::item {{
        padding: 4px 24px 4px 12px;
    }}
    QMenu::item:selected {{
        background-color: {C['accent_blue']};
        color: {C['text_light']};
    }}

    /* ── Toolbar ── */
    QToolBar {{
        background-color: {C['panel_bg']};
        border-bottom: 1px solid {C['border']};
        spacing: 6px;
        padding: 3px 6px;
    }}
    QToolBar::separator {{
        width: 1px;
        background: {C['border']};
        margin: 3px 4px;
    }}

    /* ── Group box ── */
    QGroupBox {{
        background-color: {C['panel_bg']};
        border: 1px solid {C['border']};
        border-radius: 4px;
        margin-top: 14px;
        padding: 12px 8px 8px 8px;
        font-weight: bold;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 2px 8px;
        background-color: {C['dark_blue']};
        color: {C['text_light']};
        border-radius: 3px;
        font-size: 12px;
    }}

    /* ── Buttons ── */
    QPushButton {{
        background-color: {C['button_face']};
        border: 1px solid {C['border']};
        border-radius: 3px;
        padding: 5px 16px;
        min-height: 22px;
    }}
    QPushButton:hover {{
        background-color: {C['light_blue']};
        color: {C['text_light']};
        border-color: {C['accent_blue']};
    }}
    QPushButton:pressed {{
        background-color: {C['medium_blue']};
        color: {C['text_light']};
        border-color: {C['dark_blue']};
    }}
    QPushButton:disabled {{
        background-color: {C['panel_bg']};
        color: {C['disabled']};
        border-color: {C['light_border']};
    }}

    /* ── Primary action button (Start Optimization) ── */
    QPushButton#btnStart {{
        background-color: {C['medium_blue']};
        color: {C['text_light']};
        font-weight: bold;
        border: 1px solid {C['dark_blue']};
        padding: 6px 24px;
        font-size: 14px;
    }}
    QPushButton#btnStart:hover {{
        background-color: {C['accent_blue']};
    }}
    QPushButton#btnStart:pressed {{
        background-color: {C['dark_blue']};
    }}

    /* ── Stop button ── */
    QPushButton#btnStop {{
        background-color: #cc3333;
        color: white;
        font-weight: bold;
        border: 1px solid #aa2222;
        padding: 6px 24px;
        font-size: 14px;
    }}
    QPushButton#btnStop:hover {{
        background-color: #dd4444;
    }}

    /* ── Connection button ── */
    QPushButton#btnConnect {{
        padding: 4px 14px;
        font-size: 12px;
        min-height: 20px;
    }}

    /* ── Combo box ── */
    QComboBox {{
        background-color: {C['input_bg']};
        border: 1px solid {C['border']};
        border-radius: 3px;
        padding: 3px 6px;
        min-height: 20px;
    }}
    QComboBox:hover {{
        border-color: {C['accent_blue']};
    }}
    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 20px;
        border-left: 1px solid {C['border']};
    }}
    QComboBox QAbstractItemView {{
        background-color: {C['input_bg']};
        border: 1px solid {C['border']};
        selection-background-color: {C['accent_blue']};
        selection-color: {C['text_light']};
    }}

    /* ── Spin box ── */
    QSpinBox {{
        background-color: {C['input_bg']};
        border: 1px solid {C['border']};
        border-radius: 3px;
        padding: 2px 4px;
        min-height: 20px;
    }}
    QSpinBox:hover {{
        border-color: {C['accent_blue']};
    }}

    /* ── Check box ── */
    QCheckBox {{
        spacing: 6px;
    }}
    QCheckBox::indicator {{
        width: 14px;
        height: 14px;
        border: 1px solid {C['border']};
        background-color: {C['input_bg']};
    }}
    QCheckBox::indicator:checked {{
        background-color: {C['accent_blue']};
        border-color: {C['dark_blue']};
    }}

    /* ── Line edit ── */
    QLineEdit {{
        background-color: {C['input_bg']};
        border: 1px solid {C['border']};
        border-radius: 3px;
        padding: 3px 6px;
        min-height: 20px;
    }}
    QLineEdit:hover {{
        border-color: {C['accent_blue']};
    }}
    QLineEdit:focus {{
        border-color: {C['medium_blue']};
    }}

    /* ── Table ── */
    QTableWidget {{
        background-color: {C['input_bg']};
        border: 1px solid {C['border']};
        gridline-color: {C['light_border']};
        selection-background-color: {C['accent_blue']};
        selection-color: {C['text_light']};
    }}
    QHeaderView::section {{
        background-color: {C['panel_bg']};
        border: 1px solid {C['border']};
        padding: 4px 8px;
        font-weight: bold;
    }}

    /* ── Tree ── */
    QTreeWidget {{
        background-color: {C['input_bg']};
        border: 1px solid {C['border']};
        selection-background-color: {C['accent_blue']};
        selection-color: {C['text_light']};
    }}
    QTreeWidget::item {{
        padding: 3px 2px;
    }}

    /* ── Text edit / Log ── */
    QPlainTextEdit {{
        background-color: {C['input_bg']};
        border: 1px solid {C['border']};
        font-family: "Consolas", "Courier New", monospace;
        font-size: 12px;
    }}

    /* ── Splitter ── */
    QSplitter::handle {{
        background-color: {C['border']};
        width: 2px;
        height: 2px;
    }}

    /* ── Status bar ── */
    QStatusBar {{
        background-color: {C['panel_bg']};
        border-top: 1px solid {C['border']};
        font-size: 12px;
    }}
    QStatusBar::item {{
        border: none;
    }}

    /* ── Tab widget ── */
    QTabWidget::pane {{
        border: 1px solid {C['border']};
        background-color: {C['window_bg']};
    }}
    QTabBar::tab {{
        background-color: {C['panel_bg']};
        border: 1px solid {C['border']};
        border-bottom: none;
        padding: 5px 14px;
        margin-right: 2px;
        border-radius: 3px 3px 0 0;
    }}
    QTabBar::tab:selected {{
        background-color: {C['window_bg']};
        border-bottom: 1px solid {C['window_bg']};
    }}

    /* ── Scrollbar ── */
    QScrollBar:vertical {{
        background: {C['panel_bg']};
        width: 14px;
        border: 1px solid {C['border']};
    }}
    QScrollBar::handle:vertical {{
        background: {C['button_face']};
        border: 1px solid {C['border']};
        min-height: 20px;
        border-radius: 3px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {C['accent_blue']};
    }}

    /* ── Label styles ── */
    QLabel#statusConnected {{
        color: {C['status_green']};
        font-weight: bold;
    }}
    QLabel#statusDisconnected {{
        color: {C['status_red']};
        font-weight: bold;
    }}
    QLabel#sectionTitle {{
        color: {C['dark_blue']};
        font-weight: bold;
        font-size: 12px;
        padding: 2px 0;
    }}
    """