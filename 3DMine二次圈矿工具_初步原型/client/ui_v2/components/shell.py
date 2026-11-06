# -*- coding: utf-8 -*-
"""应用外壳：沉浸式标题栏 + 左侧导航 + 窗口控制按钮。

设计要点
--------
* 标题栏与侧边栏同为深海军蓝（``theme.CHROME``），顶部不再出现系统浅色标题栏，
  从视觉上连成一整块「机箱」；内容区是浅色工作面，形成明确的前后景关系。
* 窗口为无边框（``FramelessWindowHint``），但 **不放弃 Windows 原生能力**：
  在 ``nativeEvent`` 里处理 ``WM_NCHITTEST``，把标题栏空白区交回系统当作标题栏
  （可拖动、双击最大化、拖到屏幕边缘贴靠），最大化按钮返回 ``HTMAXBUTTON``，
  因此 Win11 的 Snap Layout 悬停浮层照常工作；四边 6px 返回缩放命中码，保留原生缩放。
* 窗口按钮自绘（10px 线条，不加抗锯齿），保证 100%/125%/150% 缩放下都是硬边。
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QSizePolicy, QToolButton, QVBoxLayout, QWidget,
)

from .. import APP_NAME, APP_NAME_EN, icons, theme


# ==================================================================== 基础件

class HLine(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("hline")
        self.setFixedHeight(1)


class VLine(QFrame):
    def __init__(self, parent=None, color: str | None = None, height: int | None = None):
        super().__init__(parent)
        self.setObjectName("vline")
        self.setFixedWidth(1)
        if color:
            self.setStyleSheet("background:%s;border:none;" % color)
        if height:
            self.setFixedHeight(height)


class Dot(QWidget):
    """状态圆点（8px），颜色随状态变化。"""

    def __init__(self, color: str = theme.SUCCESS, parent=None):
        super().__init__(parent)
        self._color = color
        self.setFixedSize(8, 8)

    def set_color(self, color: str) -> None:
        self._color = color
        self.update()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(self._color))
        p.drawEllipse(QRect(0, 0, 8, 8))
        p.end()


class TitleChip(QWidget):
    """标题栏里的轻量信息胶囊：小图标 + 文本，深色半透明底。"""

    def __init__(self, icon_name: str = "", text: str = "", strong: bool = False,
                 parent=None):
        super().__init__(parent)
        self.setObjectName("titleChipStrong" if strong else "titleChip")
        self.setAttribute(Qt.WA_StyledBackground, True)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(9, 0, 10, 0)
        lay.setSpacing(6)
        self._icon: QLabel | None = None
        if icon_name:
            self._icon = icons.label(icon_name, "#9FBCD4", 13, self)
            lay.addWidget(self._icon)
        self._text = QLabel(text)
        self._text.setStyleSheet("background:transparent;color:%s;font-size:%dpx;"
                                 % ("#EAF4FC" if strong else "#C3D3E2", theme.FS_SMALL))
        lay.addWidget(self._text)
        self.setFixedHeight(26)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)

    def set_text(self, text: str, tip: str = "") -> None:
        fm = self._text.fontMetrics()
        self._text.setText(fm.elidedText(text, Qt.ElideRight, 190))
        self.setToolTip(tip or text)


class StatusChip(QWidget):
    """运行状态胶囊：圆点 + 文本。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("titleChip")
        self.setAttribute(Qt.WA_StyledBackground, True)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(9, 0, 10, 0)
        lay.setSpacing(6)
        self.dot = Dot(theme.SUCCESS, self)
        lay.addWidget(self.dot)
        self._text = QLabel("空闲")
        self._text.setStyleSheet("background:transparent;color:#C3D3E2;font-size:%dpx;"
                                 % theme.FS_SMALL)
        lay.addWidget(self._text)
        self.setFixedHeight(26)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)

    def set_state(self, text: str, busy: bool = False) -> None:
        fm = self._text.fontMetrics()
        self._text.setText(fm.elidedText(text, Qt.ElideRight, 150))
        self.dot.set_color(theme.WARNING if busy else theme.SUCCESS)
        self.setObjectName("titleChipBusy" if busy else "titleChip")
        self.style().unpolish(self)
        self.style().polish(self)
        self.setToolTip(text)


