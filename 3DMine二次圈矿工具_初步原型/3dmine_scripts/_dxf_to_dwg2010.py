# -*- coding: utf-8 -*-
"""DXF -> DWG(R2010) 转换：先启动 acad.exe，等 COM 就绪再连接，SaveAs enum=48。"""
import os, subprocess, time, sys
import win32com.client
import pythoncom

ACAD_EXE = r"E:\gzRJ\CAD\AutoCAD 2023\acad.exe"
DXF = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\3940平台 1004二次圈矿矿块图_3块版_full.dxf"
DWG = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\3940平台 1004二次圈矿矿块图_3块版_2010.dwg"

def acad_running():
    out = os.popen("tasklist /FI \"IMAGENAME eq acad.exe\"").read()
    return "acad.exe" in out

def ensure_started():
    if not acad_running():
        print("启动 acad.exe ...")
        subprocess.Popen([ACAD_EXE], cwd=os.path.dirname(ACAD_EXE))
    else:
        print("acad.exe 已在运行")

pythoncom.CoInitialize()
ensure_started()
acad = None
for i in range(90):
    try:
        acad = win32com.client.Dispatch("AutoCAD.Application")
        print(f"COM 就绪（{i*2}s）")
        break
    except Exception:
        time.sleep(2)
if acad is None:
    print("FAIL: AutoCAD COM 未就绪")
    sys.exit(1)
try:
    acad.Visible = False
except Exception:
    pass
print("version:", acad.Version)

doc = acad.Documents.Open(DXF, True)
if os.path.exists(DWG):
    os.remove(DWG)
doc.SaveAs(DWG, 48)  # ac2010_dwg = AC1024 (R2010)
with open(DWG, "rb") as fp:
    head = fp.read(6).decode("ascii", errors="ignore")
print("保存:", DWG, "版本头:", head, "大小:", os.path.getsize(DWG))
doc.Close(False)
pythoncom.CoUninitialize()
print("DONE")
