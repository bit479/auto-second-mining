# -*- coding: utf-8 -*-
"""扫描生成的 DWG：实体结构验证。"""
import sys
import win32com.client
import pythoncom

DWG = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\3940平台 1004二次圈矿矿块图_3块版_2010.dwg"
OUT = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\gen_dwg_scan.txt"

pythoncom.CoInitialize()
acad = win32com.client.Dispatch("AutoCAD.Application")
try:
    acad.Visible = False
except Exception:
    pass
doc = acad.Documents.Open(DWG, True)
lines = []
lines.append(f"=== GEN DWG: {DWG} ===")
lines.append("=== Layers ===")
for ly in doc.Layers:
    lines.append(f"  {ly.Name}  color={ly.color}  on={ly.LayerOn}  locked={ly.Lock}")
lines.append("=== ModelSpace entities ===")
stats = {}
for ent in doc.ModelSpace:
    name = ent.ObjectName
    stats[name] = stats.get(name, 0) + 1
lines.append("=== counts ===")
for k, v in sorted(stats.items(), key=lambda x: -x[1]):
    lines.append(f"  {k}: {v}")
open(OUT, "w", encoding="utf-8").write("\n".join(lines))
print("\n".join(lines))
doc.Close(False)
try:
    acad.Quit()
except Exception:
    pass
pythoncom.CoUninitialize()
print("DONE")
