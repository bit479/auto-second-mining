# -*- coding: utf-8 -*-
"""遍历 SaveAs 枚举 40-130，找 AC1024(R2010)。"""
import os
import win32com.client
import pythoncom

DXF = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\3940平台 1004二次圈矿矿块图_3块版_full.dxf"
TMP = r"D:\WK\N CRT\dwg_save_test3"
os.makedirs(TMP, exist_ok=True)

def dwg_version(p):
    try:
        with open(p, "rb") as fp:
            head = fp.read(6)
        return head.decode("ascii", errors="ignore")
    except Exception:
        return None

pythoncom.CoInitialize()
acad = win32com.client.Dispatch("AutoCAD.Application")
try:
    acad.Visible = False
except Exception:
    pass
doc = acad.Documents.Open(DXF, True)
hits = []
for n in range(40, 131):
    p = os.path.join(TMP, f"e{n}.dwg")
    if os.path.exists(p):
        os.remove(p)
    try:
        doc.SaveAs(p, n)
        v = dwg_version(p)
        print(f"enum={n}: {v if v else 'nofile'}")
        if v == "AC1024":
            hits.append(n)
    except Exception:
        print(f"enum={n}: ERR")
doc.Close(False)
try:
    acad.Quit()
except Exception:
    pass
pythoncom.CoUninitialize()
print("AC1024 hits:", hits)
print("DONE")
