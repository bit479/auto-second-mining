# -*- coding: utf-8 -*-
"""主窗口：沉浸式标题栏 + 左侧导航 + 中央工作区（QStackedWidget）。

窗口是无边框的，但没有放弃任何 Windows 原生窗口行为：
    · WM_NCHITTEST 把标题栏空白区交给系统 → 拖动、双击最大化、拖到边缘贴靠都原生；
    · 最大化按钮返回 HTMAXBUTTON → Win11 Snap Layout 悬停浮层照常弹出；
    · 四边 6px 返回缩放命中码 → 原生缩放；
    · WM_GETMINMAXINFO 把最大化尺寸限制在「工作区」→ 不遮挡任务栏。
"""

from __future__ import annotations

import sys

from PySide6.QtCore import QEvent, QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QCursor, QIcon
from PySide6.QtWidgets import (
    QAbstractButton, QApplication, QHBoxLayout, QLabel, QMainWindow, QStackedWidget,
    QVBoxLayout, QWidget,
)

from . import APP_NAME, APP_NAME_EN, APP_VERSION
from . import icons, theme
from .components import shell, widgets as W
from .components.drop_overlay import DropOverlay
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
from .services.drop_manager import GlobalFileDropManager
from .services.runner import runner

# 分组 → [(页面 key, 图标, 菜单文字)]
NAV = [
    ("工作空间", [("dashboard", "dashboard", "工作台"),
                  ("single", "target", "单炮区二次圈矿"),
                  ("batch", "layers", "批量处理")]),
    ("数据管理", [("manual", "pen", "人工圈矿与参数标定"),
                  ("composite", "map", "综合图管理"),
                  ("excel", "spreadsheet", "Excel 数据工具"),
                  ("database", "database", "炮孔数据库生成")]),
    ("系统管理", [("params", "sliders", "参数管理"),
                  ("diagnostics", "clipboard", "验收与诊断"),
                  ("settings", "settings", "系统设置")]),
]

GROUP_OF = {key: group for group, items in NAV for key, _ic, _tx in items}


def _project_label() -> str:
    home = paths.data_home()
    return home.parent.name if paths.is_frozen() else home.name


