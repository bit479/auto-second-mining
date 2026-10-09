# -*- coding: utf-8 -*-
import ctypes
from ctypes import wintypes as wt

user32 = ctypes.windll.user32

@ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
def enum_proc(hwnd, lparam):
    if not user32.IsWindowVisible(hwnd):
        return True
    length = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    title = buf.value
    pid = wt.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    rect = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    cls = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, cls, 256)
    if pid.value and "VisualMine" in title or "3DMine" in title or "3Dmine" in title or "授权" in title or "登录" in title:
        print("hwnd=%s pid=%s title=[%s] class=[%s] rect=(%d,%d,%d,%d)" % (
            hwnd, pid.value, title, cls.value, rect.left, rect.top, rect.right, rect.bottom))
    return True

user32.EnumWindows(enum_proc, 0)
print("enum done")
