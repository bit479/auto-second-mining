# -*- coding: utf-8 -*-
# 看 1004 + N CR 1018未闭合线 切出来的那个 5.85 m² 小块在哪、跟谁相邻。
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))
from shapely.geometry import LineString, Polygon, Point           # noqa: E402
from shapely.ops import split                                     # noqa: E402
from oreblocks import load_holes_xls                              # noqa: E402
import strip as S                                                 # noqa: E402

D = Path(r"C:\Users\Administrator\Desktop\N CR 1018")
holes = load_holes_xls(D / "1、3940平台 炮孔数据库1004.xls")
allh = list(holes.values())
lines = S.read_3ds_polylines(D / "N CR 1018未闭合线.3ds")


def gap(p):
    return ((p[0][0] - p[-1][0]) ** 2 + (p[0][1] - p[-1][1]) ** 2) ** 0.5


rings = [Polygon(p).buffer(0) for p in lines if gap(p) < 0.05]
opens = [p for p in lines if gap(p) >= 0.05]
ring = max(rings, key=lambda g: g.area)
parts = [ring]
for pts in opens:
    ln = LineString(S._extend_line_ends(pts, 12.0))
    nxt = []
    for part in parts:
        nxt += S.split_polygon(part, ln)
    parts = nxt
print("切出 %d 片：" % len(parts))
for i, g in enumerate(parts, 1):
    hs = [h.short for h in allh if g.buffer(1e-9).contains(Point(h.x, h.y))]
    print("  #%d 面积 %7.2f  bounds %s  孔 %s"
          % (i, g.area, [round(v, 1) for v in g.bounds], ",".join(hs) or "无"))
print("--- 彼此关系 ---")
for i, a in enumerate(parts):
    for j, b in enumerate(parts):
        if i >= j:
            continue
        d = a.distance(b)
        shared = a.boundary.intersection(b.boundary).length
        print("  #%d <-> #%d 距离 %.2f m，共边 %.2f m" % (i + 1, j + 1, d, shared))

# 顺便看：用户"闭合版"里，这块小片落在哪一块？
closed_file = D / "N CR 1018闭合线.3ds"
if closed_file.exists():
    cps = [Polygon(p).buffer(0) for p in S.read_3ds_polylines(closed_file)]
    sliver = min(parts, key=lambda g: g.area)
    rp = sliver.representative_point()
    print("\n小片代表点 (%.2f, %.2f)：用户闭合版里落在哪块？"
          % (rp.x, rp.y))
    for i, g in enumerate(cps, 1):
        if g.contains(rp) or g.buffer(0.05).contains(rp):
            print("  → 用户 #%d（面积 %.2f）" % (i, g.area))
    # 小片离最近矿孔
    near = min(allh, key=lambda h: (h.x - rp.x) ** 2 + (h.y - rp.y) ** 2)
    print("  小片代表点最近的孔：%s 品位 %.3f，距离 %.2f m"
          % (near.short, near.grade, ((near.x - rp.x) ** 2 + (near.y - rp.y) ** 2) ** 0.5))
