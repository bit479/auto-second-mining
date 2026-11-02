# -*- coding: utf-8 -*-
"""主窗口：左侧导航 + 顶部状态栏 + 中央工作区（QStackedWidget）。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QButtonGroup, QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton,
    QStackedWidget, QVBoxLayout, QWidget,
)

from . import APP_NAME, APP_NAME_EN, APP_VERSION
from . import icons, theme
from .components import widgets as W
from .pages.batch_mining import BatchMiningPage
from .pages.composite_manager import CompositeManagerPage
from .pages.dashboard import DashboardPage
from .pages.database_builder import DatabaseBuilderPage
from .pages.diagnostics import DiagnosticsPage
from .pages.excel_tools import ExcelToolsPage
from .pages.manual_calibration import ManualCalibrationPage
from .pages.parameter_manager import ParameterManagerPage
from .pages.settings import SettingsPage
from .pages.single_mining import SingleMiningPage
from .services import context as C
from .services import paths
from .services.runner import runner

NAV = [
    ("工作", [("dashboard", "dashboard", "工作台"),
              ("single", "target", "单炮区二次圈矿"),
              ("batch", "layers", "批量处理")]),
    ("数据", [("manual", "crosshair", "人工圈矿与参数标定"),
              ("composite", "map", "综合图管理"),
              ("excel", "table", "Excel 数据工具"),
              ("database", "database", "炮孔数据库生成")]),
    ("系统", [("params", "sliders", "参数管理"),
              ("diagnostics", "shield", "验收与诊断"),
              ("settings", "settings", "系统设置")]),
]


def _project_label() -> str:
    home = paths.data_home()
    return home.parent.name if paths.is_frozen() else home.name


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("%s  %s  ·  %s" % (APP_NAME, APP_VERSION, APP_NAME_EN))
        self.setWindowIcon(QIcon(icons.pixmap("pick", theme.PRIMARY, 64, 2.0)))
        self.resize(1440, 900)
        self.setMinimumSize(1280, 720)
        self.ctx = C.context()

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        lay = QHBoxLayout(root)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ---------------- 侧边栏 ----------------
        side = QWidget()
        side.setObjectName("sidebar")
        side.setFixedWidth(216)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(0, 18, 0, 10)
        sl.setSpacing(0)

        brand = QVBoxLayout()
        brand.setContentsMargins(18, 0, 12, 8)
        brand.setSpacing(2)
        t1 = QLabel(APP_NAME)
        t1.setObjectName("brandTitle")
        t2 = QLabel(APP_NAME_EN)
        t2.setObjectName("brandSub")
        brand.addWidget(t1)
        brand.addWidget(t2)
        sl.addLayout(brand)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_buttons: dict[str, QPushButton] = {}
        for group, items in NAV:
            gl = QLabel(group)
            gl.setObjectName("navGroup")
            sl.addWidget(gl)
            for key, ic, text in items:
                b = QPushButton("  " + text)
                b.setProperty("nav", "true")
                b.setCheckable(True)
                b.setCursor(Qt.PointingHandCursor)
                b.setIcon(icons.icon(ic, theme.TEXT_ON_DARK, 17))
                b.setIconSize(QSize(17, 17))
                b.clicked.connect(lambda _=False, k=key: self.navigate(k))
                self.nav_group.addButton(b)
                self.nav_buttons[key] = b
                sl.addWidget(b)
        sl.addStretch(1)

        self.lb_foot = QLabel("%s\n%s" % (APP_VERSION, "源码运行" if not paths.is_frozen() else "单文件 exe"))
        self.lb_foot.setObjectName("sidebarFoot")
        sl.addWidget(self.lb_foot)
        lay.addWidget(side)

        # ---------------- 右侧 ----------------
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)

        top = QWidget()
        top.setObjectName("topbar")
        top.setFixedHeight(64)
        tl = QHBoxLayout(top)
        tl.setContentsMargins(22, 8, 18, 8)
        tl.setSpacing(10)
        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        self.crumb = QLabel("工作台")
        self.crumb.setObjectName("pageTitle")
        self.crumb_sub = QLabel("")
        self.crumb_sub.setObjectName("pageSub")
        self.crumb_sub.setMinimumWidth(260)
        self.crumb_sub.setMaximumWidth(380)
        title_col.addWidget(self.crumb)
        title_col.addWidget(self.crumb_sub)
        tl.addLayout(title_col)
        tl.addStretch(1)
        self.action_slot = QHBoxLayout()
        self.action_slot.setSpacing(8)
        tl.addLayout(self.action_slot)

        self.chip_project = W.Chip("项目：%s" % _project_label())
        self.chip_project.setToolTip(str(paths.data_home()))
        self.chip_platform = W.Chip("平台：—")
        self.chip_section = W.Chip("矿段：自动", primary=True)
        self.chip_task = W.Chip("空闲")
        for c in (self.chip_project, self.chip_platform, self.chip_section, self.chip_task):
            tl.addWidget(c)
        tl.addWidget(W.tool_button("settings", "系统设置", lambda: self.navigate("settings")))
        rl.addWidget(top)

        self.stack = QStackedWidget()
        rl.addWidget(self.stack, 1)
        lay.addWidget(right, 1)

        # ---------------- 页面 ----------------
        self.pages: dict[str, QWidget] = {
            "dashboard": DashboardPage(),
            "single": SingleMiningPage(),
            "batch": BatchMiningPage(),
            "manual": ManualCalibrationPage(),
            "composite": CompositeManagerPage(),
            "excel": ExcelToolsPage(),
            "database": DatabaseBuilderPage(),
            "params": ParameterManagerPage(),
            "diagnostics": DiagnosticsPage(),
            "settings": SettingsPage(),
        }
        for key, page in self.pages.items():
            self.stack.addWidget(page)
        dash = self.pages["dashboard"]
        if hasattr(dash, "request_page"):
            dash.request_page.connect(self.navigate)

        self.statusBar().showMessage("就绪")
        self._wire()
        self.navigate(self.ctx.state.get("last_page", "dashboard") or "dashboard")

    # ------------------------------------------------------------ 绑定

    def _wire(self) -> None:
        self.ctx.changed.connect(self._refresh_chips)
        self.ctx.task_added.connect(self._refresh_chips)
        runner().log.connect(self._on_log)
        runner().state.connect(lambda tid, st: self._refresh_chips())
        runner().finished.connect(lambda tid, code: self._refresh_chips())
        self._refresh_chips()

    def _on_log(self, tid: str, line: str) -> None:
        if line.startswith("[开始]"):
            self.statusBar().showMessage(line.replace("[开始]", "正在执行："))

    # ------------------------------------------------------------ 导航

    def navigate(self, key: str) -> None:
        page = self.pages.get(key)
        if page is None:
            return
        self.stack.setCurrentWidget(page)
        if key in self.nav_buttons:
            self.nav_buttons[key].setChecked(True)
        self.crumb.setText(page.TITLE or key)
        sub = getattr(page, "SUB", "") or ""
        fm = self.crumb_sub.fontMetrics()
        self.crumb_sub.setText(fm.elidedText(sub, Qt.ElideRight, 360))
        self.crumb_sub.setToolTip(sub)
        # 页面动作按钮放到顶栏右侧
        while self.action_slot.count():
            item = self.action_slot.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
        for w in getattr(page, "_actions", []):
            self.action_slot.addWidget(w)
        self.ctx.state.set("last_page", key)
        try:
            page.on_show()
        except Exception as exc:      # noqa: BLE001 - 单页异常不应带崩整个界面
            self.statusBar().showMessage("页面加载异常：%s" % exc)

    # ------------------------------------------------------------ 顶栏状态

    def _refresh_chips(self) -> None:
        c = self.ctx
        self.chip_project.setText("项目：%s" % _project_label())
        self.chip_project.setToolTip(str(paths.data_home()))
        if c.platform:
            self.chip_platform.setText("平台：%s%s" % (c.platform, "-" + c.date if c.date else ""))
        else:
            self.chip_platform.setText("平台：—")
        if c.section == "auto":
            prof = c.current_profile()
            self.chip_section.setText("矿段：自动 → %s" % prof.name.split("（")[0])
        else:
            prof = c.current_profile()
            self.chip_section.setText("矿段：%s" % prof.name.split("（")[0])
        running = runner().running_names()
        if running:
            self.chip_task.setText("运行中：%s" % running[-1][:18])
            self.chip_task.setObjectName("chipPrimary")
        else:
            self.chip_task.setText("空闲")
            self.chip_task.setObjectName("chip")
        self.chip_task.setStyleSheet("")     # 让 QSS 按 objectName 重新生效
        self.chip_task.style().unpolish(self.chip_task)
        self.chip_task.style().polish(self.chip_task)

    # ------------------------------------------------------------ 关闭

    def closeEvent(self, event):
        active = runner().running_names()
        if active:
            from PySide6.QtWidgets import QMessageBox

            ok = QMessageBox.question(
                self, "还有任务在跑",
                "以下任务正在执行：\n  %s\n\n关闭会终止它们（已写出的文件会保留）。确定关闭？"
                % "\n  ".join(active),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if ok != QMessageBox.Yes:
                event.ignore()
                return
            runner().cancel_all()
        self.ctx.state.save()
        event.accept()
