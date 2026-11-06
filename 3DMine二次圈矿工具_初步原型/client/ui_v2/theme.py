# -*- coding: utf-8 -*-
"""统一设计系统：Design Tokens + 全局 QSS（v1.16）。

视觉基调：深蓝「机箱」+ 浅色「工作面」。
    · 标题栏 / 侧边栏 = 深海军蓝（#0E1B2A），构成一整块沉浸式外框；
    · 内容区 = 冷灰白（#F1F4F8），卡片纯白，靠 1px 分隔线与留白建立层级；
    · 主色为钢蓝，仅用于主操作、选中态、链接；强调色为铜褐，只用于「储量/品位」类强调。

原则：不使用渐变、发光、重阴影；圆角克制（卡片 10、控件 6、标签胶囊 999）；
所有尺寸走 4px 栅格（SPACE 系列），字号走 11/12/13/15/18/24 六级。

品位分级颜色不在这里定义 —— 必须来自 ``excel_tools/config/grade_profiles.json``
（见 services/config.py），避免两处漂移，图例与 CAD 输出一致。
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication

APP_TITLE = "二次圈矿智能工作台"

# ---------------------------------------------------------------- 外框（深色）
CHROME = "#0E1B2A"            # 标题栏 / 侧栏基色
CHROME_DEEP = "#0A1521"       # 更深的层级（侧栏底部、分隔）
CHROME_RAISED = "#16283C"     # hover 底
CHROME_ACTIVE = "#1B3350"     # 选中底
CHROME_LINE = "#1E3349"       # 深色区分隔线
CHROME_TEXT = "#E9F0F7"
CHROME_MUTED = "#7E93A8"
CHROME_FAINT = "#5C7288"

# 兼容旧命名（侧栏/图标仍常用这两个）
SIDEBAR = CHROME
SIDEBAR_HOVER = CHROME_RAISED
SIDEBAR_ACTIVE = CHROME_ACTIVE
TEXT_ON_DARK = CHROME_TEXT
TEXT_ON_DARK_MUTED = CHROME_MUTED

# ---------------------------------------------------------------- 工作面（浅色）
BG = "#F1F4F8"                # 页面底
BG_SOFT = "#F7F9FC"           # 次级底（表头、输入禁用、代码块）
CARD = "#FFFFFF"
CARD_ALT = "#FAFBFD"
BORDER = "#E3E9F0"            # 常规边框/分隔
BORDER_SOFT = "#EDF1F6"
BORDER_STRONG = "#CFD9E4"
NEUTRAL_BG = "#EDF1F6"

TEXT = "#1B2735"              # 主文字
TEXT_SUB = "#455667"          # 次级正文
TEXT_MUTED = "#6F7F90"        # 说明文字
TEXT_FAINT = "#96A4B4"        # 占位/极弱

# ---------------------------------------------------------------- 语义色
PRIMARY = "#2A6F97"           # 钢蓝：主操作
PRIMARY_DARK = "#1F5779"      # hover / 深色文字
PRIMARY_LIGHT = "#EAF2F8"     # 淡底
PRIMARY_LINE = "#C4DBEA"
FOCUS = "#3C8DBC"

ACCENT = "#B0774A"            # 铜褐：品位/储量强调
ACCENT_DARK = "#8E5C36"
ACCENT_LIGHT = "#F7EFE7"

SUCCESS = "#1F8A5F"
SUCCESS_BG = "#E7F5EF"
WARNING = "#C08319"
WARNING_BG = "#FBF3E2"
DANGER = "#C0453C"
DANGER_BG = "#FBEBE9"
INFO_BG = PRIMARY_LIGHT

# ---------------------------------------------------------------- 字体
FONT_FAMILY = '"Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI", sans-serif'
FONT_MONO = '"Cascadia Mono", "Consolas", "Microsoft YaHei Mono", monospace'
FONT_NUM = '"Segoe UI", "Microsoft YaHei UI", sans-serif'

FS_DISPLAY = 24
FS_H1 = 18
FS_H2 = 15
FS_BODY = 13
FS_SMALL = 12
FS_CAPTION = 11
FS_MICRO = 10

# ---------------------------------------------------------------- 尺寸
RADIUS = 6
RADIUS_CARD = 10
RADIUS_CHIP = 999
RADIUS_ICON = 8

SIDEBAR_W = 236
TITLEBAR_H = 56
CONTENT_PAD_X = 24
CONTENT_PAD_Y = 20
GAP = 14

CTRL_H = 34            # 输入框 / 普通按钮
CTRL_H_SM = 28         # 小按钮
BTN_PRIMARY_H = 34
ROW_H = 34             # 表格行高
HEADER_H = 34
ICON_NAV = 20
ICON_BTN = 16
ICON_CARD = 22


def mix(color: str, other: str = "#FFFFFF", ratio: float = 0.5) -> str:
    """两色线性插值（做边框、底色时的唯一入口，避免各处手写 hex）。"""
    try:
        a = color.lstrip("#")
        b = other.lstrip("#")
        ra, ga, ba = int(a[0:2], 16), int(a[2:4], 16), int(a[4:6], 16)
        rb, gb, bb = int(b[0:2], 16), int(b[2:4], 16), int(b[4:6], 16)
        r = int(ra + (rb - ra) * ratio)
        g = int(ga + (gb - ga) * ratio)
        bl = int(ba + (bb - ba) * ratio)
        return "#%02X%02X%02X" % (r, g, bl)
    except Exception:
        return color


QSS = f"""
/* =============================================================== 基础 */
* {{
    font-family: {FONT_FAMILY};
    font-size: {FS_BODY}px;
    color: {TEXT};
    outline: none;
}}
QMainWindow, QWidget#root {{
    background: {BG};
}}
QWidget#page {{
    background: {BG};
}}
QToolTip {{
    background: #16283C;
    color: #FFFFFF;
    border: 1px solid #2B4763;
    padding: 5px 9px;
    border-radius: 4px;
    font-size: {FS_SMALL}px;
}}

