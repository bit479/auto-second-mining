# -*- coding: utf-8 -*-
"""诊断 1008 #2 L1 块品位异常的来源：重建单元，逐孔打印与块多边形的交集面积。"""
import sys, json, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
from shapely.ops import unary_union

import prep_generic as pg

xls = Path(r"D:\WK\N CRT\Test\1、3940平台 炮孔数据库1008.xls")
data = pg.read_db(xls)
print("columns:", list(data.columns))
print("rows:", len(data))

comp = pg.prep_holes(data)
print("comp cols:", list(comp.columns))

x = comp["X"].to_numpy(float)
y = comp["Y"].to_numpy(float)
g = comp["GRADE"].to_numpy(float)
ids = list(comp["ID"])

cells = pg.build_voronoi_cells(x, y, g, ids)
print("cells:", len(cells))

# L1 孔（0.5-1.0）
l1 = [c for c in cells if 0.5 <= c.grade < 1.0]
print("L1 cells:", [(c.hole_id, round(c.grade,3)) for c in l1])
lo_poly = unary_union([c.polygon for c in l1])
print("lo_poly area:", lo_poly.area)

# 逐孔交集（全部 50 孔）
print("\n-- intersection with lo_poly --")
tot, wsum = 0.0, 0.0
for c in cells:
    inter = c.polygon.intersection(lo_poly).area
    if inter > 1e-6:
        tot += inter
        wsum += inter * c.grade
        print(f"{c.hole_id}: grade={c.grade:.4f} inter={inter:.1f} ({inter/lo_poly.area*100:.1f}%)")
print(f"TOT={tot:.1f} grade_w={wsum/tot:.4f}")
