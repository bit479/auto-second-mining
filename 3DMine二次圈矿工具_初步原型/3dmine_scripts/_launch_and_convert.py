# -*- coding: utf-8 -*-
"""启动 AutoCAD -> 等待 COM 就绪 -> 连接 -> 打印枚举常量 -> 转 DWG。"""
import os, subprocess, time
import win32com.client
import pythoncom

ACAD_EXE = r"E:\gzRJ\CAD\AutoCAD 2023\acad.exe"
DXF = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\3940平台 1004二次圈矿矿块图_3块版_full.dxf"
TMP = r"D:\WK\N CRT\dwg_save_test4"
os.makedirs(TMP, exist_ok=True)

def dwg_version(p):
    with open(p, "rb") as fp:
        return fp.read(6).decode("ascii", errors="ignore")

# 1) 启动 AutoCAD
if not any(p.lower().endswith("acad.exe") for p in os.popen("tasklist").read().splitlines() if "acad" in p.lower()):
    subprocess.Popen([ACAD_EXE], cwd=os.path.dirname(ACAD_EXE))
    print("AutoCAD launching...")
else:
    print("AutoCAD already running")

# 2) 等待 COM 就绪（最多 120s）
pythoncom.CoInitialize()
acad = None
for i in range(60):
    try:
        acad = win32com.client.Dispatch("AutoCAD.Application")
        print(f"COM ready after {i*2}s")
        break
    except Exception as e:
        time.sleep(2)
if acad is None:
    print("FAIL: AutoCAD COM not ready")
    raise SystemExit(1)
try:
    acad.Visible = False
except Exception:
    pass
print("version:", acad.Version)

# 3) 枚举常量
from win32com.client import gencache, constants
try:
    gencache.EnsureModule(acad._oleobj_.GetTypeInfo().GetContainingTypeLib()[0], 0, 1, 0)
except Exception as e:
    print("gencache note:", e)
names = ["ac2010_dwg", "acR2010_dwg", "ac2010_dxf", "ac2013_dwg", "ac2018_dwg",
         "ac2007_dwg", "ac2004_dwg", "ac2000_dwg"]
for n in names:
    try:
        print(f"constants.{n} = {getattr(constants, n)}")
    except Exception as e:
        print(f"constants.{n}: no")

# 4) 打开 DXF 转 DWG（优先 constants.ac2010_dwg）
doc = acad.Documents.Open(DXF, True)
tried = []
if hasattr(constants, "ac2010_dwg"):
    tried.append(("constants.ac2010_dwg", int(constants.ac2010_dwg)))
for n in [48, 49, 50, 51, 52, 60, 61]:
    tried.append((f"enum{n}", n))
for name, val in tried:
    p = os.path.join(TMP, f"out_{name.replace('.', '_')}.dwg")
    if os.path.exists(p):
        os.remove(p)
    try:
        doc.SaveAs(p, val)
        print(f"{name}: -> {dwg_version(p)} size={os.path.getsize(p)}")
    except Exception as e:
        print(f"{name}: ERR {e}")
doc.Close(False)
try:
    acad.Quit()
except Exception:
    pass
pythoncom.CoUninitialize()
print("DONE")
