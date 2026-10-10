# -*- coding: utf-8 -*-
"""全自动一键出三件套：只给一个炮孔数据库 Excel。

用法: python run_auto.py <炮孔数据库.xls> [平台] [日期] [输出目录]
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from autoblock import auto_blocks                        # noqa: E402
from deliver import (write_3ds, write_dxf, write_report_png,   # noqa: E402
                     write_report_xlsx)
from oreblocks import load_holes_xls                     # noqa: E402

DENSITY = 2.7


def parse_tag(xls: Path):
    import re
    s = xls.name
    m = re.search(r"(\d{3,4})\s*平台", s)
    plat = m.group(1) if m else ""
    rest = s[m.end():] if m else s
    d = re.search(r"(\d{4})(?=\.\w+$|[^0-9]|$)", rest)
    return plat, (d.group(1) if d else "")


def main() -> None:
    xls = Path(sys.argv[1])
    plat = sys.argv[2] if len(sys.argv) > 2 else ""
    date = sys.argv[3] if len(sys.argv) > 3 else ""
    if not plat or not date:
        p, d = parse_tag(xls)
        plat, date = plat or p, date or d
    out_dir = Path(sys.argv[4]) if len(sys.argv) > 4 else \
        xls.parent / ("二次圈矿成果_%s_%s" % (plat or "?", date or "?"))
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {"platform": plat or "?", "date": date or "?", "density": DENSITY}

    holes = load_holes_xls(xls)
    print("数据库: %s\n炮孔 %d 个" % (xls, len(holes)))
    blocks, pending = auto_blocks(holes, DENSITY)
    print("\n自动圈连得到 %d 个矿块：" % len(blocks))
    for b in blocks:
        print("   %d 号 %s  %10.3f m3  %10.3f t  %.3f g/t  %.3f 百克  (%s)"
              % (b.no, b.label, b.volume_m3, b.tonnage_t, b.grade, b.metal_hg,
                 "、".join(h.short for h in b.holes)))
    tv = sum(b.volume_m3 for b in blocks)
    tt = sum(b.tonnage_t for b in blocks)
    tm = sum(b.metal_hg for b in blocks)
    print("合计 %.3f m3 / %.3f t / %.3f 百克" % (tv, tt, tm))
    if pending:
        print("\n未圈闭区域（孤立有品位孔，缺工程，待取样验证后再进行施工）：")
        for lid, g in pending:
            print("   %s  %s" % (lid, "、".join(h.short for h in g)))

    tag = "%s平台 %s" % (meta["platform"], meta["date"])
    holes_all = list(holes.values())
    xlsx = out_dir / ("%s炮孔数据报告.xlsx" % tag)
    png = out_dir / ("%s炮孔数据报告.png" % tag)
    dxf = out_dir / ("%s二次圈矿矿块图.dxf" % tag)
    tds = out_dir / ("%s矿块边界线.3ds" % tag)
    write_report_xlsx(blocks, meta, xlsx, holes_all)
    png_used, pw, ph = write_report_png(blocks, meta, holes_all, png)
    cells_dummy = [c for b in blocks for c in b.cells]
    write_dxf(blocks, holes_all, cells_dummy, meta, dxf,
              report_png=png_used, report_px=(pw, ph))
    write_3ds(blocks, meta, tds)
    print("\n完成 ->", out_dir)


if __name__ == "__main__":
    main()
