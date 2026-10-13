# -*- coding: utf-8 -*-
"""列出当前桌面上的顶层窗口（标题 + 进程路径），用于确认哪个 3DMine 实例在显示。"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

EnumWindows = user32.EnumWindows
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def proc_path(pid: int) -> str:
    h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return "?"
    try:
        buf = ctypes.create_unicode_buffer(1024)
        size = wt.DWORD(1024)
        if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
            return buf.value
        return "?"
    finally:
        kernel32.CloseHandle(h)


def main() -> None:
    rows = []

    def cb(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        n = user32.GetWindowTextLengthW(hwnd)
        if n <= 0:
            return True
        buf = ctypes.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(hwnd, buf, n + 1)
        pid = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        rect = wt.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        rows.append((buf.value, pid.value, (rect.left, rect.top, rect.right, rect.bottom)))
        return True

    EnumWindows(WNDENUMPROC(cb), 0)
    for title, pid, rect in rows:
        print("%-70s pid=%-7d rect=%s" % (title[:70], pid, rect))
        print("      exe=%s" % proc_path(pid))


if __name__ == "__main__":
    main()