/* =============================================================== 标题栏 */
QWidget#titlebar {{
    background: {CHROME};
    border: none;
    border-bottom: 1px solid {CHROME_LINE};
}}
QWidget#titlebar QLabel {{
    background: transparent;
}}
QLabel#brandName {{
    color: #FFFFFF;
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 0.4px;
}}
QLabel#brandSub {{
    color: {CHROME_FAINT};
    font-size: 9px;
    letter-spacing: 1.6px;
}}
QLabel#crumbMain {{
    color: #D6E3EF;
    font-size: {FS_BODY}px;
    font-weight: 500;
}}
QLabel#crumbSub {{
    color: {CHROME_MUTED};
    font-size: {FS_SMALL}px;
}}
QLabel#titleChip {{
    color: #C3D3E2;
    background: #0FFFFFFF;
    border: 1px solid #1AFFFFFF;
    border-radius: {RADIUS_CHIP}px;
    padding: 3px 10px;
    font-size: {FS_SMALL}px;
}}
QLabel#titleChipStrong {{
    color: #EAF4FC;
    background: #332A6F97;
    border: 1px solid #6170B2E2;
    border-radius: {RADIUS_CHIP}px;
    padding: 3px 10px;
    font-size: {FS_SMALL}px;
}}
QLabel#titleChipBusy {{
    color: #FCEBC8;
    background: #33C08319;
    border: 1px solid #66E2B058;
    border-radius: {RADIUS_CHIP}px;
    padding: 3px 10px;
    font-size: {FS_SMALL}px;
}}

/* =============================================================== 侧边栏 */
QWidget#sidebar {{
    background: {CHROME};
    border: none;
    border-right: 1px solid {CHROME_LINE};
}}
QLabel#navGroup {{
    color: {CHROME_FAINT};
    font-size: {FS_CAPTION}px;
    font-weight: 600;
    letter-spacing: 0.6px;
}}
QWidget#navItem {{
    background: transparent;
    border: none;
    border-radius: {RADIUS_ICON}px;
}}
QWidget#navItem[state="hover"] {{
    background: {CHROME_RAISED};
}}
QWidget#navItem[state="active"] {{
    background: {CHROME_ACTIVE};
}}
QLabel#navText {{
    color: #B9C9D9;
    font-size: 13px;
    background: transparent;
}}
QLabel#navText[state="hover"] {{ color: #E2EDF7; }}
QLabel#navText[state="active"] {{ color: #FFFFFF; font-weight: 600; }}
QLabel#sideMeta {{
    color: {CHROME_FAINT};
    font-size: {FS_CAPTION}px;
}}
QLabel#sideMetaStrong {{
    color: #93A9BE;
    font-size: {FS_SMALL}px;
    font-weight: 500;
}}
QFrame#sideLine {{ background: {CHROME_LINE}; border: none; max-height: 1px; min-height: 1px; }}

