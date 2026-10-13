# -*- coding: utf-8 -*-
"""解析 3DMine 二进制工程文件(.3dm, 格式标识 3DMine_2011_Bin)。

用途：读出 AcDbFace 的属性串与顶点坐标（爆区voronoi图的面对象）。
用法: python parse_3dm.py <file.3dm>
"""
from __future__ import annotations

import re
import struct
import sys
from pathlib import Path


def tokens(data: bytes):
    """按 1 字节长度前缀提取 ASCII 串。"""
    out = []
    i = 0
    n = len(data)
    while i < n:
        L = data[i]
        if 2 <= L <= 60 and i + 1 + L <= n:
            chunk = data[i + 1:i + 1 + L]
            if all(32 <= b < 127 for b in chunk):
                out.append((i, chunk.decode("ascii")))
                i += 1 + L
                continue
        i += 1
    return out


def doubles(data: bytes):
    """扫描所有 8 字节偏移，挑出落在工程坐标范围内的 double。"""
    res = []
    for off in range(0, len(data) - 8):
        v = struct.unpack_from("<d", data, off)[0]
        if any(lo <= v <= hi for lo, hi in
               ((469000, 471000), (4349000, 4351000), (3900, 3960), (-2, 2))):
            res.append((off, v))
    return res


def main() -> None:
    p = Path(sys.argv[1])
    data = p.read_bytes()
    print("file:", p, "size:", len(data))
    print("\n== 长度前缀串 ==")
    for off, s in tokens(data):
        if len(s) >= 3:
            print("  @%-5d %s" % (off, s))
    print("\n== 可能的坐标 double ==")
    ds = doubles(data)
    # 去掉重叠的同一数值
    keep = []
    for off, v in ds:
        if keep and abs(keep[-1][0] - off) < 8 and abs(keep[-1][1] - v) < 1e-9:
            continue
        keep.append((off, v))
    for off, v in keep:
        print("  @%-5d %.6f" % (off, v))


if __name__ == "__main__":
    main()
