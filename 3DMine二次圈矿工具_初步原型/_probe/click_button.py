# -*- coding: utf-8 -*-
"""按控件 ID 点击某个对话框按钮（BM_CLICK，不需要前台窗口）。

用法: python click_button.py <pid> <button_text>
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import sys

user32 = ctypes.windll.user32
EnumWindows = user32.EnumWindows
EnumChildWindows = user32.EnumChildWindows
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
BM_CLICK = 0x00F5


def text_of(hwnd) -> str:
    n = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, buf, n + 1)
    return buf.value


def class_of(hwnd) -> str:
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def main() -> None:
    pid = int(sys.argv[1])
    want = sys.argv[2]
    tops = []

    def cb(hwnd, _l):
        p = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value == pid and user32.IsWindowVisible(hwnd) and class_of(hwnd) == "#32770":
            tops.append(hwnd)
        return True

    EnumWindows(WNDENUMPROC(cb), 0)
    if not tops:
        print("no visible dialog")
        return
    dlg = tops[0]
    kids = []

    def kcb(ch, _l):
        kids.append(ch)
        return True

    EnumChildWindows(dlg, WNDENUMPROC(kcb), 0)
    for k in kids:
        t = text_of(k)
        if class_of(k) == "Button" and want in t:
            user32.SendMessageW(k, BM_CLICK, 0, 0)
            print("clicked: %r" % t)
            return
        print("  seen button: %r" % t)
    print("button not found:", want)


if __name__ == "__main__":
    main()
