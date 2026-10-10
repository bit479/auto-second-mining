"""Excel 差异对比工具 —— 应用图标与任务栏标识。

- APP_USER_MODEL_ID: 必须在创建 Tk() 之前调用 set_app_user_model_id()，
  否则 Windows 任务栏会显示 Python 默认图标而非本程序图标。
- set_window_icon(root): 设置标题栏左上角 + 任务栏图标。
- PNG_PATH: 供 GUI 内嵌展示(应用内 logo)。
"""
from __future__ import annotations

import os
from pathlib import Path

try:
    import tkinter as tk
except Exception:  # pragma: no cover
    tk = None

ASSETS = Path(__file__).resolve().parent / "assets"
ICON_PATH = ASSETS / "app.ico"
PNG_PATH = ASSETS / "app.png"

APP_USER_MODEL_ID = "ExcelCompare.Tool.1"


def set_app_user_model_id():
    """在 Tk() 之前调用，确保任务栏图标独立于 python.exe。"""
    try:
        ctypes = __import__("ctypes")
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            APP_USER_MODEL_ID)
    except Exception:
        pass


def set_window_icon(root):
    """设置窗口标题栏与任务栏图标。"""
    try:
        if tk is None:
            return
        if ICON_PATH.exists():
            root.iconbitmap(default=str(ICON_PATH))
        if PNG_PATH.exists():
            try:
                img = tk.PhotoImage(file=str(PNG_PATH))
                root.iconphoto(True, img)
                # 防止被 GC
                root._app_logo_img = img
            except Exception:
                pass
    except Exception:
        pass


def get_logo_path():
    return str(PNG_PATH) if PNG_PATH.exists() else None
