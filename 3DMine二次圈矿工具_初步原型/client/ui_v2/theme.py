# -*- coding: utf-8 -*-
"""统一主题：配色、字号、QSS。

视觉基调：专业矿业工程软件（浅色）+ 深色侧边栏；不用渐变/发光/阴影堆叠，
靠留白、分隔线、字号层级区分信息。品位分级颜色不在这里定义 —— 那些必须
来自 ``grade_profiles.json``（见 services/config.py），避免两处漂移。
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication

# ---------------------------------------------------------------- 调色板
BG = "#F4F6F8"
SIDEBAR = "#14263D"
SIDEBAR_HOVER = "#1D3450"
SIDEBAR_ACTIVE = "#25456A"
CARD = "#FFFFFF"
BORDER = "#E3E8EE"
BORDER_STRONG = "#D3DAE3"
PRIMARY = "#2878A5"
PRIMARY_DARK = "#1F6187"
PRIMARY_LIGHT = "#E8F1F7"
ACCENT = "#B87945"
TEXT = "#263445"
TEXT_MUTED = "#7B8794"
TEXT_ON_DARK = "#E8EEF5"
TEXT_ON_DARK_MUTED = "#8FA2B8"
SUCCESS = "#26966D"
WARNING = "#D69A35"
DANGER = "#D65353"
SUCCESS_BG = "#E7F5EF"
WARNING_BG = "#FBF2E1"
DANGER_BG = "#FBEAEA"
NEUTRAL_BG = "#EDF1F5"

FONT_FAMILY = '"Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI", sans-serif'
FONT_MONO = '"Cascadia Mono", "Consolas", "Microsoft YaHei Mono", monospace'

RADIUS = 8
RADIUS_CARD = 10

QSS = f"""
* {{
    font-family: {FONT_FAMILY};
    font-size: 13px;
    color: {TEXT};
    outline: none;
}}

QMainWindow, QWidget#root {{
    background: {BG};
}}

/* ---------------- 侧边栏 ---------------- */
QWidget#sidebar {{
    background: {SIDEBAR};
    border: none;
}}
QLabel#brandTitle {{
    color: #FFFFFF;
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 1px;
}}
QLabel#brandSub {{
    color: {TEXT_ON_DARK_MUTED};
    font-size: 9px;
    letter-spacing: 1.2px;
}}
QLabel#navGroup {{
    color: #6F87A1;
    font-size: 11px;
    padding: 14px 0 4px 18px;
}}
QPushButton[nav="true"] {{
    background: transparent;
    border: none;
    border-left: 3px solid transparent;
    color: {TEXT_ON_DARK};
    text-align: left;
    padding: 9px 12px 9px 17px;
    font-size: 13px;
    border-radius: 0;
}}
QPushButton[nav="true"]:hover {{
    background: {SIDEBAR_HOVER};
}}
QPushButton[nav="true"]:checked {{
    background: {SIDEBAR_ACTIVE};
    border-left: 3px solid {PRIMARY};
    color: #FFFFFF;
    font-weight: 600;
}}
QLabel#sidebarFoot {{
    color: #6F87A1;
    font-size: 11px;
    padding: 10px 16px;
}}

/* ---------------- 顶栏 ---------------- */
QWidget#topbar {{
    background: {CARD};
    border-bottom: 1px solid {BORDER};
}}
QLabel#pageTitle {{
    font-size: 17px;
    font-weight: 700;
    color: {TEXT};
}}
QLabel#pageSub {{
    font-size: 12px;
    color: {TEXT_MUTED};
}}
QLabel#chip {{
    background: {NEUTRAL_BG};
    border: 1px solid {BORDER};
    border-radius: 11px;
    padding: 3px 10px;
    font-size: 12px;
    color: {TEXT};
}}
QLabel#chipPrimary {{
    background: {PRIMARY_LIGHT};
    border: 1px solid #C9DEEC;
    border-radius: 11px;
    padding: 3px 10px;
    font-size: 12px;
    color: {PRIMARY_DARK};
}}

