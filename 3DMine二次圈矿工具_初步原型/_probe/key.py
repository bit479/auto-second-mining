# -*- coding: utf-8 -*-
"""发送按键（供自动化操作 3DMine 菜单）。

用法:
  python key.py esc
  python key.py down
  python key.py enter
  python key.py alt k
"""
from __future__ import annotations

import ctypes
import sys
import time

user32 = ctypes.windll.user32

VK = {"esc": 0x1B, "enter": 0x0D, "down": 0x28, "up": 0x26, "left": 0x25,
      "right": 0x27, "alt": 0x12, "tab": 0x09, "space": 0x20}
KEYEVENTF_KEYUP = 0x0002


def vk(name: str) -> int:
    n = name.lower()
    if n in VK:
        return VK[n]
    if len(n) == 1:
        return ord(n.upper())
    raise SystemExit("unknown key: " + name)


def press(k: int) -> None:
    user32.keybd_event(k, 0, 0, 0)
    time.sleep(0.03)
    user32.keybd_event(k, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.15)


def main() -> None:
    args = sys.argv[1:]
    if len(args) == 2 and args[0].lower() == "alt":
        user32.keybd_event(VK["alt"], 0, 0, 0)
        time.sleep(0.05)
        press(vk(args[1]))
        user32.keybd_event(VK["alt"], 0, KEYEVENTF_KEYUP, 0)
        time.sleep(0.2)
    else:
        for a in args:
            press(vk(a))
    print("sent:", args)


if __name__ == "__main__":
    main()
