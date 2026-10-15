"""通过"开窗前后任务栏差分"精确定位本程序在任务栏上的按钮，并放大截图。"""

import ctypes
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ctypes.windll.user32.SetProcessDPIAware()

from PIL import Image, ImageChops, ImageGrab  # noqa: E402

import gui  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_out")
BAND = (0, 1000, 1920, 1080)   # 屏幕底带


def snap():
    return ImageGrab.grab(bbox=BAND)


gui.set_app_user_model_id()

import tkinter as tk  # noqa: E402

before = snap()

root = tk.Tk()
root.title("炮孔数据报告汇总工具")
root.geometry("420x260+120+120")
gui.set_window_icon(root)
root.update()
root.attributes("-topmost", True)
root.lift()
time.sleep(1.5)
after = snap()

diff = ImageChops.difference(before.convert("RGB"), after.convert("RGB"))
bbox = diff.getbbox()
print("差分区域(BAND 坐标):", bbox, "-> 屏幕 x:", (bbox[0], bbox[2]) if bbox else None)

after.save(os.path.join(OUT, "tb_after.png"))
before.save(os.path.join(OUT, "tb_before.png"))

if bbox:
    x0, x1 = max(0, bbox[0] - 40), min(1920, bbox[2] + 40)
    y0, y1 = max(0, bbox[1] - 10), min(80, bbox[3] + 10)
    crop = after.crop((x0, y0, x1, y1))
    crop = crop.resize((crop.width * 4, crop.height * 4), Image.LANCZOS)
    crop.save(os.path.join(OUT, "tb_button.png"))
    print("按钮特写已保存")

root.destroy()
