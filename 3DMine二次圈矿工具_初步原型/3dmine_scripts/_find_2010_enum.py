# -*- coding: utf-8 -*-
"""遍历 SaveAs 枚举值，找 ac2010_dwg(AC1024) 的正确数值。"""
import os
import win32com.client
import pythoncom

DXF = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\3940平台 1004二次圈矿矿块图_3块版_full.dxf"
TMP = r"D:\WK\N CRT\dwg_save_test2"
os.makedirs(TMP, exist_ok=True)
for f in os.listdir(TMP):
    os.remove(os.path.join(TMP, f))

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
results = []
for n in range(0, 40):
    p = os.path.join(TMP, f"e{n}.dwg")
    try:
        doc.SaveAs(p, n)
        v = dwg_version(p)
        results.append((n, v if v else "nofile"))
        print(f"enum={n}: {v if v else 'nofile'}")
    except Exception as e:
        results.append((n, "ERR"))
        print(f"enum={n}: ERR")
doc.Close(False)
try:
    acad.Quit()
except Exception:
    pass
pythoncom.CoUninitialize()
# 找 AC1024
hits = [r for r in results if r[1] == "AC1024"]
print("AC1024 hits:", hits)
print("DONE")
