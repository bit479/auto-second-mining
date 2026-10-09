# -*- coding: utf-8 -*-
"""用 AutoCAD COM 读取人工 DWG：枚举图层、实体类型、统计，理解人工图结构。"""
import sys
import win32com.client
import pythoncom

DWG = r"D:\WK\N CRT\北部山头3940平台2026\7、单日数据\北部山头3940平台-1004\5、 北部山头3940平台二次圈矿矿块图1004.dwg"
OUT = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\manual_dwg_scan.txt"

def main():
    pythoncom.CoInitialize()
    acad = win32com.client.Dispatch("AutoCAD.Application")
    try:
        acad.Visible = False
    except Exception:
        pass
    print("AutoCAD version:", acad.Version)
    doc = acad.Documents.Open(DWG, True)  # ReadOnly
    print("doc name:", doc.Name)
    lines = []
    lines.append(f"=== DWG: {DWG} ===")
    lines.append(f"AutoCAD version: {acad.Version}")
    lines.append("=== Layers ===")
    try:
        for ly in doc.Layers:
            lines.append(f"  {ly.Name}  color={ly.color}  on={ly.LayerOn}")
    except Exception as e:
        lines.append(f"  layer enum err: {e}")
    lines.append("=== ModelSpace entities ===")
    stats = {}
    for ent in doc.ModelSpace:
        name = ent.ObjectName
        stats[name] = stats.get(name, 0) + 1
        if stats[name] <= 3:
            try:
                if name in ("AcDbPolyline", "AcDbLwPolyline", "AcDb2dPolyline"):
                    pts = ent.Coordinates
                    n = len(pts) // 2
                    lines.append(f"  {name} layer={ent.Layer} pts={n} first=({pts[0]:.2f},{pts[1]:.2f})")
                elif name == "AcDbPoint":
                    p = ent.Coordinates
                    lines.append(f"  {name} layer={ent.Layer} pos=({p[0]:.2f},{p[1]:.2f})")
                elif name in ("AcDbText", "AcDbMText"):
                    lines.append(f"  {name} layer={ent.Layer} txt='{ent.TextString[:60]}' pos=({ent.InsertionPoint[0]:.2f},{ent.InsertionPoint[1]:.2f}) h={ent.Height}")
                elif name == "AcDbHatch":
                    lines.append(f"  {name} layer={ent.Layer} pattern={ent.PatternName}")
                elif name == "AcDbLine":
                    lines.append(f"  {name} layer={ent.Layer} start=({ent.StartPoint[0]:.2f},{ent.StartPoint[1]:.2f}) end=({ent.EndPoint[0]:.2f},{ent.EndPoint[1]:.2f})")
                else:
                    lines.append(f"  {name} layer={ent.Layer}")
            except Exception as e:
                lines.append(f"  {name} layer={ent.Layer} (detail err: {e})")
    lines.append("=== counts ===")
    for k, v in sorted(stats.items(), key=lambda x: -x[1]):
        lines.append(f"  {k}: {v}")
    open(OUT, "w", encoding="utf-8").write("\n".join(lines))
    print("\n".join(lines))
    doc.Close(False)
    acad.Quit()
    pythoncom.CoUninitialize()
    print("DONE")

if __name__ == "__main__":
    main()
