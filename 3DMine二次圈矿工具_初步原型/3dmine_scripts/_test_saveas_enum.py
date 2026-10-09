# -*- coding: utf-8 -*-
"""测试 AutoCAD SaveAs 枚举值：找出 ac2010_dwg 的正确数值。"""
import os, sys
import win32com.client
import pythoncom

DXF = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\3940平台 1004二次圈矿矿块图_3块版_full.dxf"
TMP = r"D:\WK\N CRT\dwg_save_test"
os.makedirs(TMP, exist_ok=True)

pythoncom.CoInitialize()
acad = win32com.client.Dispatch("AutoCAD.Application")
try:
    acad.Visible = False
except Exception:
    pass
doc = acad.Documents.Open(DXF, True)
for n in [5, 7, 9, 11, 12, 13, 15, 61, 103]:
    p = os.path.join(TMP, f"t{n}.dwg")
    if os.path.exists(p):
        os.remove(p)
    try:
        doc.SaveAs(p, n)
        ok = os.path.exists(p)
        sz = os.path.getsize(p) if ok else 0
        print(f"enum={n}: saved={ok} size={sz}")
    except Exception as e:
        print(f"enum={n}: ERR {e}")
doc.Close(False)
try:
    acad.Quit()
except Exception:
    pass
pythoncom.CoUninitialize()
print("DONE")
