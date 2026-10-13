# -*- coding: utf-8 -*-
"""逐条边分析 3DMine 单元：判断每条边是哪两个孔的中垂线，还是"边界边"。"""
from __future__ import annotations

import math
import re
import struct
from pathlib import Path

import xlrd
import numpy as np

TDM3 = Path(r"C:\Users\Administrator\Desktop\选择集对象.3dm")
XLS = (r"D:\WK\N CRT\北部山头3940平台2026\7、单日数据\北部山头3940平台-1008"
       r"\1、3940平台 炮孔数据库1008.xls")
ATTR = re.compile(r"Au,([\d.]+),gradeLenght,([\d.]+),holepos,([\d.]+) ([\d.]+) ([\d.]+)")


def dbl(blob):
    vals, seen = [], set()
    for off in range(len(blob) - 8):
        v = struct.unpack_from("<d", blob, off)[0]
        if not any(lo <= v <= hi for lo, hi in
                   ((469000, 471000), (4349000, 4351000), (3900, 3960))):
            continue
        k = round(v, 6)
        if k in seen:
            continue
        seen.add(k)
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
        # 去重保序
        uniq = []
        for p in pts:
            if not uniq or math.dist(p, uniq[-1]) > 1e-6:
                uniq.append(p)
        if uniq and math.dist(uniq[0], uniq[-1]) < 1e-6:
            uniq = uniq[:-1]
        out.append((hp, uniq))
    return out


def main() -> None:
    wb = xlrd.open_workbook(XLS)
    loc = wb.sheet_by_name("定位表")
    holes = {}
    for r in range(1, loc.nrows):
        hid = str(loc.cell_value(r, 0)).strip().split("-")[-1]
        holes[hid] = (loc.cell_value(r, 1), loc.cell_value(r, 2))

    for hp, pts in faces():
        best, bd = None, 1e9
        for k, v in holes.items():
            d = math.dist(hp, v)
            if d < bd:
                bd, best = d, k
        print("=" * 72)
        print("单元 孔=%s holepos=(%.3f,%.3f) 顶点数=%d 面积=%.4f"
              % (best, hp[0], hp[1], len(pts), _area(pts)))
        a = np.array(holes[best])
        for i in range(len(pts)):
            p1 = np.array(pts[i])
            p2 = np.array(pts[(i + 1) % len(pts)])
            mid = (p1 + p2) / 2.0
            best_h, best_d = None, 1e9
            for k, v in holes.items():
                if k == best:
                    continue
                b = np.array(v)
                # 该边是否等于 a,b 的中垂线：中点到 a、b 距离相等
                d = abs(np.linalg.norm(mid - a) - np.linalg.norm(mid - b))
                if d < best_d:
                    best_d, best_h = d, k
            # 边长
            L = float(np.linalg.norm(p2 - p1))
            tag = "中垂线<- %s" % best_h if best_d < 0.02 else "**边界边**(最近差 %.3f <- %s)" % (best_d, best_h)
            print("   边%d 长%7.3f 中点(%.2f,%.2f)  %s" % (i + 1, L, mid[0], mid[1], tag))


def _area(pts):
    s = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


if __name__ == "__main__":
    main()
