# -*- coding: utf-8 -*-
"""读人工 DXF 炮孔 hatch 边界尺寸（vertices 直接读）。"""
import ezdxf

DXF = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\manual_1004.dxf"
doc = ezdxf.readfile(DXF)
msp = doc.modelspace()

n = 0
for e in msp:
    if e.dxftype() != "HATCH":
        continue
    n += 1
    for bp in e.paths:
        try:
            if hasattr(bp, "vertices"):
                pts = list(bp.vertices)
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                print(f"hatch{n} color={e.dxf.color} npts={len(pts)} "
                      f"w={max(xs)-min(xs):.4f} h={max(ys)-min(ys):.4f} "
                      f"cx={(max(xs)+min(xs))/2:.1f} cy={(max(ys)+min(ys))/2:.1f}")
                break
        except Exception as ex:
            print(f"hatch{n} err: {ex}")
