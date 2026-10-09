# -*- coding: utf-8 -*-
"""检查 v4 DXF：引线方向、品位小字、矿块标注起点。"""
import ezdxf
import math

DXF = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\3940平台 1004二次圈矿矿块图_3块版_full.dxf"
doc = ezdxf.readfile(DXF)
msp = doc.modelspace()

# 1) 钻孔层 LINE：区分十字臂(水平/垂直)和引线(斜)
holes_lines = [e for e in msp if e.dxftype() == "LINE" and e.dxf.layer == "钻孔"]
h_count = v_count = diag = 0
samples = []
for e in holes_lines:
    x1, y1 = e.dxf.start.x, e.dxf.start.y
    x2, y2 = e.dxf.end.x, e.dxf.end.y
    dx, dy = x2 - x1, y2 - y1
    if abs(dx) > 1e-6 and abs(dy) < 1e-6:
        h_count += 1
    elif abs(dy) > 1e-6 and abs(dx) < 1e-6:
        v_count += 1
    else:
        diag += 1
        if len(samples) < 5:
            samples.append(((x1, y1), (x2, y2), round(dx, 2), round(dy, 2)))
print(f"钻孔层 LINE 共 {len(holes_lines)}: 水平 {h_count} / 垂直 {v_count} / 斜线 {diag}")
print("斜线样例:", samples)

# 2) 品位小字
small = [e for e in msp if e.dxftype() == "TEXT" and abs(e.dxf.height - 0.2) < 0.01]
print(f"\n品位小字(h=0.2): {len(small)} 个")
print("样例:", [(e.dxf.text, e.dxf.color, (round(e.dxf.insert.x, 2), round(e.dxf.insert.y, 2))) for e in small[:4]])

# 3) 矿块号引线（线条层 LINE）
leads = [e for e in msp if e.dxftype() == "LINE" and e.dxf.layer == "线条"]
print(f"\n矿块号引线: {len(leads)} 条")
for e in leads:
    print(f"  ({e.dxf.start.x:.2f},{e.dxf.start.y:.2f}) -> ({e.dxf.end.x:.2f},{e.dxf.end.y:.2f})")

# 4) 矿块边界范围（对照引线起点是否在各自矿块内）
polys = {}
for e in msp:
    if e.dxftype() == "LWPOLYLINE" and e.dxf.layer in ("1.500-3.000", "0.500-1.000"):
        pts = list(e.get_points())
        polys.setdefault(e.dxf.layer, []).append(pts)
for layer, rings in polys.items():
    for i, ring in enumerate(rings):
        xs = [p[0] for p in ring]
        ys = [p[1] for p in ring]
        print(f"  {layer} 环{i}: x[{min(xs):.1f},{max(xs):.1f}] y[{min(ys):.1f},{max(ys):.1f}] {len(ring)}点")
