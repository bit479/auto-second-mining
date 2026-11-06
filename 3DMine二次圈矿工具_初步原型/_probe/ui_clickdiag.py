# -*- coding: utf-8 -*-
"""诊断：最大化按钮点击为什么没生效（打印命中的窗口/坐标/前台窗口）。"""
import ctypes
import os
import sys
import time
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "client"))
os.chdir(ROOT / "client")

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)
from ui_v2 import theme
from ui_v2.main_window import MainWindow

theme.apply_theme(app)
win = MainWindow()
win.resize(1200, 800)
win.move(60, 70)
win.show()
win.activateWindow()
win.raise_()
for _ in range(30):
    app.processEvents()
    time.sleep(0.04)

u = ctypes.windll.user32
d = win.devicePixelRatioF()
btn = win.titlebar.btn_max
c = btn.mapToGlobal(btn.rect().center())
px, py = int(round(c.x() * d)), int(round(c.y() * d))

print("DPR =", d)
print("窗口 logical 几何 =", win.geometry().getRect())
print("按钮 logical 中心 =", c, "→ 物理 =", (px, py))
print("窗口 hwnd =", int(win.winId()),
      "｜ 前台 hwnd =", u.GetForegroundWindow())
print("按钮中心命中码 =", win._hit_test(win.mapFromGlobal(c)))

u.SetCursorPos(px, py)
time.sleep(0.2)
pt = wintypes.POINT()
u.GetCursorPos(ctypes.byref(pt))
print("光标实际物理位置 =", (pt.x, pt.y))
# 该点属于哪个窗口
child = wintypes.HWND()
top = u.WindowFromPoint(pt)
print("该点顶层窗口 =", int(top), "｜ 是否本窗口 =", int(top) == int(win.winId()))
u.SetCursorPos(px, py)
time.sleep(0.1)
u.mouse_event(0x0002, 0, 0, 0, 0)
time.sleep(0.08)
u.mouse_event(0x0004, 0, 0, 0, 0)
for _ in range(40):
    app.processEvents()
    time.sleep(0.03)
print("点击后最大化 =", win.isMaximized(), win.size().toTuple())
print("前台 hwnd =", u.GetForegroundWindow())
