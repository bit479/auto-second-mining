# -*- coding: utf-8 -*-
"""用真实鼠标事件点击标题栏「最大化」，验证原生行为（会短暂移动光标）。"""
import ctypes
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "client"))
os.chdir(ROOT / "client")

from PySide6.QtCore import QPoint, Qt
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
u = ctypes.windll.user32
hwnd = int(win.winId())
# 等窗口真正成为前台窗口（脚本启动时首个点击可能只用于激活）
for _ in range(80):
    app.processEvents()
    if u.GetForegroundWindow() == hwnd:
        break
    time.sleep(0.05)
orig = QPoint(*u.GetCursorPos.__self__ and (0, 0)) if False else None

def click_at(widget):
    c = widget.mapToGlobal(widget.rect().center())
    d = win.devicePixelRatioF()          # SetCursorPos 用物理像素
    u.SetCursorPos(int(round(c.x() * d)), int(round(c.y() * d)))
    for _ in range(6):
        app.processEvents()
        time.sleep(0.02)
    u.mouse_event(0x0002, 0, 0, 0, 0)   # LEFTDOWN
    time.sleep(0.06)
    u.mouse_event(0x0004, 0, 0, 0, 0)   # LEFTUP
    for _ in range(40):
        app.processEvents()
        time.sleep(0.03)

dpr = win.devicePixelRatioF()
btn = win.titlebar.btn_max
print("DPR =", dpr, "｜ 最大化按钮屏幕坐标 =",
      btn.mapToGlobal(btn.rect().center()), flush=True)
click_at(btn)
print("第 1 次点击后：最大化 =", win.isMaximized(),
      "尺寸 = %dx%d" % (win.width(), win.height()), flush=True)
click_at(btn)
print("第 2 次点击后：最大化 =", win.isMaximized(),
      "尺寸 = %dx%d" % (win.width(), win.height()), flush=True)
print("工作区 =", win.screen().availableGeometry().width(),
      "x", win.screen().availableGeometry().height())