# ---------------------------------------------------------------- Win32 常量
WM_NCHITTEST = 0x0084
WM_GETMINMAXINFO = 0x0024
WM_NCLBUTTONDOWN = 0x00A1
WM_NCLBUTTONDBLCLK = 0x00A3
HTCLIENT, HTCAPTION, HTMAXBUTTON = 1, 2, 9
HTLEFT, HTRIGHT, HTTOP, HTTOPLEFT = 10, 11, 12, 13
HTTOPRIGHT, HTBOTTOM, HTBOTTOMLEFT, HTBOTTOMRIGHT = 14, 15, 16, 17
_RESIZE_BORDER = 6


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("%s  %s" % (APP_NAME, APP_VERSION))
        self.setWindowIcon(QIcon(icons.pixmap("pick", theme.PRIMARY, 64)))
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setMinimumSize(1180, 700)
        self.ctx = C.context()
        self._last_max_toggle = 0.0

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ---------------- 标题栏
        self.titlebar = shell.TitleBar()
        outer.addWidget(self.titlebar)

        # ---------------- 主体：侧栏 + 工作区
        body = QWidget()
        bl = QHBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)
        self.sidebar = shell.Sidebar(NAV)
        self.sidebar.bind(self.navigate)
        self.sidebar.set_footer(APP_VERSION, paths.build_stamp())
        bl.addWidget(self.sidebar)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)
        self.stack = QStackedWidget()
        self.stack.setObjectName("workspace")
        rl.addWidget(self.stack, 1)

        self.footer = QWidget()
        self.footer.setObjectName("appFooter")
        fl = QHBoxLayout(self.footer)
        fl.setContentsMargins(theme.CONTENT_PAD_X, 0, 16, 0)
        fl.setSpacing(10)
        self.lb_status = QLabel("就绪")
        self.lb_status.setObjectName("statusText")
        self.lb_env = QLabel("")
        self.lb_env.setObjectName("statusText")
        fl.addWidget(self.lb_status)
        fl.addStretch(1)
        fl.addWidget(self.lb_env)
        rl.addWidget(self.footer)
        bl.addWidget(right, 1)
        outer.addWidget(body, 1)

        # ---------------- 页面
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
        for page in self.pages.values():
            self.stack.addWidget(page)
        dash = self.pages["dashboard"]
        if hasattr(dash, "request_page"):
            dash.request_page.connect(self.navigate)

        # ---------------- 全局 TXT 拖放：任意页面拖入都可自动导入
        self.setAcceptDrops(True)
        self.drop_overlay = DropOverlay(self)
        self.drop_manager = GlobalFileDropManager(self, self)
        self.drop_manager.hint.connect(self._on_drop_hint)
        self.drop_manager.busy_changed.connect(self._on_drop_busy)
        self.drop_manager.finished.connect(self._on_txt_imported)
        self.drop_manager.failed.connect(self._on_import_failed)
        db_page = self.pages.get("database")
        if hasattr(db_page, "request_import"):
            db_page.request_import.connect(self.drop_manager.start_import)

        self._wire()
        self._restore_geometry()
        self.navigate(self.ctx.state.get("last_page", "dashboard") or "dashboard")

        # 非客户区收不到 Qt 的 enter/leave，窗口按钮 hover 用轻量轮询补齐
        self._hover_timer = QTimer(self)
        self._hover_timer.setInterval(90)
        self._hover_timer.timeout.connect(self._poll_window_button_hover)
        self._hover_timer.start()

    # ------------------------------------------------------------ 绑定

    def _wire(self) -> None:
        self.ctx.changed.connect(self._refresh_chips)
        self.ctx.task_added.connect(self._refresh_chips)
        runner().log.connect(self._on_log)
        runner().state.connect(lambda tid, st: self._refresh_chips())
        runner().finished.connect(lambda tid, code: self._refresh_chips())
        self.titlebar.btn_min.clicked.connect(self.showMinimized)
        self.titlebar.btn_max.clicked.connect(self._toggle_max)
        self.titlebar.btn_close.clicked.connect(self.close)
        self.titlebar.btn_settings.clicked.connect(lambda: self.navigate("settings"))
        self._refresh_chips()

    def set_status(self, text: str) -> None:
        self.lb_status.setText(text)

    def _on_log(self, tid: str, line: str) -> None:
        if line.startswith("[开始]"):
            self.set_status(line.replace("[开始]", "正在执行："))

    # ------------------------------------------------------------ 导航

    def navigate(self, key: str) -> None:
        page = self.pages.get(key)
        if page is None:
            return
        self.stack.setCurrentWidget(page)
        self.sidebar.set_active(key)
        self.titlebar.set_page(GROUP_OF.get(key, "工作空间"), page.TITLE or key)
        self.ctx.state.set("last_page", key)
        try:
            page.on_show()
        except Exception as exc:      # noqa: BLE001 - 单页异常不应带崩整个界面
            self.set_status("页面加载异常：%s" % exc)

    # ------------------------------------------------------------ 顶栏状态

    def _refresh_chips(self) -> None:
        c = self.ctx
        project = _project_label()
        platform = "%s-%s" % (c.platform, c.date) if (c.platform and c.date) else (c.platform or "")
        prof = c.current_profile()
        section = prof.name.split("（")[0]
        if c.section == "auto":
            section = "%s（自动）" % section
        running = runner().running_names()
        if running:
            state = "运行中 · %s" % running[-1]
        else:
            state = "空闲"
        self.titlebar.set_info(project, platform, section, state, busy=bool(running))
        home = str(paths.data_home())
        fm = self.lb_env.fontMetrics()
        self.lb_env.setText(fm.elidedText("数据目录 %s" % home, Qt.ElideMiddle, 430))
        self.lb_env.setToolTip(home)

    # ------------------------------------------------------------ 窗口

    def _toggle_max(self) -> None:
        import time

        now = time.time()
        if now - self._last_max_toggle < 0.35:      # Windows 与 Qt 可能各触发一次
            return
        self._last_max_toggle = now
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            self.titlebar.set_maximized(self.isMaximized())

    def _poll_window_button_hover(self) -> None:
        if not self.isActiveWindow():
            return
        pos = self.mapFromGlobal(QCursor.pos())
        for btn in (self.titlebar.btn_min, self.titlebar.btn_max, self.titlebar.btn_close):
            local = btn.mapFrom(self, pos)
            btn.set_hover(btn.rect().contains(local))

    def showEvent(self, event) -> None:
        super().showEvent(event)
        _dwm_polish(self)
        if getattr(self, "drop_overlay", None) is not None:
            self.drop_overlay.setGeometry(self.rect())

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        overlay = getattr(self, "drop_overlay", None)
        if overlay is not None:
            overlay.setGeometry(self.rect())
            overlay.raise_()

    # ------------------------------------------------------------ 全局拖放

    def _on_drop_hint(self, kind: str, text: str) -> None:
        ov = getattr(self, "drop_overlay", None)
        if ov is None:
            return
        if kind == "drop":
            ov.show_drop(text)
        elif kind == "busy":
            ov.show_busy(text)
        elif kind == "hide":
            ov.hide_overlay()
        elif kind == "reject":
            ov.show_toast(False, text)
        else:
            ov.show_toast(True, text)

    def _on_drop_busy(self, busy: bool) -> None:
        self.set_status("正在解析 TXT 坐标文件…（Esc 取消）" if busy else "就绪")

    def _on_txt_imported(self, task) -> None:
        """解析成功：写入上下文 → 跳到炮孔数据库生成页 → 自动填充。"""
        self.ctx.txt_import = task
        self.ctx.txt_import_changed.emit()
        self.navigate("database")
        page = self.pages.get("database")
        if page is not None and hasattr(page, "apply_import"):
            page.apply_import(task)

        plat = task.platform or "—"
        date = task.date or "—"
        if task.blocked:
            title = "已导入，但有 %d 处问题需要处理" % len(task.errors)
            detail = "%s · 平台 %s · 日期 %s · 有效 %d 孔" % (
                task.source_name, plat, date, task.valid_rows)
            self.drop_overlay.show_toast(False, title, detail)
            self.set_status("TXT 已导入（存在问题）：%s" % task.source_name)
        else:
            title = "已导入 %d 孔 · 平台 %s · 日期 %s" % (task.valid_rows, plat, date)
            self.drop_overlay.show_toast(True, title, task.source_name)
            self.set_status("TXT 已导入：%s" % task.source_name)

    def _on_import_failed(self, message: str) -> None:
        self.set_status("TXT 导入失败：%s" % message)

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
        if not self.isMaximized():
            g = self.geometry()
            self.ctx.state.set("win_geom", [g.x(), g.y(), g.width(), g.height()])
        event.accept()

    def _restore_geometry(self) -> None:
        scr = QApplication.primaryScreen()
        avail = scr.availableGeometry() if scr is not None else QRect(0, 0, 1440, 900)
        geom = self.ctx.state.get("win_geom")
        if isinstance(geom, list) and len(geom) == 4:
            rect = QRect(*[int(v) for v in geom])
            if avail.intersects(rect):
                # 分辨率/缩放变化后，旧位置可能落到屏幕外 → 夹回可用区域
                w = min(rect.width(), avail.width())
                h = min(rect.height(), avail.height())
                x = max(avail.x(), min(rect.x(), avail.x() + avail.width() - w))
                y = max(avail.y(), min(rect.y(), avail.y() + avail.height() - h))
                self.setGeometry(QRect(x, y, w, h))
                return
        w = min(1440, max(1180, avail.width() - 80))
        h = min(900, max(700, avail.height() - 80))
        self.resize(w, h)
        self.move(avail.x() + (avail.width() - w) // 2,
                  avail.y() + max(0, (avail.height() - h) // 2 - 20))

    # ------------------------------------------------------------ Win32 原生行为

    def nativeEvent(self, eventType, message):
        if sys.platform == "win32":
            try:
                return self._win_native(eventType, message)
            except Exception:            # noqa: BLE001 - 原生调用失败时退回 Qt 默认
                pass
        return super().nativeEvent(eventType, message)

    def _win_native(self, eventType, message):
        import ctypes
        from ctypes import wintypes

        if bytes(eventType) not in (b"windows_generic_MSG", b"windows_dispatcher_MSG"):
            return super().nativeEvent(eventType, message)
        msg = wintypes.MSG.from_address(int(message))

        if msg.message == WM_GETMINMAXINFO:
            return self._limit_to_work_area(msg, wintypes, ctypes)

        if msg.message == WM_NCHITTEST:
            hit = self._hit_test()
            if hit is not None:
                # Qt 期望返回 (handled, result)
                return True, hit

        # 非客户区（标题栏）的点击 Qt 不会自己处理，这里补上：
        #   · 最大化键（HTMAXBUTTON，Win11 贴靠浮层依赖这个命中码）→ 切换最大化/还原
        #   · 标题栏空白处（HTCAPTION）双击 → 切换最大化/还原
        if msg.message == WM_NCLBUTTONDOWN and int(msg.wParam) == HTMAXBUTTON:
            self._toggle_max()
            return True, 0
        if msg.message == WM_NCLBUTTONDBLCLK and int(msg.wParam) in (HTMAXBUTTON, HTCAPTION):
            self._toggle_max()
            return True, 0
        return super().nativeEvent(eventType, message)

    def _hit_test(self, pos=None) -> int | None:
        """返回 Win32 命中码；pos 为空时取当前光标（WM_NCHITTEST 的实际语义）。"""
        if pos is None:
            pos = self.mapFromGlobal(QCursor.pos())
        pos = QPoint(pos.x(), pos.y())
        if not self.rect().contains(pos):
            return None

        if not self.isMaximized():
            x, y = pos.x(), pos.y()
            w, h = self.width(), self.height()
            b = _RESIZE_BORDER
            left, right = x < b, x >= w - b
            top, bottom = y < b, y >= h - b
            if top and left:
                return HTTOPLEFT
            if top and right:
                return HTTOPRIGHT
            if bottom and left:
                return HTBOTTOMLEFT
            if bottom and right:
                return HTBOTTOMRIGHT
            if left:
                return HTLEFT
            if right:
                return HTRIGHT
            if top:
                return HTTOP
            if bottom:
                return HTBOTTOM

        if pos.y() < self.titlebar.height():
            node = self.childAt(pos)
            while node is not None:
                if node is self.titlebar.btn_max:
                    return HTMAXBUTTON          # 交给系统：点击最大化 + Win11 贴靠浮层
                if node is self.titlebar.btn_min or node is self.titlebar.btn_close:
                    return HTCLIENT
                if isinstance(node, QAbstractButton):
                    return HTCLIENT
                node = node.parentWidget()
            return HTCAPTION                    # 拖动 / 双击最大化 / 拖边贴靠
        return HTCLIENT

    def _limit_to_work_area(self, msg, wintypes, ctypes):
        class MONITORINFO(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.DWORD),
                        ("rcMonitor", wintypes.RECT),
                        ("rcWork", wintypes.RECT),
                        ("dwFlags", wintypes.DWORD)]

        class MINMAXINFO(ctypes.Structure):
            _fields_ = [("ptReserved", wintypes.POINT),
                        ("ptMaxSize", wintypes.POINT),
                        ("ptMaxPosition", wintypes.POINT),
                        ("ptMinTrackSize", wintypes.POINT),
                        ("ptMaxTrackSize", wintypes.POINT)]

        hwnd = int(self.winId())
        user32 = ctypes.windll.user32
        MONITOR_DEFAULTTONEAREST = 2
        hmon = user32.MonitorFromWindow(wintypes.HWND(hwnd), MONITOR_DEFAULTTONEAREST)
        if not hmon:
            return False
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        if not user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
            return False
        mmi = MINMAXINFO.from_address(msg.lParam)
        work, mon = mi.rcWork, mi.rcMonitor
        mmi.ptMaxPosition.x = work.left - mon.left
        mmi.ptMaxPosition.y = work.top - mon.top
        mmi.ptMaxSize.x = max(1, work.right - work.left)
        mmi.ptMaxSize.y = max(1, work.bottom - work.top)
        mmi.ptMinTrackSize.x = self.minimumWidth()
        mmi.ptMinTrackSize.y = self.minimumHeight()
        return True, 0


def _dwm_polish(win: QWidget) -> None:
    """Win11 圆角与深色边框（失败静默，不影响功能）。"""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        hwnd = int(win.winId())
        dwm = ctypes.windll.dwmapi
        # DWMWA_USE_IMMERSIVE_DARK_MODE = 20 / DWMWA_WINDOW_CORNER_PREFERENCE = 33
        one = ctypes.c_int(1)
        dwm.DwmSetWindowAttribute(ctypes.c_void_p(hwnd), 20, ctypes.byref(one), 4)
        round_pref = ctypes.c_int(2)
        dwm.DwmSetWindowAttribute(ctypes.c_void_p(hwnd), 33, ctypes.byref(round_pref), 4)
    except Exception:
        pass
