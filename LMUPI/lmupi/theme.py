"""Dark motorsport-themed stylesheet for LMUPI."""

import matplotlib.figure

PLOT_COLORS = [
    "#e8751a",  # accent orange
    "#f5a623",  # amber
    "#00bcd4",  # cyan
    "#e040fb",  # magenta
    "#27ae60",  # green
    "#d63031",  # red
    "#4fc3f7",  # sky blue
    "#ab47bc",  # violet
]


def apply_plot_theme(fig: matplotlib.figure.Figure, ax) -> None:
    """Apply dark motorsport theme to a matplotlib figure/axes."""
    bg = "#1a1a1a"
    bg_light = "#242424"
    text = "#d4d4d4"
    grid = "#3a3a3a"

    fig.patch.set_facecolor(bg)
    axes = fig.get_axes() if hasattr(fig, "get_axes") else [ax]
    for a in axes:
        a.set_facecolor(bg_light)
        a.tick_params(colors=text, which="both")
        a.xaxis.label.set_color(text)
        a.yaxis.label.set_color(text)
        a.title.set_color(text)
        a.grid(True, color=grid, alpha=0.5, linewidth=0.5)
        for spine in a.spines.values():
            spine.set_color(grid)
    if fig.legends:
        for leg in fig.legends:
            leg.get_frame().set_facecolor(bg_light)
            leg.get_frame().set_edgecolor(grid)
            for t in leg.get_texts():
                t.set_color(text)


COLORS = {
    "bg": "#1a1a1a",
    "bg_light": "#242424",
    "bg_lighter": "#2e2e2e",
    "bg_input": "#1e1e1e",
    "border": "#3a3a3a",
    "border_light": "#4a4a4a",
    "text": "#d4d4d4",
    "text_dim": "#888888",
    "text_bright": "#f0f0f0",
    "accent": "#e8751a",
    "accent_hover": "#f08c3a",
    "accent_pressed": "#c85f10",
    "amber": "#f5a623",
    "red": "#d63031",
    "green": "#27ae60",
    "selection": "#3a3020",
}

