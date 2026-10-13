# -*- coding: utf-8 -*-
"""读取指定 pid 的对话框内容（标题 + 所有子控件文本），不需要把窗口置前。

用法: python dlg_text.py <pid>
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import sys

user32 = ctypes.windll.user32
EnumWindows = user32.EnumWindows
EnumChildWindows = user32.EnumChildWindows
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)


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
        if p.value == pid:
            tops.append(hwnd)
        return True

    EnumWindows(WNDENUMPROC(cb), 0)
    for h in tops:
        cls = class_of(h)
        vis = user32.IsWindowVisible(h)
        print("TOP hwnd=%s class=%s visible=%s text=%r" % (h, cls, bool(vis), text_of(h)))
        if cls == "#32770":
            kids = []

            def kcb(ch, _l):
                kids.append(ch)
                return True

            EnumChildWindows(h, WNDENUMPROC(kcb), 0)
            for k in kids:
                print("     child class=%-16s id=%-5s text=%r"
                      % (class_of(k), user32.GetDlgCtrlID(k), text_of(k)))


if __name__ == "__main__":
    main()
