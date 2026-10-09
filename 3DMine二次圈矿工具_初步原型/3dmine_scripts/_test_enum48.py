# -*- coding: utf-8 -*-
"""单点验证：enum=48 是否 AC1024 (R2010)。"""
import os
import win32com.client
import pythoncom

DXF = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\3940平台 1004二次圈矿矿块图_3块版_full.dxf"
P = r"D:\WK\N CRT\dwg_save_test3\e48.dwg"
os.makedirs(os.path.dirname(P), exist_ok=True)
if os.path.exists(P):
    os.remove(P)

def dwg_version(p):
    with open(p, "rb") as fp:
        return fp.read(6).decode("ascii", errors="ignore")

pythoncom.CoInitialize()
acad = win32com.client.Dispatch("AutoCAD.Application")
try:
    acad.Visible = False
except Exception:
    pass
doc = acad.Documents.Open(DXF, True)
for n in [48, 49, 50]:
    p = P.replace("48", str(n))
    try:
        doc.SaveAs(p, n)
        print(f"enum={n}: {dwg_version(p)}")
    except Exception as e:
        print(f"enum={n}: ERR {e}")
doc.Close(False)
try:
    acad.Quit()
except Exception:
    pass
pythoncom.CoUninitialize()
print("DONE")
