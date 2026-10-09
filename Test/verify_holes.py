# -*- coding: utf-8 -*-
"""读 blocks.json + 源数据，核对每个矿块实际包含哪些炮孔（孔点在块内）。"""
import sys, json
sys.path.insert(0, r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型")
sys.path.insert(0, r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\src")
from shapely.geometry import Polygon, Point
from mdb_loader import load_xls_blast

js = sys.argv[1]
xls = sys.argv[2]
d = json.load(open(js, encoding="utf-8"))
c = load_xls_blast(xls)
holes = {r["Hole_ID"]: (r["X"], r["Y"], r["Grade"]) for _, r in c.iterrows()}

for b in d["blocks"]:
    rings = b["parts"]
    poly = None
    for part in rings:
        p = Polygon(part)
        poly = p if poly is None else poly.union(p)
    inside = []
    for hid, (x, y, g) in holes.items():
        if g >= 0.5 and Point(x, y).within(poly):
            inside.append((hid.split("-")[-1], g))
    inside.sort(key=lambda t: -t[1])
    ids = ", ".join(f"{i}({g:.2f})" for i, g in inside)
    print(f"#{b['no']} {b['grade_label']} 面积{b['area_m2']:.0f} 报告孔数{b['cell_count']} -> 实际孔点 {len(inside)} 个: {ids}")
