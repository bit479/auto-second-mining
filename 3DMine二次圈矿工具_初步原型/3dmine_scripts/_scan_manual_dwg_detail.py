# -*- coding: utf-8 -*-
"""详细扫描人工 DWG：炮孔尺寸/颜色、品位文字属性、矿块号引出线、OLE 报告、网格线颜色。"""
import sys
import win32com.client
import pythoncom

DWG = r"D:\WK\N CRT\北部山头3940平台2026\7、单日数据\北部山头3940平台-1004\5、 北部山头3940平台二次圈矿矿块图1004.dwg"
OUT = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\manual_dwg_detail.txt"
ACAD_EXE = r"E:\gzRJ\CAD\AutoCAD 2023\acad.exe"

import os, subprocess, time
# 先杀残留，再启动
os.system("taskkill /IM acad.exe /F >nul 2>nul")
time.sleep(3)
subprocess.Popen([ACAD_EXE], cwd=os.path.dirname(ACAD_EXE))

pythoncom.CoInitialize()
acad = None
for i in range(90):
    try:
        acad = win32com.client.Dispatch("AutoCAD.Application")
        print(f"COM ready after {i*2}s")
        break
    except Exception:
        time.sleep(2)
if acad is None:
    print("FAIL: AutoCAD COM not ready")
    raise SystemExit(1)
try:
    acad.Visible = False
except Exception:
    pass
doc = acad.Documents.Open(DWG, True)
lines = []
lines.append("=== 文字样式 ===")
for st in doc.TextStyles:
    try:
        lines.append(f"  {st.Name} font={st.FontFile} bigfont={st.BigFontFile} height={st.Height} width={st.WidthFactor}")
    except Exception as e:
        lines.append(f"  {st.Name}: err {e}")

lines.append("=== 实体抽样（每类取若干） ===")
n = 0
for ent in doc.ModelSpace:
    name = ent.ObjectName
    try:
        if name in ("AcDbText", "AcDbMText"):
            if n > 12:
                continue
            n += 1
            st = ent.TextString[:30].replace("\n", "|")
            lines.append(f"[{name}] layer={ent.Layer} color={getattr(ent,'TrueColor','?')} txt='{st}' "
                         f"pos=({ent.InsertionPoint[0]:.1f},{ent.InsertionPoint[1]:.1f}) "
                         f"h={ent.Height} style={ent.StyleName}")
        elif name == "AcDbHatch":
            if n > 8:
                continue
            n += 1
            try:
                bb = ent.GeometricExtents
                w = bb.MaxPoint[0] - bb.MinPoint[0]
                hgt = bb.MaxPoint[1] - bb.MinPoint[1]
                lines.append(f"[Hatch] layer={ent.Layer} pattern={ent.PatternName} "
                             f"extent w={w:.2f} h={hgt:.2f} center=({(bb.MinPoint[0]+bb.MaxPoint[0])/2:.1f},{(bb.MinPoint[1]+bb.MaxPoint[1])/2:.1f})")
            except Exception as e:
                lines.append(f"[Hatch] layer={ent.Layer} pattern={ent.PatternName} err={e}")
        elif name == "AcDbPolyline":
            if n > 10:
                continue
            n += 1
            try:
                bb = ent.GeometricExtents
                w = bb.MaxPoint[0] - bb.MinPoint[0]
                hgt = bb.MaxPoint[1] - bb.MinPoint[1]
                lines.append(f"[Polyline] layer={ent.Layer} color={ent.Color} closed={ent.Closed} "
                             f"extent w={w:.1f} h={hgt:.1f} pt0=({ent.Coordinates[0]:.1f},{ent.Coordinates[1]:.1f})")
            except Exception as e:
                lines.append(f"[Polyline] layer={ent.Layer} err={e}")
        elif name == "AcDbLine":
            if n > 6:
                continue
            n += 1
            lines.append(f"[Line] layer={ent.Layer} color={ent.Color} "
                         f"({ent.StartPoint[0]:.1f},{ent.StartPoint[1]:.1f})->({ent.EndPoint[0]:.1f},{ent.EndPoint[1]:.1f})")
        elif name == "AcDbOle2Frame":
            if n > 3:
                continue
            n += 1
            try:
                bb = ent.GeometricExtents
                w = bb.MaxPoint[0] - bb.MinPoint[0]
                hgt = bb.MaxPoint[1] - bb.MinPoint[1]
                lines.append(f"[Ole2Frame] layer={ent.Layer} extent w={w:.1f} h={hgt:.1f} "
                             f"pos=({bb.MinPoint[0]:.1f},{bb.MinPoint[1]:.1f})")
            except Exception as e:
                lines.append(f"[Ole2Frame] layer={ent.Layer} err={e}")
    except Exception as e:
        lines.append(f"  {name}: probe err {e}")

# 矿块号 MText 与附近 Line（引出线？）
lines.append("=== 矿块号 MText 与 3 条 Line ===")
for ent in doc.ModelSpace:
    if ent.ObjectName == "AcDbMText":
        try:
            lines.append(f"MText '{ent.TextString[:20]}' at ({ent.InsertionPoint[0]:.2f},{ent.InsertionPoint[1]:.2f})")
        except Exception:
            pass
    if ent.ObjectName == "AcDbLine":
        try:
            lines.append(f"Line ({ent.StartPoint[0]:.2f},{ent.StartPoint[1]:.2f})->({ent.EndPoint[0]:.2f},{ent.EndPoint[1]:.2f})")
        except Exception:
            pass

open(OUT, "w", encoding="utf-8").write("\n".join(lines))
print("\n".join(lines))
doc.Close(False)
pythoncom.CoUninitialize()
print("DONE")
