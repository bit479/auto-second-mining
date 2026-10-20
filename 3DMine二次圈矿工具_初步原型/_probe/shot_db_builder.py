# -*- coding: utf-8 -*-
"""截一张「新建炮孔数据库」窗口图（验收/说明用）。"""
import sys
import time
import tkinter as tk
from ctypes import wintypes
import ctypes
from pathlib import Path

from PIL import ImageGrab

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "client"))
from db_builder import DbBuilder      # noqa: E402

TXT = Path(r"D:\WK\N CRT\北部山头3940平台2026\7、单日数据\北部山头3940平台-0915"
           r"\BS-3940-0915-P1-P47.txt")
GRADES = ROOT / "_probe" / "0915_grades.md"
OUT = ROOT / "sample_data" / "output" / "v1.9_数据库生成界面.png"


def main():
    root = tk.Tk()
    root.withdraw()
    d = DbBuilder(root, TXT)
    d.txt_grades.insert("1.0", GRADES.read_text(encoding="utf-8"))
    d.win.geometry("920x700+80+20")
    d.win.deiconify()
    d.win.lift()
    d.win.attributes("-topmost", True)
    d.win.focus_force()
    d.win.update_idletasks()
    root.update()
    time.sleep(1.0)
    root.update()
    d.win.lift()
    d.win.attributes("-topmost", True)
    d.win.update()
    hwnd = int(d.win.wm_frame(), 16)
    rect = wintypes.RECT()
    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
    try:
        scale = ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100.0
    except Exception:
        scale = 1.0
    x, y = int(rect.left * scale), int(rect.top * scale)
    w, h = int((rect.right - rect.left) * scale), int((rect.bottom - rect.top) * scale)
    print("window:", d.win.winfo_geometry(), "bbox:", (x, y, w, h))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    ImageGrab.grab(bbox=(x, y, x + w, y + h)).save(OUT)
    ImageGrab.grab(all_screens=True).save(
        ROOT / "sample_data" / "output" / "v1.9_全屏调试.png")
    print("截图 ->", OUT)
    root.destroy()


if __name__ == "__main__":
    main()
