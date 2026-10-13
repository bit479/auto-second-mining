# -*- coding: utf-8 -*-
"""打开 3DMine 顶部菜单栏的第 <n> 个菜单并执行第 <m> 项（键盘选择，避免误点工具栏）。

用法: python open_and_run.py <菜单横坐标> <菜单纵坐标> [下移次数]
"""
from __future__ import annotations

import ctypes
import sys
import time

user32 = ctypes.windll.user32
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
VK_DOWN, VK_RETURN, VK_ESC = 0x28, 0x0D, 0x1B
KEYEVENTF_KEYUP = 0x0002


def click(x: int, y: int) -> None:
    user32.SetCursorPos(x, y)
    time.sleep(0.2)
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.08)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(0.5)


def press(k: int) -> None:
    user32.keybd_event(k, 0, 0, 0)
    time.sleep(0.05)
    user32.keybd_event(k, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.25)


def main() -> None:
    x, y = int(sys.argv[1]), int(sys.argv[2])
    downs = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    click(x, y)
    for _ in range(downs):
        press(VK_DOWN)
    press(VK_RETURN)
    print("menu(%d,%d) + %d down + enter sent" % (x, y, downs))


if __name__ == "__main__":
    main()
