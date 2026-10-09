# -*- coding: utf-8 -*-
"""读人工 DXF：炮孔 hatch 直径（boundary path 范围）+ 网格线颜色分布。"""
import ezdxf
from collections import Counter

DXF = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\manual_1004.dxf"
doc = ezdxf.readfile(DXF)
msp = doc.modelspace()

print("=== HATCH（钻孔）尺寸 ===")
n = 0
for e in msp:
    if e.dxftype() != "HATCH":
        continue
    n += 1
    if n > 6:
        continue
    try:
        for bp in e.paths:
            if bp.path_type == "polyline":
                pts = list(bp.vertices)
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                print(f"  hatch{n} color={e.dxf.color} npts={len(pts)} "
                      f"w={max(xs)-min(xs):.3f} h={max(ys)-min(ys):.3f}")
    except Exception as ex:
        print(f"  hatch{n} err: {ex}")
print("hatch total:", n)

print("=== 爆区方格网 polyline 颜色分布 ===")
c = Counter()
samples = {}
for e in msp:
    if e.dxftype() in ("LWPOLYLINE", "POLYLINE") and e.dxf.layer == "爆区方格网":
        col = e.dxf.color
        c[col] += 1
        if col not in samples:
            pts = list(e.get_points())[:2]
            samples[col] = tuple(pts[0][:2]) if pts else None
print("color counts:", dict(c))
print("samples:", samples)

print("=== 0 层 polyline 颜色分布 ===")
c2 = Counter()
for e in msp:
    if e.dxftype() in ("LWPOLYLINE", "POLYLINE") and e.dxf.layer == "0":
        c2[e.dxf.color] += 1
print("layer0 counts:", dict(c2))

print("=== 品位文字颜色分布 ===")
c3 = Counter()
for e in msp:
    if e.dxftype() == "TEXT":
        c3[e.dxf.color] += 1
print("text colors:", dict(c3))