DARK_STYLESHEET = f"""
/* === Global === */
QMainWindow, QWidget {{
    background-color: {COLORS["bg"]};
    color: {COLORS["text"]};
    font-family: "Segoe UI", "Inter", "Helvetica Neue", sans-serif;
    font-size: 13px;
}}

/* === Menu Bar === */
QMenuBar {{
    background-color: {COLORS["bg_light"]};
    color: {COLORS["text"]};
    border-bottom: 1px solid {COLORS["border"]};
    padding: 2px;
}}
QMenuBar::item:selected {{
    background-color: {COLORS["bg_lighter"]};
    color: {COLORS["accent"]};
}}
QMenu {{
    background-color: {COLORS["bg_light"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border"]};
    padding: 4px 0;
}}
QMenu::item {{
    padding: 6px 28px 6px 20px;
}}
QMenu::item:selected {{
    background-color: {COLORS["bg_lighter"]};
    color: {COLORS["accent"]};
}}
QMenu::separator {{
    height: 1px;
    background-color: {COLORS["border"]};
    margin: 4px 8px;
}}

/* === Tool Bar === */
QToolBar {{
    background-color: {COLORS["bg_light"]};
    border-bottom: 1px solid {COLORS["border"]};
    padding: 4px;
    spacing: 4px;
}}
QToolBar QToolButton {{
    background-color: transparent;
    color: {COLORS["text"]};
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 4px 10px;
    font-weight: 500;
}}
QToolBar QToolButton:hover {{
    background-color: {COLORS["bg_lighter"]};
    border: 1px solid {COLORS["border"]};
    color: {COLORS["accent"]};
}}
QToolBar QToolButton:pressed {{
    background-color: {COLORS["accent_pressed"]};
    color: {COLORS["text_bright"]};
}}

/* === Tab Widget === */
QTabWidget::pane {{
    border: 1px solid {COLORS["border"]};
    background-color: {COLORS["bg"]};
    top: -1px;
}}
QTabBar::tab {{
    background-color: {COLORS["bg_light"]};
    color: {COLORS["text_dim"]};
    border: 1px solid {COLORS["border"]};
    border-bottom: none;
    padding: 7px 18px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}}
QTabBar::tab:selected {{
    background-color: {COLORS["bg"]};
    color: {COLORS["accent"]};
    border-bottom: 2px solid {COLORS["accent"]};
}}
QTabBar::tab:hover:!selected {{
    background-color: {COLORS["bg_lighter"]};
    color: {COLORS["text"]};
}}

/* === Table Widget === */
QTableWidget, QTableView {{
    background-color: {COLORS["bg"]};
    alternate-background-color: {COLORS["bg_light"]};
    color: {COLORS["text"]};
    gridline-color: {COLORS["border"]};
    border: 1px solid {COLORS["border"]};
    selection-background-color: {COLORS["selection"]};
    selection-color: {COLORS["accent"]};
}}
QHeaderView::section {{
    background-color: {COLORS["bg_light"]};
    color: {COLORS["text_bright"]};
    border: none;
    border-right: 1px solid {COLORS["border"]};
    border-bottom: 1px solid {COLORS["border"]};
    padding: 5px 8px;
    font-weight: 600;
}}

/* === Tree Widget === */
QTreeWidget {{
    background-color: {COLORS["bg"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border"]};
    outline: none;
}}
QTreeWidget::item {{
    padding: 4px 2px;
    border: none;
}}
QTreeWidget::item:selected {{
    background-color: {COLORS["selection"]};
    color: {COLORS["accent"]};
}}
QTreeWidget::item:hover:!selected {{
    background-color: {COLORS["bg_light"]};
}}
QTreeWidget::branch:has-children:closed {{
    image: none;
    border-image: none;
}}
QTreeWidget::branch:has-children:open {{
    image: none;
    border-image: none;
}}

/* === Inputs === */
QLineEdit, QPlainTextEdit, QTextEdit {{
    background-color: {COLORS["bg_input"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
    padding: 5px 8px;
    selection-background-color: {COLORS["selection"]};
    selection-color: {COLORS["accent"]};
}}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {{
    border: 1px solid {COLORS["accent"]};
}}

/* === Combo Box === */
QComboBox {{
    background-color: {COLORS["bg_input"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
    padding: 5px 8px;
    min-width: 80px;
}}
QComboBox:hover {{
    border: 1px solid {COLORS["border_light"]};
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox QAbstractItemView {{
    background-color: {COLORS["bg_light"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border"]};
    selection-background-color: {COLORS["selection"]};
    selection-color: {COLORS["accent"]};
}}

/* === Push Button === */
QPushButton {{
    background-color: {COLORS["bg_lighter"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
    padding: 6px 16px;
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: {COLORS["border"]};
    color: {COLORS["text_bright"]};
}}
QPushButton:pressed {{
    background-color: {COLORS["accent_pressed"]};
    color: {COLORS["text_bright"]};
}}
QPushButton#accent {{
    background-color: {COLORS["accent"]};
    color: {COLORS["text_bright"]};
    border: none;
}}
QPushButton#accent:hover {{
    background-color: {COLORS["accent_hover"]};
}}
QPushButton#accent:pressed {{
    background-color: {COLORS["accent_pressed"]};
}}

/* === Scroll Bars === */
QScrollBar:vertical {{
    background-color: {COLORS["bg"]};
    width: 10px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background-color: {COLORS["border"]};
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {COLORS["border_light"]};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background-color: {COLORS["bg"]};
    height: 10px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background-color: {COLORS["border"]};
    border-radius: 5px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: {COLORS["border_light"]};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* === Splitter === */
QSplitter::handle {{
    background-color: {COLORS["border"]};
    width: 2px;
    height: 2px;
}}
QSplitter::handle:hover {{
    background-color: {COLORS["accent"]};
}}

/* === Status Bar === */
QStatusBar {{
    background-color: {COLORS["bg_light"]};
    color: {COLORS["text_dim"]};
    border-top: 1px solid {COLORS["border"]};
    padding: 2px;
}}
QStatusBar::item {{
    border: none;
}}

/* === Labels === */
QLabel {{
    color: {COLORS["text"]};
}}
QLabel#dim {{
    color: {COLORS["text_dim"]};
}}
QLabel#accent {{
    color: {COLORS["accent"]};
}}
QLabel#error {{
    color: {COLORS["red"]};
}}
QLabel#success {{
    color: {COLORS["green"]};
}}

/* === Scroll Area === */
QScrollArea {{
    border: none;
    background-color: transparent;
}}

/* === Group Box === */
QGroupBox {{
    color: {COLORS["text_dim"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 16px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
}}

/* === Tooltip === */
QToolTip {{
    background-color: {COLORS["bg_light"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border"]};
    padding: 4px;
}}
"""
