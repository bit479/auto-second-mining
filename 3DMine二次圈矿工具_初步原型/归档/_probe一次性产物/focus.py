# -*- coding: utf-8 -*-
"""把指定 pid 的顶层窗口还原并置前（用于让 3DMine 出现在桌面上）。

用法: python focus.py <pid>
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import sys
import time

user32 = ctypes.windll.user32

SW_RESTORE = 9
EnumWindows = user32.EnumWindows
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)


def find_window(pid: int) -> int:
    found = {"hwnd": 0}

    def cb(hwnd, _lparam):
        p = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value != pid:
            return True
        if not user32.IsWindowVisible(hwnd):
            return True
        if user32.GetWindowTextLengthW(hwnd) <= 0:
            return True
        found["hwnd"] = hwnd
        return False

    EnumWindows(WNDENUMPROC(cb), 0)
    return found["hwnd"]


def main() -> None:
    pid = int(sys.argv[1])
    hwnd = find_window(pid)
    if not hwnd:
        print("window not found for pid", pid)
        return
    user32.ShowWindow(hwnd, SW_RESTORE)
    time.sleep(0.4)
    ok = user32.SetForegroundWindow(hwnd)
    time.sleep(0.4)
    rect = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    print("hwnd=%s foreground=%s rect=(%d,%d,%d,%d)"
          % (hwnd, ok, rect.left, rect.top, rect.right, rect.bottom))


if __name__ == "__main__":
    main()
