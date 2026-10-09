"""验证窗口标题栏左上角是否真的换成了 app.ico：截图窗口左上角看一眼。"""

import ctypes
import ctypes.wintypes as wt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk

from PIL import Image, ImageGrab

import gui

ctypes.windll.user32.SetProcessDPIAware()

gui.set_app_user_model_id()      # 先声明 AppUserModelID，再建窗口
root = tk.Tk()
root.title("炮孔数据报告汇总工具")
root.geometry("420x260+120+120")
gui.set_window_icon(root)
root.update_idletasks()
root.update()
root.attributes("-topmost", True)
root.lift()
root.focus_force()
root.update()

hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
rect = wt.RECT()
ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
print("窗口矩形:", rect.left, rect.top, rect.right, rect.bottom,
      "| rootx/y:", root.winfo_rootx(), root.winfo_rooty())
shot = ImageGrab.grab(bbox=(rect.left, rect.top, rect.left + 300, rect.top + 42))
out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_out", "titlebar.png")
shot.save(out)

# 任务栏图标（屏幕底部）：直接截全屏再取底带，避免坐标系误差
full = ImageGrab.grab()
print("全屏尺寸:", full.size)
bottom = full.crop((0, full.height - 130, full.width, full.height))
bottom.save(os.path.join(os.path.dirname(out), "taskbar.png"))
root.destroy()
print("截图已保存：", out)
