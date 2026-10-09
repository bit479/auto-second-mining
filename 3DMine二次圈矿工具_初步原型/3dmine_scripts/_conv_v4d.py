# -*- coding: utf-8 -*-
"""v4d 稳健转换：清 acad -> 启动 -> 长等待 -> 轮询 COM -> Open -> SaveAs(48) -> 校验 -> 清理。"""
import os, sys, time, subprocess

DXF = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\3940平台 1004二次圈矿矿块图_3块版_full.dxf"
DWG = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\3940平台 1004二次圈矿矿块图_3块版_2010.dwg"
ACAD_EXE = r"E:\gzRJ\CAD\AutoCAD 2023\acad.exe"

print("kill acad", flush=True)
os.system("taskkill /IM acad.exe /F >nul 2>nul")
time.sleep(6)
print("launch acad", flush=True)
subprocess.Popen([ACAD_EXE], cwd=os.path.dirname(ACAD_EXE))
time.sleep(20)

import win32com.client
import pythoncom
pythoncom.CoInitialize()
acad = None
for i in range(300):
    try:
        acad = win32com.client.Dispatch("AutoCAD.Application")
        print(f"COM ready {i+1}s", flush=True)
        break
    except Exception:
        time.sleep(1)
if acad is None:
    print("FAIL: AutoCAD COM not ready after 300s", flush=True)
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
doc.SaveAs(DWG, 48)  # AC1024 R2010
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