/* =============================================================== 卡片 */
QFrame#card {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_CARD}px;
}}
QFrame#cardTight {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_CARD}px;
}}
QFrame#modeCard {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: {RADIUS}px;
}}
QFrame#modeCard[selected="true"] {{
    background: {PRIMARY_LIGHT};
    border: 1px solid {PRIMARY_LINE};
}}
QFrame#panel {{
    background: {BG_SOFT};
    border: 1px solid {BORDER_SOFT};
    border-radius: {RADIUS}px;
}}
QFrame#hline {{ background: {BORDER}; max-height: 1px; min-height: 1px; border: none; }}
QFrame#vline {{ background: {BORDER}; max-width: 1px; min-width: 1px; border: none; }}

/* =============================================================== 文字层级 */
QLabel#h1 {{ font-size: {FS_H1}px; font-weight: 700; color: {TEXT}; }}
QLabel#h2 {{ font-size: {FS_H2}px; font-weight: 600; color: {TEXT}; }}
QLabel#cardTitle {{ font-size: 14px; font-weight: 600; color: {TEXT}; }}
QLabel#pageSub {{ font-size: {FS_SMALL}px; color: {TEXT_MUTED}; }}
QLabel#muted {{ color: {TEXT_MUTED}; font-size: {FS_SMALL}px; }}
QLabel#faint {{ color: {TEXT_MUTED}; font-size: {FS_CAPTION}px; }}
QLabel#mono {{ font-family: {FONT_MONO}; font-size: {FS_SMALL}px; color: {TEXT_MUTED}; }}
QLabel#fieldLabel {{ color: {TEXT_MUTED}; font-size: {FS_SMALL}px; }}
QLabel#statValue {{
    font-family: {FONT_NUM};
    font-size: {FS_DISPLAY}px;
    font-weight: 600;
    color: {TEXT};
}}
QLabel#statLabel {{ font-size: {FS_SMALL}px; color: {TEXT_SUB}; font-weight: 500; }}
QLabel#statHint {{ font-size: {FS_CAPTION}px; color: {TEXT_MUTED}; }}
QLabel#sectionNo {{
    background: {NEUTRAL_BG};
    color: {TEXT_SUB};
    border-radius: {RADIUS}px;
    font-family: {FONT_MONO};
    font-size: {FS_CAPTION}px;
    font-weight: 600;
}}
QLabel#kpiUnit {{ font-size: {FS_SMALL}px; color: {TEXT_MUTED}; }}