# ==================================================================== 窗口按钮

class WindowButton(QWidget):
    """自绘窗口按钮：min / max / restore / close。"""

    clicked = Signal()

    def __init__(self, kind: str, parent=None):
        super().__init__(parent)
        self.kind = kind
        self._hover = False
        self._down = False
        self.setFixedSize(46, theme.TITLEBAR_H)
        self.setCursor(Qt.ArrowCursor)
        self.setAttribute(Qt.WA_Hover, True)
        self.setToolTip({"min": "最小化", "max": "最大化", "restore": "向下还原",
                         "close": "关闭"}.get(kind, ""))

    def sizeHint(self) -> QSize:
        return QSize(46, theme.TITLEBAR_H)

    def set_hover(self, on: bool) -> None:
        if self._hover != on:
            self._hover = on
            self.update()

    def enterEvent(self, _e) -> None:
        self.set_hover(True)

    def leaveEvent(self, _e) -> None:
        self._hover = False
        self._down = False
        self.update()

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.LeftButton:
            self._down = True
            self.update()

    def mouseReleaseEvent(self, e) -> None:
        was = self._down
        self._down = False
        self.update()
        if was and e.button() == Qt.LeftButton and self.rect().contains(e.position().toPoint()):
            self.clicked.emit()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, False)
        rect = self.rect()

        if self.kind == "close":
            bg = QColor("#C42B1C") if (self._hover or self._down) else QColor(0, 0, 0, 0)
            if self._down and self._hover:
                bg = QColor("#B02718")
        else:
            bg = QColor(255, 255, 255, 22 if self._hover else 0)
            if self._down and self._hover:
                bg = QColor(255, 255, 255, 38)
        if bg.alpha():
            p.fillRect(rect, bg)

        fg = QColor("#FFFFFF")
        p.setPen(QPen(fg, 1))
        cx, cy = rect.width() // 2, rect.height() // 2
        if self.kind == "min":
            p.drawLine(cx - 5, cy + 4, cx + 5, cy + 4)
        elif self.kind == "max":
            p.drawRect(cx - 5, cy - 5, 10, 10)
        elif self.kind == "restore":
            p.drawRect(cx - 5, cy - 3, 8, 8)
            p.drawLine(cx - 3, cy - 5, cx + 5, cy - 5)
            p.drawLine(cx + 5, cy - 5, cx + 5, cy + 3)
        else:  # close
            p.drawLine(cx - 4, cy - 4, cx + 4, cy + 4)
            p.drawLine(cx + 4, cy - 4, cx - 4, cy + 4)
        p.end()


# ==================================================================== 标题栏

