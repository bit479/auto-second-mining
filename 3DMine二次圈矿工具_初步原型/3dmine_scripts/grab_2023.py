# -*- coding: utf-8 -*-
"""抓取当前屏幕（含 3DMine 窗口）。"""
import ctypes
from ctypes import wintypes
import struct
import os

user32 = ctypes.windll.user32

# 全屏 BitBlt
w = user32.GetSystemMetrics(0)
h = user32.GetSystemMetrics(1)
hdc_screen = user32.GetDC(0)
hdc_mem = user32.CreateCompatibleDC(hdc_screen)
hbmp = user32.CreateCompatibleBitmap(hdc_screen, w, h)
user32.SelectObject(hdc_mem, hbmp)
user32.BitBlt(hdc_mem, 0, 0, w, h, hdc_screen, 0, 0, 0x00CC0020)

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", ctypes.c_long),
                ("biHeight", ctypes.c_long), ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", ctypes.c_long),
                ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD)]

bmi = BITMAPINFOHEADER()
bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
bmi.biWidth = w
bmi.biHeight = -h
bmi.biPlanes = 1
bmi.biBitCount = 32
bmi.biCompression = 0
buf = ctypes.create_string_buffer(w * h * 4)
user32.GetDIBits(hdc_mem, hbmp, 0, h, buf, ctypes.byref(bmi), 0)

# BGR->RGB 存 BMP
out = bytearray(54 + w * h * 4)
out[0] = 0x42; out[1] = 0x4D
struct.pack_into("<I", out, 2, 54 + w * h * 4)
struct.pack_into("<I", out, 10, 54)
struct.pack_into("<I", out, 14, 40)
struct.pack_into("<i", out, 18, w)
struct.pack_into("<i", out, 22, h)
struct.pack_into("<H", out, 26, 1)
struct.pack_into("<H", out, 28, 32)
src = bytes(buf)
# BMP 行对齐（w*4 通常已对齐）
out[54:] = src
p = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\screen_2023_now.bmp"
open(p, "wb").write(out)
print("saved", p, w, "x", h)
