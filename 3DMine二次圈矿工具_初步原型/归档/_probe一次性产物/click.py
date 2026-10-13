# -*- coding: utf-8 -*-
"""鼠标点击/移动助手（供自动化操作 3DMine 菜单）。

用法:
  python click.py move <x> <y>
  python click.py click <x> <y>
  python click.py dclick <x> <y>
"""
from __future__ import annotations

import ctypes
import sys
import time

user32 = ctypes.windll.user32

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004


def move(x: int, y: int) -> None:
    user32.SetCursorPos(x, y)
    time.sleep(0.15)


def click(x: int, y: int) -> None:
    move(x, y)
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.06)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(0.25)


def main() -> None:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass
    cmd = sys.argv[1]
    x, y = int(sys.argv[2]), int(sys.argv[3])
    if cmd == "move":
        move(x, y)
    elif cmd == "click":
        click(x, y)
    elif cmd == "dclick":
        click(x, y)
        click(x, y)
    print("done: %s %d %d  cursor=%s" % (cmd, x, y, user32.GetCursorPos.__name__))


if __name__ == "__main__":
    main()
