# -*- coding: utf-8 -*-
"""解析 3DMine 二进制 .3dm 里的 AcDbFace：属性串 + 顶/底面顶点，算每单元面积与体积。

用法: python parse_3dm_faces.py <file.3dm>
"""
from __future__ import annotations

import re
import struct
import sys
from pathlib import Path

from shapely.geometry import Polygon

ATTR = re.compile(r"Au,([\d.]+),gradeLenght,([\d.]+),holepos,([\d.]+) ([\d.]+) ([\d.]+)")


def strings_in(blob: bytes):
    out = []
    i = 0
    n = len(blob)
    while i < n:
        L = blob[i]
        if 2 <= L <= 90 and i + 1 + L <= n:
            chunk = blob[i + 1:i + 1 + L]
            if all(32 <= b < 127 for b in chunk):
                out.append(chunk.decode("ascii"))
                i += 1 + L
                continue
        i += 1
    return out


def doubles_in(blob: bytes):
    vals = []
    seen = set()
    for off in range(0, len(blob) - 8):
        v = struct.unpack_from("<d", blob, off)[0]
        if not any(lo <= v <= hi for lo, hi in
                   ((469000, 471000), (4349000, 4351000), (3900, 3960))):
            continue
        key = (round(v, 6))
        if key in seen:
            continue
        seen.add(key)
        vals.append((off, v))
    vals.sort()
    return vals


def main() -> None:
    p = Path(sys.argv[1])
    data = p.read_bytes()
    idx = [m.start() for m in re.finditer(b"AcDbFace", data)]
    print("face 数 =", len(idx))
    total = 0.0
    rows = []
    attrs = [(m.start(), m.group(1), m.group(2), m.group(3), m.group(4), m.group(5))
             for m in ATTR.finditer(data.decode("latin-1"))]
    print("属性串数 =", len(attrs))
    for k, start in enumerate(idx):
        end = idx[k + 1] if k + 1 < len(idx) else len(data)
        blob = data[start:end]
        strs = strings_in(blob)
        layer = next((s for s in strs if s in
                      ("0.500-1.000", "1.000-1.500", "1.500-3.000", "3.000-999.000")), "?")
        cand = [a for a in attrs if start <= a[0] < end]
        au = float(cand[0][1]) if cand else None
        lenght = float(cand[0][2]) if cand else None
        hp = (float(cand[0][3]), float(cand[0][4]), float(cand[0][5])) if cand else None

        ds = doubles_in(blob)
        zs = sorted({round(v, 3) for _, v in ds if 3900 <= v <= 3960})
        ztop = zs[-1] if zs else None
        pts = [(v, ds[i + 1][1]) for i, (_, v) in enumerate(ds)
               if 469000 <= v <= 471000 and i + 1 < len(ds)
               and 4349000 <= ds[i + 1][1] <= 4351000
               and abs(ds[i + 1][0] - ds[i][0]) <= 9]
        # 取 N 与 Z 配对：三元组顺序为 (E, N, Z) 时，E 后紧跟 N
        poly = Polygon(pts).buffer(0) if len(pts) >= 3 else None
        area = poly.area if poly else 0.0
        vol = area * (lenght or 0)
        total += vol
        rows.append((k + 1, layer, au, lenght, hp, len(pts), area, vol))

    print("%-3s %-13s %-6s %-9s %-30s %-5s %-12s %-12s" %
          ("#", "图层", "Au", "gradeLen", "holepos(E,N,Z)", "点数", "面积m2", "体积m3"))
    for r in rows:
        print("%-3d %-13s %-6s %-9s %-30s %-5d %-12.4f %-12.4f" %
              (r[0], r[1], r[2], r[3],
               "%.2f,%.2f,%.2f" % r[4] if r[4] else "-", r[5], r[6], r[7]))
    print("\n合计体积 = %.4f m3" % total)
    print("人工报告   714.095 + 1327.522 + 1909.877 = %.3f" % (714.095 + 1327.522 + 1909.877))


if __name__ == "__main__":
    main()
