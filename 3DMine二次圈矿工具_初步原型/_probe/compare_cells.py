# -*- coding: utf-8 -*-
"""把 3DMine 导出的真实单元（.3dm）与我用 50 孔 Voronoi 算的单元做几何比对。"""
from __future__ import annotations

import re
import struct
import xlrd
import numpy as np
from pathlib import Path
from shapely.geometry import Polygon
from scipy.spatial import Voronoi

TDM3 = Path(r"C:\Users\Administrator\Desktop\选择集对象.3dm")
XLS = (r"D:\WK\N CRT\北部山头3940平台2026\7、单日数据\北部山头3940平台-1008"
       r"\1、3940平台 炮孔数据库1008.xls")
ATTR = re.compile(r"Au,([\d.]+),gradeLenght,([\d.]+),holepos,([\d.]+) ([\d.]+) ([\d.]+)")


def dbl(blob):
    vals = []
    seen = set()
    for off in range(len(blob) - 8):
        v = struct.unpack_from("<d", blob, off)[0]
        if not any(lo <= v <= hi for lo, hi in
                   ((469000, 471000), (4349000, 4351000), (3900, 3960))):
            continue
        key = round(v, 6)
        if key in seen:
            continue
        seen.add(key)
        vals.append((off, v))
    vals.sort()
    return vals


def faces():
    data = TDM3.read_bytes()
    idx = [m.start() for m in re.finditer(b"AcDbFace", data)]
    txt = data.decode("latin-1")
    attrs = [(m.start(), m.group(3), m.group(4)) for m in ATTR.finditer(txt)]
    out = []
    for k, start in enumerate(idx):
        end = idx[k + 1] if k + 1 < len(idx) else len(data)
        blob = data[start:end]
        a = [x for x in attrs if start <= x[0] < end]
        if not a:
            continue
        hp = (float(a[0][1]), float(a[0][2]))
        ds = dbl(blob)
        pts = []
        for i, (_, v) in enumerate(ds):
            if 469000 <= v <= 471000 and i + 1 < len(ds):
                n = ds[i + 1][1]
                if 4349000 <= n <= 4351000 and abs(ds[i + 1][0] - ds[i][0]) <= 9:
                    pts.append((v, n))
        out.append((hp, Polygon(pts).buffer(0)))
    return out


def main() -> None:
    wb = xlrd.open_workbook(XLS)
    loc = wb.sheet_by_name("定位表")
    holes = {}
    for r in range(1, loc.nrows):
        hid = str(loc.cell_value(r, 0)).strip().split("-")[-1]
        holes[hid] = (loc.cell_value(r, 1), loc.cell_value(r, 2))
    keys = sorted(holes)
    xy = np.array([holes[k] for k in keys], float)
    far = np.array([[-9e4, -9e4], [9e4, -9e4], [-9e4, 9e4], [9e4, 9e4]], float)
    vor = Voronoi(np.vstack([xy, far]))
    mine = {}
    for i, k in enumerate(keys):
        reg = vor.regions[vor.point_region[i]]
        mine[k] = Polygon(vor.vertices[reg]).buffer(0) if reg and -1 not in reg else None

    print("%-6s %9s %9s %9s %8s %10s" % ("孔", "3DMine", "我的", "我∩他", "他/我", "IoU"))
    for (hx, hy), poly in faces():
        # 找最近的孔
        best, bd = None, 1e9
        for k in keys:
            d = (holes[k][0] - hx) ** 2 + (holes[k][1] - hy) ** 2
            if d < bd:
                bd, best = d, k
        m = mine[best]
        inter = poly.intersection(m).area
        uni = poly.union(m).area
        print("%-6s %9.4f %9.4f %9.4f %8.4f %10.4f"
              % (best, poly.area, m.area, inter, poly.area / m.area, inter / uni))


if __name__ == "__main__":
    main()
