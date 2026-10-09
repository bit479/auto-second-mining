# -*- coding: utf-8 -*-
"""用 EnsureDispatch + constants 获取 ac2010_dwg 命名枚举。"""
import os
import win32com.client
import pythoncom

pythoncom.CoInitialize()
from win32com.client import gencache, constants
acad = gencache.EnsureDispatch("AutoCAD.Application")
try:
    acad.Visible = False
except Exception as e:
    print("visible set err:", e)
print("version:", acad.Version)
# 打印相关常量
names = ["ac2010_dwg", "acR2010_dwg", "ac2010_dxf", "ac2013_dwg", "ac2018_dwg", "ac2007_dwg", "ac2004_dwg", "ac2000_dwg"]
for n in names:
    try:
        print(f"constants.{n} = {getattr(constants, n)}")
    except Exception as e:
        print(f"constants.{n}: no ({e})")
pythoncom.CoUninitialize()
print("DONE")