/* =============================================================== 按钮 */
QPushButton {{
    background: {CARD};
    border: 1px solid {BORDER_STRONG};
    border-radius: {RADIUS}px;
    padding: 6px 14px;
    min-height: 18px;
    color: {TEXT};
    font-size: {FS_BODY}px;
}}
QPushButton:hover {{ background: #F7FAFC; border-color: #B9C7D6; }}
QPushButton:pressed {{ background: #EDF2F7; border-color: #A8B8C9; }}
QPushButton:focus {{ border-color: {FOCUS}; }}
QPushButton:disabled {{ color: #A7B2BE; background: {BG_SOFT}; border-color: {BORDER}; }}

QPushButton[kind="primary"] {{
    background: {PRIMARY};
    border: 1px solid {PRIMARY};
    color: #FFFFFF;
    font-weight: 600;
    padding: 7px 18px;
}}
QPushButton[kind="primary"]:hover {{ background: {PRIMARY_DARK}; border-color: {PRIMARY_DARK}; }}
QPushButton[kind="primary"]:pressed {{ background: #194966; border-color: #194966; }}
QPushButton[kind="primary"]:focus {{ border-color: #7FBCE0; }}
QPushButton[kind="primary"]:disabled {{ background: #A9C3D3; border-color: #A9C3D3; color: #F4F9FC; }}

QPushButton[kind="accent"] {{
    background: {ACCENT};
    border: 1px solid {ACCENT};
    color: #FFFFFF;
    font-weight: 600;
    padding: 7px 16px;
}}
QPushButton[kind="accent"]:hover {{ background: {ACCENT_DARK}; border-color: {ACCENT_DARK}; }}

QPushButton[kind="danger"] {{
    color: {DANGER};
    border: 1px solid #E7C3BF;
    background: {DANGER_BG};
}}
QPushButton[kind="danger"]:hover {{ background: #F8DEDB; border-color: #DCA9A3; }}

QPushButton[kind="ghost"] {{
    background: transparent;
    border: 1px solid transparent;
    color: {PRIMARY_DARK};
    padding: 4px 8px;
}}
QPushButton[kind="ghost"]:hover {{ background: {PRIMARY_LIGHT}; border-color: {PRIMARY_LINE}; }}
QPushButton[kind="ghost"]:pressed {{ background: #DEEBF4; }}

QPushButton[kind="nav"] {{
    background: transparent;
    border: none;
    color: {PRIMARY_DARK};
    padding: 2px 4px;
    text-align: left;
}}

QToolButton {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: {RADIUS};
    padding: 4px;
}}
QToolButton:hover {{ background: {NEUTRAL_BG}; border-color: {BORDER}; }}
QToolButton:pressed {{ background: #E2E9F0; }}

/* =============================================================== 输入 */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background: {CARD};
    border: 1px solid {BORDER_STRONG};
    border-radius: {RADIUS}px;
    padding: 5px 9px;
    min-height: 18px;
    selection-background-color: {PRIMARY};
    selection-color: #FFFFFF;
}}
QLineEdit:hover, QComboBox:hover {{ border-color: #B9C7D6; }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {FOCUS};
    background: #FFFFFF;
}}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled {{
    background: {BG_SOFT}; color: #9AA6B4; border-color: {BORDER};
}}
QLineEdit[state="ok"] {{ border-color: #B7DDCB; background: #F8FCFA; }}
QLineEdit[state="warn"] {{ border-color: #E4CE9F; background: #FFFDF7; }}
QLineEdit[state="error"] {{ border-color: #E4B7B2; background: #FFF9F8; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox::down-arrow {{ image: none; }}
QComboBox QAbstractItemView {{
    background: {CARD};
    border: 1px solid {BORDER_STRONG};
    border-radius: {RADIUS}px;
    selection-background-color: {PRIMARY_LIGHT};
    selection-color: {TEXT};
    padding: 4px;
    outline: none;
}}
QPlainTextEdit, QTextEdit {{
    background: {CARD};
    border: 1px solid {BORDER_STRONG};
    border-radius: {RADIUS}px;
    padding: 7px;
    selection-background-color: {PRIMARY};
    selection-color: #FFFFFF;
}}
QPlainTextEdit:focus, QTextEdit:focus {{ border-color: {FOCUS}; }}
QPlainTextEdit#paste {{
    background: {BG_SOFT};
    font-family: {FONT_MONO};
    font-size: {FS_SMALL}px;
    color: {TEXT_SUB};
}}
QPlainTextEdit#log, QTextEdit#log {{
    background: {BG_SOFT};
    border: 1px solid {BORDER_SOFT};
    font-family: {FONT_MONO};
    font-size: {FS_SMALL}px;
    color: #2F3E4D;
}}

/* =============================================================== 表格 */
QTableView, QTableWidget {{
    background: {CARD};
    border: 1px solid {BORDER_SOFT};
    border-radius: {RADIUS}px;
    gridline-color: {BORDER_SOFT};
    selection-background-color: {PRIMARY_LIGHT};
    selection-color: {TEXT};
    alternate-background-color: {CARD_ALT};
}}
QTableView::item, QTableWidget::item {{
    padding: 0 8px;
    border: none;
    border-bottom: 1px solid {BORDER_SOFT};
}}
QTableView::item:hover, QTableWidget::item:hover {{ background: #F5F9FC; }}
QTableView::item:selected, QTableWidget::item:selected {{
    background: {PRIMARY_LIGHT};
    color: {TEXT};
}}
QHeaderView {{ background: transparent; }}
QHeaderView::section {{
    background: {BG_SOFT};
    color: {TEXT_MUTED};
    border: none;
    border-bottom: 1px solid {BORDER};
    border-right: 1px solid {BORDER_SOFT};
    padding: 7px 8px;
    font-size: {FS_SMALL}px;
    font-weight: 600;
}}
QHeaderView::section:first {{ border-top-left-radius: {RADIUS}px; }}
QHeaderView::section:last {{ border-right: none; border-top-right-radius: {RADIUS}px; }}
QTableCornerButton::section {{ background: {BG_SOFT}; border: none; }}

QTreeWidget, QListWidget {{
    background: {CARD};
    border: 1px solid {BORDER_SOFT};
    border-radius: {RADIUS}px;
    outline: none;
}}
QTreeWidget::item, QListWidget::item {{
    padding: 5px 6px;
    border-radius: 4px;
    color: {TEXT_SUB};
}}
QTreeWidget::item:hover, QListWidget::item:hover {{ background: {BG_SOFT}; }}
QTreeWidget::item:selected, QListWidget::item:selected {{
    background: {PRIMARY_LIGHT}; color: {TEXT};
}}
QTreeWidget::branch {{ background: transparent; }}

/* =============================================================== 页签 */
QTabWidget::pane {{ border: none; background: transparent; }}
QTabBar {{ background: transparent; }}
QTabBar::tab {{
    background: transparent;
    color: {TEXT_MUTED};
    padding: 9px 18px;
    border: none;
    border-bottom: 2px solid transparent;
    margin-right: 2px;
    font-size: {FS_BODY}px;
}}
QTabBar::tab:hover {{ color: {TEXT}; }}
QTabBar::tab:selected {{
    color: {PRIMARY_DARK};
    border-bottom: 2px solid {PRIMARY};
    font-weight: 600;
}}

/* =============================================================== 选择控件 */
QCheckBox, QRadioButton {{ spacing: 7px; color: {TEXT_SUB}; font-size: {FS_SMALL}px; }}
QCheckBox::indicator, QRadioButton::indicator {{ width: 15px; height: 15px; }}
QCheckBox::indicator {{ border: 1px solid {BORDER_STRONG}; border-radius: 3px; background: #FFFFFF; }}
QCheckBox::indicator:hover {{ border-color: {FOCUS}; }}
QCheckBox::indicator:checked {{ background: {PRIMARY}; border-color: {PRIMARY}; }}
QRadioButton::indicator {{ border: 1px solid {BORDER_STRONG}; border-radius: 8px; background: #FFFFFF; }}
QRadioButton::indicator:hover {{ border-color: {FOCUS}; }}
QRadioButton::indicator:checked {{ border: 4px solid {PRIMARY}; background: #FFFFFF; }}

/* =============================================================== 进度 / 分隔 */
QProgressBar {{
    background: {NEUTRAL_BG};
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{ background: {PRIMARY}; border-radius: 4px; }}
QSplitter::handle {{ background: transparent; }}
QSplitter::handle:horizontal {{ width: 12px; }}
QSplitter::handle:vertical {{ height: 12px; }}

/* =============================================================== 滚动条 */
QScrollBar:vertical {{ background: transparent; width: 11px; margin: 2px 2px 2px 1px; }}
QScrollBar::handle:vertical {{
    background: #C3CFDB;
    border-radius: 4px;
    min-height: 32px;
}}
QScrollBar::handle:vertical:hover {{ background: #A9B9C9; }}
QScrollBar:horizontal {{ background: transparent; height: 11px; margin: 1px 2px 2px 2px; }}
QScrollBar::handle:horizontal {{ background: #C3CFDB; border-radius: 4px; min-width: 32px; }}
QScrollBar::handle:horizontal:hover {{ background: #A9B9C9; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; border: none; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}

/* =============================================================== 状态栏 / 菜单 */
QStatusBar {{
    background: {CARD};
    border-top: 1px solid {BORDER};
    color: {TEXT_MUTED};
    font-size: {FS_CAPTION}px;
}}
QStatusBar::item {{ border: none; }}
QMenu {{
    background: {CARD};
    border: 1px solid {BORDER_STRONG};
    border-radius: {RADIUS}px;
    padding: 5px;
}}
QMenu::item {{ padding: 6px 24px 6px 14px; border-radius: 4px; }}
QMenu::item:selected {{ background: {PRIMARY_LIGHT}; }}
QMessageBox {{ background: {CARD}; }}

/* =============================================================== v1.16 复合件 */
QFrame#statCard {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_CARD}px;
}}
QFrame#quickCard {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_CARD}px;
}}
QFrame#quickCard[hover="true"] {{
    background: {PRIMARY_LIGHT};
    border-color: {PRIMARY_LINE};
}}
QLabel#body {{ font-size: {FS_SMALL}px; color: {TEXT}; }}
QWidget#pageHeader {{ background: {BG}; }}
QWidget#appFooter {{
    background: {CARD};
    border-top: 1px solid {BORDER};
    min-height: 28px;
    max-height: 28px;
}}
QLabel#statusText {{ color: {TEXT_MUTED}; font-size: {FS_CAPTION}px; }}
QWidget#pageContent {{ background: {BG}; }}
QLabel#chip {{
    background: {NEUTRAL_BG};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_CHIP}px;
    padding: 2px 9px;
    font-size: {FS_CAPTION}px;
    color: {TEXT_SUB};
}}
QLabel#chipPrimary {{
    background: {PRIMARY_LIGHT};
    border: 1px solid {PRIMARY_LINE};
    border-radius: {RADIUS_CHIP}px;
    padding: 2px 9px;
    font-size: {FS_CAPTION}px;
    color: {PRIMARY_DARK};
}}
QFrame#card QLabel, QFrame#cardTight QLabel, QFrame#statCard QLabel,
QFrame#quickCard QLabel {{ background: transparent; }}

/* ---------------- 全局拖放提示层 ---------------- */
QFrame#dropCard {{
    background: #14283C;
    border: 1px solid #2F5878;
    border-radius: 12px;
}}
QFrame#dropCard[tone="ok"] {{ border-color: #2F7F5E; }}
QFrame#dropCard[tone="warn"] {{ border-color: #7A4B45; }}
QLabel#dropTitle {{
    color: #EAF4FC;
    font-size: 13px;
    font-weight: 600;
    background: transparent;
}}
QLabel#dropSub {{
    color: #9FBCD4;
    font-size: 11px;
    background: transparent;
}}

/* ---------------- 本次导入卡片 ---------------- */
QFrame#metaChip {{
    background: {BG_SOFT};
    border: 1px solid {BORDER};
    border-radius: {RADIUS}px;
}}
QFrame#metaChip[warn="true"] {{
    background: {WARNING_BG};
    border: 1px solid #E7D3AC;
}}
QLabel#metaChipKey {{ color: {TEXT_MUTED}; font-size: 10px; background: transparent; }}
QLabel#metaChipVal {{ color: {TEXT}; font-size: 13px; font-weight: 600; background: transparent; }}
QLabel#metaChipSrc {{ color: {TEXT_FAINT}; font-size: 9px; background: transparent; }}
QLabel#importFile {{ font-size: 13px; font-weight: 600; color: {TEXT}; }}
QLabel#importMeta {{ font-size: 11px; color: {TEXT_MUTED}; }}
"""


def apply_theme(app: QApplication) -> None:
    """字体 + 调色板 + QSS（唯一入口，页面里不再各自设全局样式）。"""
    app.setStyle("Fusion")
    font = QFont("Microsoft YaHei UI", 10)
    font.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(font)

    pal = QPalette()
    pal.setColor(QPalette.Window, QColor(BG))
    pal.setColor(QPalette.Base, QColor(CARD))
    pal.setColor(QPalette.AlternateBase, QColor(CARD_ALT))
    pal.setColor(QPalette.Text, QColor(TEXT))
    pal.setColor(QPalette.WindowText, QColor(TEXT))
    pal.setColor(QPalette.Button, QColor(CARD))
    pal.setColor(QPalette.ButtonText, QColor(TEXT))
    pal.setColor(QPalette.Highlight, QColor(PRIMARY))
    pal.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    pal.setColor(QPalette.ToolTipBase, QColor("#16283C"))
    pal.setColor(QPalette.ToolTipText, QColor("#FFFFFF"))
    pal.setColor(QPalette.PlaceholderText, QColor(TEXT_FAINT))
    app.setPalette(pal)
    app.setStyleSheet(QSS)


def status_color(status: str) -> tuple[str, str]:
    """状态 → (前景, 背景)。用于徽章与表格状态列。"""
    s = (status or "").strip()
    if s in ("通过", "成功", "完成", "已生成", "ok", "OK", "就绪"):
        return SUCCESS, SUCCESS_BG
    if s in ("警告", "部分失败", "跳过", "运行中", "排队中", "待执行", "正在执行"):
        return WARNING, WARNING_BG
    if s in ("失败", "错误", "没通过", "异常", "未执行"):
        return DANGER, DANGER_BG
    return TEXT_MUTED, NEUTRAL_BG
