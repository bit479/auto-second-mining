# -*- coding: utf-8 -*-
"""窗口/任务栏图标设置（二次圈矿客户端）。

注意两点（都踩过坑）：
1. 任务栏图标：Windows 默认按 python.exe 归组，必须在本进程创建任何窗口之前
   调用 SetCurrentProcessExplicitAppUserModelID 声明自己的 AppUserModelID；
2. 标题栏图标：tkinter 的 iconbitmap 只有 ``-default`` 形式才接受 .ico，
   普通形式只认 .xbm，传 .ico 会静默失败。
"""
from __future__ import annotations

import ctypes
import os
import sys

ICON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "app.ico")
APP_USER_MODEL_ID = "OreDelineation.Client.1"


def set_app_user_model_id() -> None:
    """必须在 tk.Tk() 之前调用。"""
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:  # noqa: BLE001 - 接口缺失时静默跳过
        pass


def set_window_icon(root) -> None:
    if os.path.exists(ICON_PATH):
        try:
            root.iconbitmap(default=ICON_PATH)
        except Exception:  # noqa: BLE001
            pass
