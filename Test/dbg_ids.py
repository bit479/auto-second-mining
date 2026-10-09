# -*- coding: utf-8 -*-
"""debug：用与 prep_generic 相同逻辑跑 1004，输出每块最终包含的孔ID"""
import sys, json
sys.path.insert(0, r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型")
sys.path.insert(0, r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\src")
import numpy as np
import pandas as pd
from scipy.spatial import Delaunay
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union
from mdb_loader import load_xls_blast
from voronoi import GRADE_LEVELS, OreBlock, build_voronoi_cells

ROOT = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型"
BLOCK_ORDER = ["L4", "L3", "L2", "L1"]
MERGE_DIST = 25.0
MIN_BLOCK_AREA = 80.0
ALPHA_SHAPE_M = 4.0
EDGE_BUFFER_M = 2.5

def square_around(pt, half):
    x, y = float(pt[0]), float(pt[1])
    return Polygon([(x - half, y - half), (x + half, y - half),
                    (x + half, y + half), (x - half, y + half)])

def alpha_shape_poly(xy, alpha):
    if len(xy) < 3:
        return None
    try:
        tri = Delaunay(xy)
    except Exception:
        return None
    polys = []
    for s in tri.simplices:
        p = xy[s]
        d = [float(np.hypot(*(p[(i + 1) % 3] - p[i]))) for i in range(3)]
        if max(d) < 2.0 * alpha:
            polys.append(Polygon(p))
    if not polys:
        return None
    return unary_union(polys)

def auto_alpha(xy):
    try:
        tri = Delaunay(xy)
    except Exception:
        return ALPHA_SHAPE_M
    ds = []
    for s in tri.simplices:
        p = xy[s]
        ds += [float(np.hypot(*(p[(i + 1) % 3] - p[i]))) for i in range(3)]
    med = float(np.median(ds)) if ds else ALPHA_SHAPE_M
    return max(3.0, min(12.0, med * 0.75))

def outline_for(xy):
    if len(xy) == 0:
        return None
    if len(xy) == 1:
        return square_around(xy[0], EDGE_BUFFER_M + 1.0)
    a = auto_alpha(xy)
    body = alpha_shape_poly(xy, a)
    polys = []
    if body is not None and body.area > 1e-6:
        polys.append(body.buffer(EDGE_BUFFER_M, join_style="mitre", cap_style="square", mitre_limit=3.0))
    for p in xy:
        if body is None or not body.contains(Point(*p)):
            polys.append(square_around(p, EDGE_BUFFER_M + 1.0))
    if not polys:
        return None
    return unary_union(polys).buffer(0)

c = load_xls_blast(r"D:\WK\N CRT\北部山头3940平台2026\7、单日数据\北部山头3940平台-1004\1、3940平台 炮孔数据库1004.xls")
comp = c
ore = comp[comp["Grade"] >= 0.5].reset_index(drop=True)
CA = build_voronoi_cells(ore["X"].to_numpy(float), ore["Y"].to_numpy(float),
                         ore["Grade"].to_numpy(float), ore["Hole_ID"].tolist())
H, D = 10.0, 2.7

# 每档 alpha shape 块
bl_by_level = {}
for lv in GRADE_LEVELS:
    sel = ore[(ore["Grade"] >= lv["lo"]) & (ore["Grade"] < lv["hi"])]
    pts = np.column_stack([sel["X"].to_numpy(float), sel["Y"].to_numpy(float)])
    ids = sel["Hole_ID"].tolist()
    if len(pts) == 0:
        bl_by_level[lv["id"]] = []
        continue
    poly = outline_for(pts)
    if poly is None:
        bl_by_level[lv["id"]] = []
        continue
    parts = list(poly.geoms) if poly.geom_type == "MultiPolygon" else [poly]
    bl = []
    for part in parts:
        if part.area < 15:
            continue
        n_in = sum(1 for cid in ids if Point(*ore[ore["Hole_ID"] == cid][["X", "Y"]].values[0]).within(part))
        bl.append({"ids": [i for i in ids if Point(*ore[ore["Hole_ID"] == i][["X", "Y"]].values[0]).within(part)],
                   "poly": part.buffer(0)})
    bl_by_level[lv["id"]] = bl
    print(f"[{lv['id']}] {len(bl)} 块:", [f"{len(b['ids'])}孔" for b in bl])

for lv in BLOCK_ORDER:
    for i, b in enumerate(bl_by_level.get(lv, []), 1):
        print(f"  初始 {lv}#{i}: {[x.split('-')[-1] for x in b['ids']]} 面积{b['poly'].area:.0f}")
