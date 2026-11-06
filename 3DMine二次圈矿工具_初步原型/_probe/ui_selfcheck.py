# -*- coding: utf-8 -*-
"""v1.16 UI 自检：布局 / 图标 / 文字截断 / 横向滚动 / 原生命中测试。

只读检查，不改任何业务数据。输出一份可粘贴到验收报告的清单。

    python _probe/ui_selfcheck.py [1920x1080] [1.0]
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLIENT = ROOT / "client"
sys.path.insert(0, str(CLIENT))
os.chdir(CLIENT)

SIZE = sys.argv[1] if len(sys.argv) > 1 else "1440x900"
SCALE = sys.argv[2] if len(sys.argv) > 2 else ""
if SCALE:
    os.environ["QT_SCALE_FACTOR"] = SCALE

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QAbstractButton

QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
    Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

from ui_v2 import theme
from ui_v2.main_window import MainWindow, NAV

app = QApplication(sys.argv)
theme.apply_theme(app)

win = MainWindow()
w, h = [int(x) for x in SIZE.lower().split("x")]
win.resize(w, h)
win.show()
app.processEvents()

problems: list[str] = []
notes: list[str] = []

notes.append("窗口 %dx%d  屏幕 DPR=%.2f  逻辑尺寸=%dx%d"
             % (w, h, win.screen().devicePixelRatio(),
                win.width(), win.height()))
notes.append("标题栏高度=%d  侧栏宽度=%d  导航项=%d  页面=%d"
             % (win.titlebar.height(), win.sidebar.width(),
                len(win.sidebar.items), len(win.pages)))

# ---- 导航清单与页面清单一致
nav_keys = [k for _g, items in NAV for k, _i, _t in items]
if sorted(nav_keys) != sorted(win.pages.keys()):
    problems.append("导航项与页面清单不一致：%s vs %s" % (nav_keys, sorted(win.pages)))

for key in nav_keys:
    win.navigate(key)
    app.processEvents()
    page = win.pages[key]

    # 1) 无横向滚动条
    hbar = page.scroll.horizontalScrollBar()
    if hbar.maximum() > 0:
        problems.append("[%s] 内容区出现横向滚动（max=%d）" % (key, hbar.maximum()))

    # 2) 按钮文字不被截断（用 QStyle 给出的真实内容区宽度判断）
    from PySide6.QtWidgets import QStyle, QStyleOptionButton

    for btn in page.findChildren(QPushButton):
        if not btn.isVisible() or not btn.text():
            continue
        opt = QStyleOptionButton()
        btn.initStyleOption(opt)
        rect = btn.style().subElementRect(QStyle.SE_PushButtonContents, opt, btn)
        need = btn.fontMetrics().horizontalAdvance(btn.text())
        if not btn.icon().isNull():
            need += btn.iconSize().width() + 4
        if need > rect.width():
            problems.append("[%s] 按钮文字被截断：%r 需要 %dpx，可用 %dpx"
                            % (key, btn.text(), need, rect.width()))

    # 3) 图标固定尺寸（不被压缩/裁切）
    for lab in page.findChildren(QLabel):
        pm = lab.pixmap()
        if pm is None or pm.isNull():
            continue
        dpr = pm.devicePixelRatio() or 1.0
        lw, lh = pm.width() / dpr, pm.height() / dpr
        if lab.width() < lw - 0.5 or lab.height() < lh - 0.5:
            problems.append("[%s] 图标被裁切：%dx%d 放进 %dx%d"
                            % (key, lw, lh, lab.width(), lab.height()))

    # 4) 图标绘制区域与 iconSize 一致（防止错位）
    for btn in page.findChildren(QAbstractButton):
        ic = btn.icon()
        if ic.isNull():
            continue
        size = btn.iconSize()
        if size.width() <= 0:
            problems.append("[%s] 按钮图标尺寸未设置：%r" % (key, btn.text()))

# ---- 标题栏信息
notes.append("顶栏：%s ｜ %s ｜ %s ｜ %s" % (
    win.titlebar.chip_project._text.text(),
    win.titlebar.chip_platform._text.text(),
    win.titlebar.chip_section._text.text(),
    win.titlebar.chip_status._text.text()))

# ---- 原生命中测试
if sys.platform == "win32":
    win.navigate("dashboard")
    app.processEvents()
    tb = win.titlebar
    from PySide6.QtGui import QCursor

    def hit_at(widget: "QWidget", dx: int, dy: int):
        g = widget.mapToGlobal(widget.rect().center()) if dx is None else None
        return g

    from PySide6.QtCore import QPoint

    results = []
    probes = [
        ("标题栏空白", (win.width() // 2, 24), 2),
        ("最大化按钮", (tb.btn_max.mapTo(win, tb.btn_max.rect().center()).x(),
                        tb.btn_max.mapTo(win, tb.btn_max.rect().center()).y()), 9),
        ("左边界", (2, win.height() // 2), 10),
        ("右边界", (win.width() - 2, win.height() // 2), 11),
        ("内容区", (win.width() // 2, win.height() - 60), 1),
    ]
    for name, (x, y), expect in probes:
        res = win._hit_test(QPoint(x, y))
        ok = (res == expect)
        results.append("%s=%s(%s)" % (name, res, "符合预期" if ok else "预期 %d" % expect))
        if not ok:
            problems.append("命中测试异常：%s 返回 %s，预期 %d" % (name, res, expect))
    notes.append("原生命中： " + " ｜ ".join(results))

    # 最大化后应等于工作区
    win.showMaximized()
    app.processEvents()
    avail = win.screen().availableGeometry()
    notes.append("最大化几何=%dx%d  工作区=%dx%d  任务栏让位=%s"
                 % (win.width(), win.height(), avail.width(), avail.height(),
                    "是" if win.geometry() == avail else "否"))
    win.showNormal()
    app.processEvents()

print("=" * 72)
for n in notes:
    print("·", n)
print("=" * 72)
if problems:
    print("发现问题 %d 项：" % len(problems))
    for p in problems:
        print("  ✗", p)
else:
    print("未发现布局 / 图标 / 截断问题")
