# -*- coding: utf-8 -*-
"""用 1008 真实数据自检计算核心（对照人工报告）。

用法: python check_1008.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from oreblocks import (attach_cells, build_blocks, load_holes_xls,  # noqa: E402
                       read_3dm)

XLS = Path(r"D:\WK\N CRT\北部山头3940平台2026\7、单日数据\北部山头3940平台-1008"
           r"\1、3940平台 炮孔数据库1008.xls")
TDM = Path(r"C:\Users\Administrator\Desktop\选择集对象.3dm")
DENSITY = 2.7

EXPECT = [
    ("0.500-1.000", 714.095, 1928.056, 0.680, 13.111, ["P14", "P23"]),
    ("0.500-1.000", 1327.522, 3584.311, 0.729, 26.134, ["P4", "P6", "P8", "P9"]),
    ("1.000-1.500", 1909.877, 5156.668, 1.204, 62.104,
     ["P1", "P12", "P2", "P3", "P5", "P7"]),
]


def main() -> None:
    holes = load_holes_xls(XLS)
    faces = read_3dm(TDM)
    cells = attach_cells(holes, faces)
    print("炮孔 %d 个；读到 3DMine 单元 %d 个" % (len(holes), len(cells)))
    blocks = build_blocks(cells)
    print("自动划分出 %d 个矿块\n" % len(blocks))

    print("%-4s %-13s %10s %10s %8s %8s  %s" %
          ("体号", "品位类型", "体积m3", "重量t", "品位", "金属量", "孔"))
    for b in blocks:
        b.compute(DENSITY)
        print("%-4d %-13s %10.3f %10.3f %8.3f %8.3f  %s"
              % (b.no, b.label, b.volume_m3, b.tonnage_t, b.grade, b.metal_hg,
                 "、".join(h.short for h in b.holes)))
    tv = sum(b.volume_m3 for b in blocks)
    tt = sum(b.tonnage_t for b in blocks)
    tm = sum(b.metal_hg for b in blocks)
    print("\n合计体积 %.3f 重量 %.3f 金属量 %.3f" % (tv, tt, tm))

    print("\n==== 与人工报告对比 ====")
    ok = True
    used = set()
    for label, ev, et, eg, em, eholes in EXPECT:
        match = None
        for b in blocks:
            if b.no in used:
                continue
            if set(h.short for h in b.holes) == set(eholes):
                match = b
                break
        if match is None:
            print("  未匹配到块: %s %s" % (label, eholes))
            ok = False
            continue
        used.add(match.no)
        dv, dt, dg, dm = (match.volume_m3 - ev, match.tonnage_t - et,
                          match.grade - eg, match.metal_hg - em)
        flag = "OK" if max(abs(dv), abs(dt), abs(dg), abs(dm)) < 0.01 else "差异"
        print("  %s 孔=%s  体积 %+.4f  重量 %+.4f  品位 %+.5f  金属量 %+.4f -> %s"
              % (label, "、".join(eholes), dv, dt, dg, dm, flag))
        if flag != "OK":
            ok = False
    print("\n结论:", "全部精确一致 ✓" if ok else "存在差异 ✗")


if __name__ == "__main__":
    main()