/* ---------------- 卡片与文字 ---------------- */
QFrame#card {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_CARD}px;
}}
QFrame#cardTight {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: {RADIUS}px;
}}
QLabel#cardTitle {{
    font-size: 14px;
    font-weight: 600;
}}
QLabel#h1 {{ font-size: 20px; font-weight: 700; }}
QLabel#h2 {{ font-size: 15px; font-weight: 600; }}
QLabel#muted {{ color: {TEXT_MUTED}; font-size: 12px; }}
QLabel#mono {{ font-family: {FONT_MONO}; font-size: 12px; color: {TEXT_MUTED}; }}
QLabel#statValue {{ font-size: 22px; font-weight: 700; color: {TEXT}; }}
QLabel#statLabel {{ font-size: 12px; color: {TEXT_MUTED}; }}
QLabel#fieldLabel {{ color: {TEXT_MUTED}; font-size: 12px; }}
QLabel#sectionNo {{
    background: {PRIMARY_LIGHT};
    color: {PRIMARY_DARK};
    border-radius: 11px;
    font-weight: 700;
    min-width: 22px;
    max-width: 22px;
    min-height: 22px;
    max-height: 22px;
}}
QFrame#hline {{ background: {BORDER}; max-height: 1px; min-height: 1px; border: none; }}
QFrame#vline {{ background: {BORDER}; max-width: 1px; min-width: 1px; border: none; }}

