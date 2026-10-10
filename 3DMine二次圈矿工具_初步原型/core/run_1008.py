# -*- coding: utf-8 -*-
"""1008 三件套一键生成（A 方案）。

用法: python run_1008.py [输出目录]
输入: 炮孔数据库 xls + 3DMine 导出的选择集 .3dm
产出: <平台>平台 <日期>炮孔数据报告.xlsx / _二次圈矿矿块图.dxf / _矿块边界线.3ds
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from deliver import write_3ds, write_dxf, write_report_xlsx       # noqa: E402
from oreblocks import (attach_cells, build_blocks, load_holes_xls,  # noqa: E402
                       read_3dm)

PLATFORM = "3940"
DATE = "1008"
XLS = Path(r"D:\WK\N CRT\北部山头3940平台2026\7、单日数据\北部山头3940平台-1008"
           r"\1、3940平台 炮孔数据库1008.xls")
TDM = Path(r"C:\Users\Administrator\Desktop\选择集对象.3dm")
DENSITY = 2.7


def main() -> None:
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else \
        Path(r"D:\WK\N CRT\北部山头3940平台2026\7、单日数据\北部山头3940平台-1008"
             r"\二次圈矿成果_3940_1008_v2")
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {"platform": PLATFORM, "date": DATE, "bench_z": 3940.0, "density": DENSITY}

    holes = load_holes_xls(XLS)
    faces = read_3dm(TDM)
    cells = attach_cells(holes, faces)
    blocks = build_blocks(cells)
    for b in blocks:
        b.compute(DENSITY)

    print("矿块 %d 个：" % len(blocks))
    for b in blocks:
        print("   %d 号 %s  %10.3f m3  %10.3f t  %.3f g/t  %.3f 百克  (%s)"
              % (b.no, b.label, b.volume_m3, b.tonnage_t, b.grade, b.metal_hg,
                 "、".join(h.short for h in b.holes)))
    tv = sum(b.volume_m3 for b in blocks)
    tt = sum(b.tonnage_t for b in blocks)
    tm = sum(b.metal_hg for b in blocks)
    print("合计 %.3f m3 / %.3f t / %.3f 百克" % (tv, tt, tm))

    tag = "%s平台 %s" % (PLATFORM, DATE)
    xlsx = out_dir / ("%s炮孔数据报告.xlsx" % tag)
    dxf = out_dir / ("%s二次圈矿矿块图.dxf" % tag)
    tds = out_dir / ("%s矿块边界线.3ds" % tag)

    write_report_xlsx(blocks, meta, xlsx)
    print("[报告]", xlsx)
    write_dxf(blocks, list(holes.values()), cells, meta, dxf)
    print("[图件]", dxf)
    write_3ds(blocks, meta, tds)
    print("[3ds ]", tds)
    print("\n完成 ->", out_dir)


if __name__ == "__main__":
    main()
