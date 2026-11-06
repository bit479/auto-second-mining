# -*- coding: utf-8 -*-
"""真实鼠标事件验证：标题栏拖动 / 双击最大化（输入在线程里发，避免模态循环卡住主线程）。"""
import ctypes
import os
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "client"))
os.chdir(ROOT / "client")

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)
from ui_v2 import theme
from ui_v2.main_window import MainWindow

theme.apply_theme(app)
win = MainWindow()
win.resize(1300, 820)
win.move(140, 100)
win.show()
win.activateWindow()
win.raise_()

u = ctypes.windll.user32
d = win.devicePixelRatioF()
result = {}


def phys(widget, pt):
    g = widget.mapToGlobal(pt)
    return int(round(g.x() * d)), int(round(g.y() * d))


def worker():
    time.sleep(1.0)
    pt = win.titlebar.rect().center()
    pt.setX(theme.SIDEBAR_W + 260)
    x, y = phys(win.titlebar, pt)
    u.SetCursorPos(x, y)
    time.sleep(0.2)
    u.mouse_event(0x0002, 0, 0, 0, 0)          # 左键按下
    time.sleep(0.25)
    for i in range(1, 13):
        u.SetCursorPos(x + int(90 * d * i / 12), y + int(60 * d * i / 12))
        time.sleep(0.03)
    u.mouse_event(0x0004, 0, 0, 0, 0)          # 左键抬起
    time.sleep(0.7)
    result["pos"] = (win.x(), win.y())

    x, y = phys(win.titlebar, pt)               # 双击标题栏空白
    u.SetCursorPos(x, y)
    time.sleep(0.15)
    for _ in range(2):
        u.mouse_event(0x0002, 0, 0, 0, 0)
        time.sleep(0.02)
        u.mouse_event(0x0004, 0, 0, 0, 0)
        time.sleep(0.08)
    time.sleep(0.9)
    result["dbl_max"] = win.isMaximized()
    result["dbl_size"] = (win.width(), win.height())
    QTimer.singleShot(0, app.quit)


start = (140, 100)
threading.Thread(target=worker, daemon=True).start()
QTimer.singleShot(25000, app.quit)
app.exec()

print("拖动前位置 =", start, "｜ 拖动后位置 =", result.get("pos"),
      "｜", "可拖动 ✓" if result.get("pos") not in (None, start) else "拖动无效 ✗")
print("双击标题栏后：最大化 =", result.get("dbl_max"), "尺寸 =", result.get("dbl_size"))