class TitleBar(QWidget):
    """沉浸式标题栏：品牌区 | 面包屑 | 项目/平台/矿段/状态 | 设置 | 窗口按钮。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("titlebar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedHeight(theme.TITLEBAR_H)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ---- 品牌区（宽度与侧边栏对齐）
        brand = QWidget()
        brand.setFixedWidth(theme.SIDEBAR_W)
        bl = QHBoxLayout(brand)
        bl.setContentsMargins(15, 0, 10, 0)
        bl.setSpacing(10)
        self.logo = QLabel()
        self.logo.setFixedSize(30, 30)
        self.logo.setPixmap(icons.pixmap("pick", "#9CC7E4", 20))
        self.logo.setAlignment(Qt.AlignCenter)
        self.logo.setStyleSheet(
            "background:#17364F;border:1px solid #2A4E6C;border-radius:7px;")
        bl.addWidget(self.logo)
        title_col = QVBoxLayout()
        title_col.setContentsMargins(0, 0, 0, 0)
        title_col.setSpacing(0)
        name = QLabel(APP_NAME)
        name.setObjectName("brandName")
        sub = QLabel("MINING WORKSPACE")
        sub.setObjectName("brandSub")
        title_col.addWidget(name)
        title_col.addWidget(sub)
        bl.addLayout(title_col, 1)
        lay.addWidget(brand)

        div = VLine(self, theme.CHROME_LINE, 24)
        lay.addWidget(div)

        # ---- 面包屑
        crumb = QWidget()
        cl = QHBoxLayout(crumb)
        cl.setContentsMargins(18, 0, 10, 0)
        cl.setSpacing(8)
        self.crumb_group = QLabel("工作空间")
        self.crumb_group.setObjectName("crumbSub")
        self.crumb_sep = icons.label("chevron", "#41586F", 13, self)
        self.crumb_main = QLabel("工作台")
        self.crumb_main.setObjectName("crumbMain")
        cl.addWidget(self.crumb_group)
        cl.addWidget(self.crumb_sep)
        cl.addWidget(self.crumb_main)
        cl.addStretch(1)
        lay.addWidget(crumb, 1)

        # ---- 右侧信息区
        right = QWidget()
        rl = QHBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(8)
        self.chip_project = TitleChip("folder", "项目 —")
        self.chip_platform = TitleChip("mountain", "平台 —")
        self.chip_section = TitleChip("target", "矿段 —", strong=True)
        self.chip_status = StatusChip()
        for c in (self.chip_project, self.chip_platform, self.chip_section, self.chip_status):
            rl.addWidget(c)

        self.btn_settings = QToolButton()
        self.btn_settings.setIcon(icons.icon("settings", "#A9C0D6", 17))
        self.btn_settings.setIconSize(QSize(17, 17))
        self.btn_settings.setFixedSize(30, 28)
        self.btn_settings.setCursor(Qt.PointingHandCursor)
        self.btn_settings.setToolTip("系统设置")
        self.btn_settings.setStyleSheet(
            "QToolButton{background:transparent;border:1px solid transparent;border-radius:6px;}"
            "QToolButton:hover{background:#1B3350;border-color:#28455F;}"
            "QToolButton:pressed{background:#16283C;}")
        rl.addSpacing(2)
        rl.addWidget(self.btn_settings)
        rl.addSpacing(6)
        lay.addWidget(right)

        # ---- 窗口按钮
        self.btn_min = WindowButton("min", self)
        self.btn_max = WindowButton("max", self)
        self.btn_close = WindowButton("close", self)
        for b in (self.btn_min, self.btn_max, self.btn_close):
            lay.addWidget(b)

    # ---- 状态更新 ----

    def set_page(self, group: str, title: str) -> None:
        self.crumb_group.setText(group or "工作空间")
        self.crumb_main.setText(title or "")

    def set_info(self, project: str, platform: str, section: str, state: str,
                 busy: bool = False) -> None:
        self.chip_project.set_text("项目 %s" % project if project else "项目 —",
                                   "数据目录：%s" % project)
        self.chip_platform.set_text("平台 %s" % platform if platform else "平台 —", platform)
        self.chip_section.set_text("矿段 %s" % section if section else "矿段 —", section)
        self.chip_status.set_state(state, busy)

    def set_maximized(self, maximized: bool) -> None:
        self.btn_max.kind = "restore" if maximized else "max"
        self.btn_max.setToolTip("向下还原" if maximized else "最大化")
        self.btn_max.update()


# ==================================================================== 导航

class NavItem(QWidget):
    """单个导航项：左侧状态条 + 20px 图标 + 14px 文字（三层固定尺寸，绝不被压缩）。"""

    clicked = Signal(str)

    def __init__(self, key: str, icon_name: str, text: str, parent=None):
        super().__init__(parent)
        self.key = key
        self.icon_name = icon_name
        self.setObjectName("navItem")
        self.setProperty("state", "normal")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedHeight(38)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(text)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 10, 0)
        lay.setSpacing(0)
        self.bar = QFrame()
        self.bar.setFixedSize(3, 16)
        self.bar.setStyleSheet("background:transparent;border:none;border-radius:2px;")
        lay.addWidget(self.bar)
        lay.addSpacing(11)

        self.icon_label = QLabel()
        self.icon_label.setFixedSize(theme.ICON_NAV, theme.ICON_NAV)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setPixmap(icons.pixmap(icon_name, "#A6BCCF", theme.ICON_NAV))
        lay.addWidget(self.icon_label)
        lay.addSpacing(11)

        self.text_label = QLabel(text)
        self.text_label.setObjectName("navText")
        lay.addWidget(self.text_label, 1)

    # ---- 状态 ----

    def set_active(self, active: bool) -> None:
        state = "active" if active else "normal"
        self.setProperty("state", state)
        self._repolish(self)
        if active:
            self.bar.setStyleSheet("background:%s;border:none;border-radius:2px;"
                                   % "#5FA8D8")
        else:
            self.bar.setStyleSheet("background:transparent;border:none;border-radius:2px;")
        color = "#DFF0FB" if active else "#A6BCCF"
        self.icon_label.setPixmap(icons.pixmap(self.icon_name, color, theme.ICON_NAV))
        self.text_label.setProperty("state", state)
        self._repolish(self.text_label)

    def _set_hover(self, on: bool) -> None:
        if self.property("state") == "active":
            return
        state = "hover" if on else "normal"
        self.setProperty("state", state)
        self._repolish(self)
        self.icon_label.setPixmap(
            icons.pixmap(self.icon_name, "#DCE8F3" if on else "#A6BCCF", theme.ICON_NAV))
        self.text_label.setProperty("state", state)
        self._repolish(self.text_label)

    @staticmethod
    def _repolish(w: QWidget) -> None:
        w.style().unpolish(w)
        w.style().polish(w)
        w.update()

    # ---- 事件 ----

    def enterEvent(self, _e) -> None:
        self._set_hover(True)

    def leaveEvent(self, _e) -> None:
        self._set_hover(False)

    def mouseReleaseEvent(self, e) -> None:
        if e.button() == Qt.LeftButton and self.rect().contains(e.position().toPoint()):
            self.clicked.emit(self.key)


class Sidebar(QWidget):
    """深蓝导航栏：分组标题 + 菜单项 + 底部版本/构建信息。"""

    def __init__(self, nav: list[tuple[str, list[tuple[str, str, str]]]], parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedWidth(theme.SIDEBAR_W)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 14, 10, 12)
        lay.setSpacing(1)

        self.items: dict[str, NavItem] = {}
        for group, entries in nav:
            g = QLabel(group)
            g.setObjectName("navGroup")
            g.setContentsMargins(12, 15, 0, 7)
            lay.addWidget(g)
            for key, icon_name, text in entries:
                item = NavItem(key, icon_name, text)
                item.clicked.connect(self._on_click)
                self.items[key] = item
                lay.addWidget(item)

        lay.addStretch(1)

        line = HLine()
        line.setStyleSheet("background:%s;border:none;" % theme.CHROME_LINE)
        lay.addWidget(line)
        foot = QVBoxLayout()
        foot.setContentsMargins(12, 9, 8, 0)
        foot.setSpacing(3)
        self.lb_version = QLabel("")
        self.lb_version.setObjectName("sideMetaStrong")
        self.lb_build = QLabel("")
        self.lb_build.setObjectName("sideMeta")
        foot.addWidget(self.lb_version)
        foot.addWidget(self.lb_build)
        lay.addLayout(foot)

        self._active: str | None = None
        self._on_click_cb = None

    def bind(self, cb) -> None:
        self._on_click_cb = cb

    def _on_click(self, key: str) -> None:
        if self._on_click_cb is not None:
            self._on_click_cb(key)

    def set_active(self, key: str) -> None:
        for k, item in self.items.items():
            item.set_active(k == key)
        self._active = key

    def set_footer(self, version: str, build: str) -> None:
        self.lb_version.setText(version)
        self.lb_build.setText(build)