/* ---------------- 按钮 ---------------- */
QPushButton {{
    background: {CARD};
    border: 1px solid {BORDER_STRONG};
    border-radius: {RADIUS}px;
    padding: 7px 14px;
    min-height: 18px;
}}
QPushButton:hover {{ background: #F7FAFC; border-color: #BFCAD6; }}
QPushButton:pressed {{ background: #EEF3F7; }}
QPushButton:disabled {{ color: #A9B3BF; background: #F4F6F8; border-color: {BORDER}; }}

QPushButton[kind="primary"] {{
    background: {PRIMARY};
    border: 1px solid {PRIMARY};
    color: #FFFFFF;
    font-weight: 600;
    padding: 9px 20px;
}}
QPushButton[kind="primary"]:hover {{ background: {PRIMARY_DARK}; border-color: {PRIMARY_DARK}; }}
QPushButton[kind="primary"]:disabled {{ background: #A9C6D6; border-color: #A9C6D6; color: #F2F7FA; }}

QPushButton[kind="accent"] {{
    background: {ACCENT};
    border: 1px solid {ACCENT};
    color: #FFFFFF;
    font-weight: 600;
}}
QPushButton[kind="accent"]:hover {{ background: #A26A3C; border-color: #A26A3C; }}

QPushButton[kind="danger"] {{
    color: {DANGER};
    border: 1px solid #EBBDBD;
    background: {DANGER_BG};
}}
QPushButton[kind="danger"]:hover {{ background: #F7DCDC; }}

QPushButton[kind="ghost"] {{
    background: transparent;
    border: 1px solid transparent;
    color: {PRIMARY_DARK};
    padding: 5px 8px;
}}
QPushButton[kind="ghost"]:hover {{ background: {PRIMARY_LIGHT}; }}

QToolButton {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 4px;
}}
QToolButton:hover {{ background: {NEUTRAL_BG}; }}

/* ---------------- 输入 ---------------- */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background: {CARD};
    border: 1px solid {BORDER_STRONG};
    border-radius: 6px;
    padding: 6px 9px;
    min-height: 18px;
    selection-background-color: {PRIMARY};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {PRIMARY};
}}
QLineEdit:disabled, QComboBox:disabled {{ background: #F4F6F8; color: #97A2AE; }}
QLineEdit[state="ok"] {{ border-color: #BFE0D2; background: #F7FCF9; }}
QLineEdit[state="warn"] {{ border-color: #EBD4A5; background: #FFFDF7; }}
QLineEdit[state="error"] {{ border-color: #EBBCBC; background: #FFF9F9; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {CARD};
    border: 1px solid {BORDER_STRONG};
    selection-background-color: {PRIMARY_LIGHT};
    selection-color: {TEXT};
    padding: 4px;
}}
QPlainTextEdit, QTextEdit {{
    background: {CARD};
    border: 1px solid {BORDER_STRONG};
    border-radius: 6px;
    padding: 6px;
    selection-background-color: {PRIMARY};
}}
QPlainTextEdit#paste {{
    background: #FCFDFE;
    font-family: {FONT_MONO};
    font-size: 12px;
}}
QPlainTextEdit#log {{
    background: #FBFCFD;
    font-family: {FONT_MONO};
    font-size: 12px;
    color: #33424F;
}}

/* ---------------- 表格 ---------------- */
QTableView {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: {RADIUS}px;
    gridline-color: #EDF1F5;
    selection-background-color: {PRIMARY_LIGHT};
    selection-color: {TEXT};
    alternate-background-color: #FAFBFC;
}}
QTableView::item {{ padding: 4px 6px; border: none; }}
QHeaderView::section {{
    background: #F7F9FB;
    color: {TEXT_MUTED};
    border: none;
    border-bottom: 1px solid {BORDER};
    border-right: 1px solid {BORDER};
    padding: 7px 8px;
    font-size: 12px;
    font-weight: 600;
}}
QHeaderView::section:last {{ border-right: none; }}
QTableCornerButton::section {{ background: #F7F9FB; border: none; }}

/* ---------------- 其它控件 ---------------- */
QTabWidget::pane {{ border: none; background: transparent; }}
QTabBar::tab {{
    background: transparent;
    color: {TEXT_MUTED};
    padding: 8px 16px;
    border: none;
    border-bottom: 2px solid transparent;
    margin-right: 4px;
}}
QTabBar::tab:selected {{ color: {PRIMARY_DARK}; border-bottom: 2px solid {PRIMARY}; font-weight: 600; }}
QTabBar::tab:hover {{ color: {TEXT}; }}

QCheckBox, QRadioButton {{ spacing: 7px; }}
QCheckBox::indicator, QRadioButton::indicator {{ width: 15px; height: 15px; }}
QCheckBox::indicator {{ border: 1px solid {BORDER_STRONG}; border-radius: 3px; background: #FFF; }}
QCheckBox::indicator:checked {{ background: {PRIMARY}; border-color: {PRIMARY}; }}
QRadioButton::indicator {{ border: 1px solid {BORDER_STRONG}; border-radius: 8px; background: #FFF; }}
QRadioButton::indicator:checked {{ border: 4px solid {PRIMARY}; background: #FFF; }}

QProgressBar {{
    background: #E9EEF3;
    border: none;
    border-radius: 5px;
    height: 10px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{ background: {PRIMARY}; border-radius: 5px; }}

QSplitter::handle {{ background: {BORDER}; }}
QSplitter::handle:horizontal {{ width: 3px; }}
QSplitter::handle:vertical {{ height: 3px; }}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #C6D0DA; border-radius: 5px; min-height: 28px; }}
QScrollBar::handle:vertical:hover {{ background: #AEBBc8; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: #C6D0DA; border-radius: 5px; min-width: 28px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}

QStatusBar {{ background: {CARD}; border-top: 1px solid {BORDER}; color: {TEXT_MUTED}; }}
QToolTip {{
    background: #22374F;
    color: #FFFFFF;
    border: none;
    padding: 5px 8px;
    border-radius: 4px;
}}
QMessageBox {{ background: {CARD}; }}
QMenu {{ background: {CARD}; border: 1px solid {BORDER_STRONG}; padding: 4px; }}
QMenu::item {{ padding: 6px 22px 6px 14px; border-radius: 4px; }}
QMenu::item:selected {{ background: {PRIMARY_LIGHT}; }}
"""


def apply_theme(app: QApplication) -> None:
    """字体 + 调色板 + QSS。"""
    app.setStyle("Fusion")
    font = QFont("Microsoft YaHei UI", 10)
    font.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(font)

    pal = QPalette()
    pal.setColor(QPalette.Window, QColor(BG))
    pal.setColor(QPalette.Base, QColor(CARD))
    pal.setColor(QPalette.AlternateBase, QColor("#FAFBFC"))
    pal.setColor(QPalette.Text, QColor(TEXT))
    pal.setColor(QPalette.WindowText, QColor(TEXT))
    pal.setColor(QPalette.Button, QColor(CARD))
    pal.setColor(QPalette.ButtonText, QColor(TEXT))
    pal.setColor(QPalette.Highlight, QColor(PRIMARY))
    pal.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    pal.setColor(QPalette.ToolTipBase, QColor("#22374F"))
    pal.setColor(QPalette.ToolTipText, QColor("#FFFFFF"))
    app.setPalette(pal)
    app.setStyleSheet(QSS)


def status_color(status: str) -> tuple[str, str]:
    """状态 → (前景, 背景)。用于徽章与表格状态列。"""
    s = (status or "").strip()
    if s in ("通过", "成功", "完成", "已生成", "ok", "OK"):
        return SUCCESS, SUCCESS_BG
    if s in ("警告", "部分失败", "跳过", "运行中", "排队中"):
        return WARNING, WARNING_BG
    if s in ("失败", "错误", "没通过", "异常"):
        return DANGER, DANGER_BG
    return TEXT_MUTED, NEUTRAL_BG
