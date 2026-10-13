# -*- coding: utf-8 -*-
"""读取对话框里按钮的选中状态（BM_GETCHECK）。

用法: python dlg_state.py <pid>
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import sys

user32 = ctypes.windll.user32
EnumWindows = user32.EnumWindows
EnumChildWindows = user32.EnumChildWindows
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
BM_GETCHECK = 0x00F0


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
    tops = []

    def cb(hwnd, _l):
        p = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value == pid and user32.IsWindowVisible(hwnd) and class_of(hwnd) == "#32770":
            tops.append(hwnd)
        return True

    EnumWindows(WNDENUMPROC(cb), 0)
    for dlg in tops:
        print("dialog: %r" % text_of(dlg))
        kids = []

        def kcb(ch, _l):
            kids.append(ch)
            return True

        EnumChildWindows(dlg, WNDENUMPROC(kcb), 0)
        for k in kids:
            if class_of(k) == "Button":
                print("   id=%-5s text=%-12r checked=%s enabled=%s"
                      % (user32.GetDlgCtrlID(k), text_of(k),
                         user32.SendMessageW(k, BM_GETCHECK, 0, 0),
                         bool(user32.IsWindowEnabled(k))))


if __name__ == "__main__":
    main()
