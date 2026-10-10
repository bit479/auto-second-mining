# -*- coding: utf-8 -*-
"""验证：把人工导出的 4 段线按点序直接拼成外围矿界，再用两条品位界限切块。

4 段（用户人工画的顺序）：
  左边界(已外推3m) -> 与综合图边界 -> 右边界(已外推3m) -> 连接辅助线中点形成右上边界
"""
from __future__ import annotations

from pathlib import Path

from shapely.geometry import LineString, Polygon
from shapely.ops import split as shp_split, unary_union

D = Path(r"C:\Users\Administrator\Desktop")
PARTS = ["左边界，已外推3m.3ds", "与综合图边界.3ds",
         "右边界，已外推3m.3ds", "连接辅助线中点形成右上边界.3ds"]


def read_points(p: Path):
    txt = p.read_bytes().decode("gbk", "replace")
    pts = []
    for line in txt.splitlines():
        s = line.strip()
        if not s:
            continue
        parts = [x.strip() for x in s.split(",")]
        if len(parts) >= 4 and parts[0] == "1":
            try:
                pts.append((float(parts[2]), float(parts[1])))   # X=E, Y=N
            except Exception:
                pass
    return pts


def build_ring():
    ring = []
    for n in PARTS:
        pts = read_points(D / n)
        if ring and pts:
            # 若与上一段末点重合则去掉重复点，保证首尾相接
            if abs(ring[-1][0] - pts[0][0]) < 1e-6 and abs(ring[-1][1] - pts[0][1]) < 1e-6:
                pts = pts[1:]
        ring += pts
        print("  %-28s %d 点  起(%.2f,%.2f) 末(%.2f,%.2f)"
              % (n, len(pts) + (1 if ring and pts else 0),
                 pts[0][0] if pts else 0, pts[0][1] if pts else 0,
                 pts[-1][0] if pts else 0, pts[-1][1] if pts else 0))
    return ring


def main() -> None:
    print("按人工顺序拼接 4 段线：")
    ring = build_ring()
    poly = Polygon(ring).buffer(0)
    print("\n拼接结果：顶点 %d，面积 %.3f m²（人工三块合计 344.969）"
          % (len(ring), poly.area))
    if poly.geom_type != "Polygon":
        print("  注意：不是单一多边形（%s）" % poly.geom_type)
    return poly


if __name__ == "__main__":
    main()
