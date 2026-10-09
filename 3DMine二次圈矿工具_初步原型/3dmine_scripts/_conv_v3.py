# -*- coding: utf-8 -*-
"""稳健版 DXF -> DWG(AC1024) 转换：清进程 -> 启动 -> 轮询 COM -> Open -> SaveAs -> 校验。"""
import os, sys, time, subprocess

DXF = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\3940平台 1004二次圈矿矿块图_3块版_full.dxf"
DWG = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\3940平台 1004二次圈矿矿块图_3块版_2010.dwg"
ACAD_EXE = r"E:\gzRJ\CAD\AutoCAD 2023\acad.exe"

os.system("taskkill /IM acad.exe /F >nul 2>nul")
time.sleep(4)
subprocess.Popen([ACAD_EXE], cwd=os.path.dirname(ACAD_EXE))

import win32com.client
import pythoncom
pythoncom.CoInitialize()
acad = None
for i in range(90):
    try:
        acad = win32com.client.Dispatch("AutoCAD.Application")
        print(f"COM ready {i*2}s", flush=True)
        break
    except Exception:
        time.sleep(2)
if acad is None:
    print("FAIL: AutoCAD COM not ready")
    sys.exit(1)
try:
    acad.Visible = False
except Exception:
    pass
time.sleep(2)
try:
    doc = acad.Documents.Open(DXF, True)
except Exception as ex:
    print("Open err:", ex, flush=True)
    # 若有文档已打开，直接使用
    try:
        doc = acad.ActiveDocument
    except Exception:
        sys.exit(1)
time.sleep(3)
if os.path.exists(DWG):
    os.remove(DWG)
doc.SaveAs(DWG, 48)  # AC1024 R2010
time.sleep(1)
with open(DWG, "rb") as fp:
    head = fp.read(6).decode("ascii", errors="ignore")
print("DWG:", DWG, "head:", head, "size:", os.path.getsize(DWG), flush=True)
doc.Close(False)
pythoncom.CoUninitialize()
print("DONE")
