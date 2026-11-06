# -*- coding: utf-8 -*-
"""给主窗口截图（PrintWindow，不依赖 ImageGrab 的屏幕坐标）。

用法：
    python _probe/shot_ui.py                # 三个页面各一张
    python _probe/shot_ui.py --page work    # 只截某页
    python _probe/shot_ui.py --size 1180x820
"""
from __future__ import annotations

import ctypes
import os
import sys
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLIENT = ROOT / "client"
sys.path.insert(0, str(CLIENT))
OUT = ROOT / "_probe" / "ui_shots"
OUT.mkdir(parents=True, exist_ok=True)


def grab(root, path: Path) -> bool:
    from PIL import Image

    user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
    hwnd = user32.GetParent(root.winfo_id())
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    w, h = rect.right - rect.left, rect.bottom - rect.top
    if w <= 0 or h <= 0:
        print("窗口尺寸异常：", w, h)
        return False

    hdc = user32.GetWindowDC(hwnd)
    mdc = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    gdi32.SelectObject(mdc, bmp)
    user32.PrintWindow(hwnd, mdc, 2)

    class BIH(ctypes.Structure):
        _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
                    ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
                    ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                    ("biSizeImage", wintypes.DWORD),
                    ("biXPelsPerMeter", wintypes.LONG),
                    ("biYPelsPerMeter", wintypes.LONG),
                    ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD)]

    bi = BIH()
    bi.biSize = ctypes.sizeof(BIH)
    bi.biWidth, bi.biHeight = w, -h
    bi.biPlanes, bi.biBitCount, bi.biCompression = 1, 32, 0
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(bi), 0)

    img = Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1)
    img.convert("RGB").save(path)

    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mdc)
    user32.ReleaseDC(hwnd, hdc)
    return True


def main() -> int:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    size = "1180x820"
    page = None
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--size" and i + 1 < len(args):
            size = args[i + 1]
        elif a == "--page" and i + 1 < len(args):
            page = args[i + 1]

    import tkinter as tk

    import gui

    root = tk.Tk()
    app = gui.App(root)
    root.geometry(size + "+40+40")
    root.update_idletasks()
    root.update()

    pages = [page] if page else ["work", "data", "check"]
    ok = True
    for key in pages:
        app._show_page(key)
        # 让自绘控件把尺寸算完
        for _ in range(3):
            root.update_idletasks()
            root.update()
        target = OUT / ("%s_%s.png" % (key, size))
        if grab(root, target):
            print("已截图：%s" % target)
        else:
            ok = False

    root.destroy()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
