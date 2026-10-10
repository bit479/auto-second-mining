# -*- coding: utf-8 -*-
"""用 3DMine 导出的 12 个真实 Voronoi 单元做标定，寻找裁剪边界规则。

已知：
  - 3DMine 单元面积（来自 选择集对象.3dm）：P14 37.5495, P23 27.3682, P4 25.8461,
    P6 35.1237, P8 28.9165, P9 25.3041, P1 25.3403, P12 31.6778, P2 20.7562,
    P3 22.2553, P5 29.3273, P7 35.4956
  - 待定：裁剪边界（爆区边界）

做法：对若干候选边界，计算 Voronoi 单元 ∩ 边界 的面积，与目标比对。
"""
from __future__ import annotations

import xlrd
import numpy as np
from shapely.geometry import MultiPoint, Point, Polygon, box
from scipy.spatial import Voronoi

XLS = (r"D:\WK\N CRT\北部山头3940平台2026\7、单日数据\北部山头3940平台-1008"
       r"\1、3940平台 炮孔数据库1008.xls")

TARGET = {
    "P14": 37.5495, "P23": 27.3682, "P4": 25.8461, "P6": 35.1237,
    "P8": 28.9165, "P9": 25.3041, "P1": 25.3403, "P12": 31.6778,
    "P2": 20.7562, "P3": 22.2553, "P5": 29.3273, "P7": 35.4956,
}


def load():
    wb = xlrd.open_workbook(XLS)
    loc = wb.sheet_by_name("定位表")
    holes = {}
    for r in range(1, loc.nrows):
        hid = str(loc.cell_value(r, 0)).strip()
        holes[hid.split("-")[-1]] = (loc.cell_value(r, 1), loc.cell_value(r, 2))
    return holes


def cells(holes):
    keys = sorted(holes)
    xy = np.array([holes[k] for k in keys], float)
    far = np.array([[-9e4, -9e4], [9e4, -9e4], [-9e4, 9e4], [9e4, 9e4]], float)
    vor = Voronoi(np.vstack([xy, far]))
    out = {}
    for i, k in enumerate(keys):
        reg = vor.regions[vor.point_region[i]]
        out[k] = Polygon(vor.vertices[reg]).buffer(0) if reg and -1 not in reg else None
    return out


def main() -> None:
    holes = load()
    c = cells(holes)
    allxy = np.array(list(holes.values()), float)
    hull = MultiPoint(allxy).convex_hull
    print("50 孔凸包面积 %.3f" % hull.area)
    print()
    print("%-6s %9s | %s" % ("k(m)", "误差和", "各单元面积（前6）"))
    best = None
    for k in [x / 10.0 for x in range(0, 121)]:
        zone = hull if k == 0 else hull.buffer(k, join_style="mitre")
        err = 0.0
        got = []
        for name, t in TARGET.items():
            poly = c[name].intersection(zone)
            a = poly.area
            err += abs(a - t)
            got.append(a)
        if best is None or err < best[1]:
            best = (k, err, got[:6])
        if abs(k * 10 - round(k * 10)) < 1e-9 and int(k * 10) % 5 == 0:
            print("%-6.1f %9.3f | %s" % (k, err, ["%.3f" % v for v in got[:6]]))
    print()
    print("最佳 k = %.2f m, 误差和 = %.4f m2" % (best[0], best[1]))
    zone = hull if best[0] == 0 else hull.buffer(best[0], join_style="mitre")
    for name, t in TARGET.items():
        a = c[name].intersection(zone).area
        print("   %-5s 我的=%9.4f  3DMine=%9.4f  差=%+.4f" % (name, a, t, a - t))


if __name__ == "__main__":
    main()
