# -*- coding: utf-8 -*-
# 看"未闭合线.3ds"里那几条开线相对闭合矿界的位置：端点离矿界多远、延伸后能不能切开矿界。
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))
import numpy as np                                        # noqa: E402
from shapely.geometry import LineString, Point, Polygon    # noqa: E402
from shapely.ops import split                             # noqa: E402
from strip import read_3ds_polylines                      # noqa: E402

D = Path(r"C:\Users\Administrator\Desktop\N CR 1018")
lines = read_3ds_polylines(D / "N CR 1018未闭合线.3ds")


def gap(pts):
    return math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1])


closed = [Polygon(p) for p in lines if gap(p) < 0.05]
opened = [p for p in lines if gap(p) >= 0.05]
ring = max(closed, key=lambda g: g.area).buffer(0)
print("闭合矿界：%d 条，最大面积 %.1f m2" % (len(closed), ring.area))
print("开口线：%d 条" % len(opened))


def extend(pts, ext=12.0):
    p = np.array(pts, float)
    d0 = p[0] - p[1]
    d1 = p[-1] - p[-2]
    n0 = np.linalg.norm(d0) or 1.0
    n1 = np.linalg.norm(d1) or 1.0
    return ([tuple(p[0] + d0 / n0 * ext)] + [tuple(x) for x in p] +
            [tuple(p[-1] + d1 / n1 * ext)])


for i, pts in enumerate(opened, 1):
    ln = LineString(pts)
    d_start = ring.exterior.distance(Point(pts[0]))
    d_end = ring.exterior.distance(Point(pts[-1]))
    print("")
    print("#%d: %d点 长%.1fm 端点到矿界 %.2f/%.2f m 整线在界内=%s"
          % (i, len(pts), ln.length, d_start, d_end, ring.buffer(0.01).contains(ln)))
    try:
        pieces = split(ring, LineString(extend(pts))).geoms
        print("    延伸12m后切出 %d 片: %s" % (len(pieces), [round(g.area, 1) for g in pieces]))
    except Exception as exc:
        print("    切不开: %s" % exc)
