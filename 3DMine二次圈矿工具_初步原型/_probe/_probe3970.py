# -*- coding: utf-8 -*-
# 用 3970-1011 的人工 .3ds 试算：看我们的口径能不能复现用户报告里的数字。
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))
sys.path.insert(0, str(ROOT / "_probe"))
from shapely.geometry import Point, Polygon            # noqa: E402
from oreblocks import load_holes_xls                   # noqa: E402
from strip import _cells_within, read_3ds_polylines    # noqa: E402
import baseline as _bl                                 # noqa: E402

folder = _bl.blast_dir("3970", "1011")
print("数据目录:", folder)
holes = load_holes_xls(sorted(folder.glob("1、*.xls"))[0])
allh = list(holes.values())
print("炮孔 %d 个；品位分布 %s" % (len(allh), {
    b: sum(1 for h in allh if h.grade >= lo and (hi is None or h.grade < hi))
    for b, lo, hi in ((">=3", 3.0, None), ("1.5-3", 1.5, 3.0),
                      ("1-1.5", 1.0, 1.5), ("0.5-1", 0.5, 1.0), ("<0.5", 0.0, 0.5))}))


def stats(poly, local=False):
    """local=True 时只用"落在块内的孔"做 Voronoi（3DMine 分块算量就是这么做）。"""
    hs_in = [h for h in allh if poly.buffer(1e-9).contains(Point(h.x, h.y))]
    src = hs_in if (local and hs_in) else allh
    cells = _cells_within(src, poly)            # {hid: 裁剪到 poly 的单元多边形}
    byh = {h.hid: h for h in src}
    vol = sum(c.area * byh[k].grade_lenght for k, c in cells.items())
    wt = sum(c.area * byh[k].grade_lenght * (2.65 if byh[k].grade < 0.5 else 2.7)
             for k, c in cells.items())
    hs = hs_in
    lsum = sum(h.grade_lenght for h in hs)
    g = (sum(h.grade_lenght * h.grade_disp for h in hs) / lsum) if lsum else 0.0
    return poly.area, vol, wt, g, wt * g / 100.0, len(hs)


def dump_holes(poly, tag):
    hs = [h for h in allh if poly.buffer(1e-9).contains(Point(h.x, h.y))]
    print("   %s 块内孔 %d 个：" % (tag, len(hs)))
    for h in sorted(hs, key=lambda x: -x.grade):
        print("      %-24s 品位 %.4g  gradeLenght %.1f" % (h.short, h.grade, h.grade_lenght))


def territory_stats(poly):
    """另一种口径：块体积 = 块内孔在**全场 Voronoi** 里的领地面积（不裁到多边形）× 孔长。"""
    import numpy as np
    from scipy.spatial import Voronoi
    xy = np.array([(h.x, h.y) for h in allh], float)
    b = 1e5
    extra = np.array([[xy[:, 0].min() - b, xy[:, 1].min() - b],
                      [xy[:, 0].max() + b, xy[:, 1].min() - b],
                      [xy[:, 0].min() - b, xy[:, 1].max() + b],
                      [xy[:, 0].max() + b, xy[:, 1].max() + b]], float)
    vor = Voronoi(np.vstack([xy, extra]))
    hs = [h for h in allh if poly.buffer(1e-9).contains(Point(h.x, h.y))]
    tot_a = tot_v = 0.0
    for h in hs:
        i = allh.index(h)
        reg = vor.regions[vor.point_region[i]]
        if -1 in reg or not reg:
            continue
        p = Polygon(vor.vertices[reg])
        tot_a += p.area
        tot_v += p.area * h.grade_lenght
    return tot_a, tot_v


for name in ("选择集对象.3ds", "选择集对象分品位.3ds"):
    p = folder / name
    if not p.exists():
        continue
    polys = read_3ds_polylines(p)
    print("\n%s → %d 条折线" % (name, len(polys)))
    for i, pts in enumerate(polys, 1):
        poly = Polygon(pts)
        if not poly.is_valid:
            poly = poly.buffer(0)
        a2, v2 = territory_stats(poly)
        print("  第%d条 领地口径: 领地面积 %.1f m² / 体积 %.3f m³" % (i, a2, v2))
        for local in (False, True):
            a, v, w, g, m, n = stats(poly, local=local)
            print("  第%d条%s: 面积 %.1f m² / 体积 %.3f m³ / 重量 %.3f t / 品位 %.3f / "
                  "金属量 %.3f 百克 / 孔 %d"
                  % (i, "（块内孔 Voronoi）" if local else "（全场孔 Voronoi）", a, v, w, g, m, n))
