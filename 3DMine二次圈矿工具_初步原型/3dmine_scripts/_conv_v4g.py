# -*- coding: utf-8 -*-
"""v4g 热实例转换：预启动 acad 等待完全加载 -> Dispatch -> Open -> SaveAs(48) -> 校验。"""
import os, sys, time, subprocess

DXF = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\3940平台 1004二次圈矿矿块图_3块版_full.dxf"
DWG = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\3940平台 1004二次圈矿矿块图_3块版_2010.dwg"
ACAD_EXE = r"E:\gzRJ\CAD\AutoCAD 2023\acad.exe"

os.system("taskkill /IM acad.exe /F >nul 2>nul")
time.sleep(6)
print("launch acad (prewarm)", flush=True)
subprocess.Popen([ACAD_EXE, "/nologo"], cwd=os.path.dirname(ACAD_EXE))
print("wait 180s for acad full load...", flush=True)
time.sleep(180)

import win32com.client
import pythoncom
pythoncom.CoInitialize()
acad = None
for i in range(60):
    try:
        acad = win32com.client.Dispatch("AutoCAD.Application")
        print(f"COM ready {i+1}s", flush=True)
        break
    except Exception:
        time.sleep(1)
if acad is None:
    print("FAIL: COM not ready", flush=True)
    os.system("taskkill /IM acad.exe /F >nul 2>nul")
    sys.exit(1)
try:
    acad.Visible = False
except Exception:
    pass
time.sleep(3)
try:
    doc = acad.Documents.Open(DXF, True)
    print("opened dxf", flush=True)
except Exception as ex:
    print("Open err:", ex, flush=True)
    try:
        doc = acad.ActiveDocument
        print("use active doc", flush=True)
    except Exception:
        os.system("taskkill /IM acad.exe /F >nul 2>nul")
        sys.exit(1)
time.sleep(5)
if os.path.exists(DWG):
    try:
        os.remove(DWG)
    except Exception:
        pass
doc.SaveAs(DWG, 48)
time.sleep(2)
with open(DWG, "rb") as fp:
    head = fp.read(6).decode("ascii", errors="ignore")
print("DWG:", DWG, "head:", head, "size:", os.path.getsize(DWG), flush=True)
try:
    doc.Close(False)
except Exception:
    pass
time.sleep(2)
os.system("taskkill /IM acad.exe /F >nul 2>nul")
pythoncom.CoUninitialize()
print("DONE", flush=True)
