"""Windows 文件拖放支持 —— 让 tkinter 窗口可以直接接收拖进来的文件。

原理: 通过 ctypes 调用 Shell 的 DragAcceptFiles + 子类化窗口过程拦截 WM_DROPFILES，
解析出拖入的文件路径列表后回调交给上层处理。纯标准库实现，无需安装额外包。

仅 Windows 有效；非 Windows 平台 enable_drop 直接返回 False。
"""
from __future__ import annotations

import ctypes
import os
import sys

WM_DROPFILES = 0x0233
GWLP_WNDPROC = -4

if sys.platform.startswith("win"):
    WNDPROC = ctypes.WINFUNCTYPE(
        ctypes.c_long,
        ctypes.wintypes.HWND,
        ctypes.wintypes.UINT,
        ctypes.wintypes.WPARAM,
        ctypes.wintypes.LPARAM,
    )
else:
    WNDPROC = None

# 保持存活: 全局 trampoline + 每窗口状态
_trampoline = None
_window_state = {}  # hwnd(int) -> (orig_proc_callable, handler)


def _parse_drop(hdrop):
    """解析 HDROP 句柄，返回拖入的文件路径列表。"""
    shell = ctypes.windll.shell32
    count = shell.DragQueryFileW(hdrop, 0xFFFFFFFF, None, 0)
    files = []
    for i in range(count):
        length = shell.DragQueryFileW(hdrop, i, None, 0) + 1
        buf = ctypes.create_unicode_buffer(length)
        shell.DragQueryFileW(hdrop, i, buf, length)
        files.append(buf.value)
    shell.DragFinish(hdrop)
    return files


def _make_trampoline():
    def proc(hwnd, msg, wparam, lparam):
        state = _window_state.get(int(hwnd))
        if state is not None:
            orig_proc, handler = state
            if msg == WM_DROPFILES:
                try:
                    files = _parse_drop(wparam)
                    if handler:
                        handler(files)
                except Exception:
                    pass
                return 0
            if orig_proc is not None:
                return orig_proc(hwnd, msg, wparam, lparam)
        return ctypes.windll.user32.DefWindowProcW(hwnd, msg, wparam, lparam)
    return WNDPROC(proc)


def enable_drop(root, handler):
    """为 tkinter 根窗口启用文件拖放。

    handler(files: list[str]) 会在文件被拖入后调用，files 为完整路径列表。
    返回 True 表示已启用；当前仅 Windows 支持，其它平台返回 False。
    """
    if not sys.platform.startswith("win") or WNDPROC is None:
        return False
    try:
        hwnd = int(root.winfo_id())
    except Exception:
        return False

    user32 = ctypes.windll.user32
    shell32 = ctypes.windll.shell32

    # 声明正确的 64 位参数类型，否则 SetWindowLongPtrW 会因指针溢出报错
    shell32.DragAcceptFiles.argtypes = [ctypes.wintypes.HWND, ctypes.wintypes.BOOL]
    shell32.DragAcceptFiles.restype = None
    user32.GetWindowLongPtrW.argtypes = [ctypes.wintypes.HWND, ctypes.c_int]
    user32.GetWindowLongPtrW.restype = ctypes.c_void_p
    user32.SetWindowLongPtrW.argtypes = [ctypes.wintypes.HWND, ctypes.c_int, WNDPROC]
    user32.SetWindowLongPtrW.restype = WNDPROC

    shell32.DragAcceptFiles(hwnd, True)

    global _trampoline
    if _trampoline is None:
        _trampoline = _make_trampoline()

    orig = user32.GetWindowLongPtrW(hwnd, GWLP_WNDPROC)
    orig_proc = WNDPROC(orig) if orig else None
    _window_state[hwnd] = (orig_proc, handler)

    user32.SetWindowLongPtrW(hwnd, GWLP_WNDPROC, _trampoline)
    return True


# 允许的文件后缀(仅用于上层筛选提示，这里不做强制)
EXCEL_EXTS = (".xlsx", ".xlsm", ".xls", ".csv")


def filter_excel(files):
    return [f for f in files if os.path.splitext(f)[1].lower() in EXCEL_EXTS]
