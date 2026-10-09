# -*- coding: utf-8 -*-
"""人工 DWG -> DXF（保留精确属性），再用 ezdxf 精读：文字样式/颜色/hatch尺寸/线宽。"""
import os, subprocess, time
import win32com.client
import pythoncom

DWG = r"D:\WK\N CRT\北部山头3940平台2026\7、单日数据\北部山头3940平台-1004\5、 北部山头3940平台二次圈矿矿块图1004.dwg"
DXFOUT = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\manual_1004.dxf"
ACAD_EXE = r"E:\gzRJ\CAD\AutoCAD 2023\acad.exe"

os.system("taskkill /IM acad.exe /F >nul 2>nul")
time.sleep(3)
subprocess.Popen([ACAD_EXE], cwd=os.path.dirname(ACAD_EXE))
pythoncom.CoInitialize()
acad = None
for i in range(90):
    try:
        acad = win32com.client.Dispatch("AutoCAD.Application")
        print(f"COM ready {i*2}s")
        break
    except Exception:
        time.sleep(2)
if acad is None:
    print("FAIL")
    raise SystemExit(1)
try:
    acad.Visible = False
except Exception:
    pass
acad.Documents.Open(DWG, True)
doc = acad.ActiveDocument
if os.path.exists(DXFOUT):
    os.remove(DXFOUT)
doc.SaveAs(DXFOUT, 13)  # dxf 格式
print("saved:", os.path.exists(DXFOUT), os.path.getsize(DXFOUT) if os.path.exists(DXFOUT) else 0)
doc.Close(False)
pythoncom.CoUninitialize()
print("DONE")
