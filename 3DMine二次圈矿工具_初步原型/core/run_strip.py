# -*- coding: utf-8 -*-
"""一键出三件套（条带法核心，人工流程复刻）。

用法:
  python run_strip.py <炮孔数据库.xls> [平台] [日期] [输出目录] [综合图.dwg]

流程：
  读库 - 矿孔分档 - 孤立单孔剔除（列待取样）- 走向中线分左右链
  - 链局部法向外推 3 m + 端部中点闭合 - 外围矿界
  - 外围矿界内按品位档分块（块内 Voronoi 算量）
  - 与综合图合并（<=4.5 m，重新编号）/ 空白区标注 - 报告 + 图 + .3ds
"""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from deliver import (write_3ds, write_dxf, write_report_png,   # noqa: E402
                     write_report_xlsx)
from oreblocks import load_holes_xls                           # noqa: E402
from pipeline import pick_zone, run_blast                      # noqa: E402
import params as _params                                       # noqa: E402

DENSITY = 2.7


def parse_tag(name: str):
    m = re.search(r"(\d{3,4})\s*平台", name)
    plat = m.group(1) if m else ""
    rest = name[m.end():] if m else name
    d = re.search(r"(\d{4})(?=\.\w+$|[^0-9]|$)", rest)
    return plat, (d.group(1) if d else "")


# 孤立孔判定：矿孔之间相距 ≤ 15 m 才算"连在同一条矿化带上"（用户 2026-10-10 定）。
# 依据：1004 人工图把北边间隔 10.6~13.9 m 的孔都连成一条；1008 的 P43 离主带 21.4 m 没圈。
# 现在这段逻辑在 pipeline.py，这里保留常量名给别的脚本引用。
ZONE_LINK_M = 15.0


def main() -> None:
    xls = Path(sys.argv[1])
    plat = sys.argv[2] if len(sys.argv) > 2 else ""
    date = sys.argv[3] if len(sys.argv) > 3 else ""
    if not plat or not date:
        p, d = parse_tag(xls.name)
        plat, date = plat or p, date or d
    out_dir = Path(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4] else \
        xls.parent / ("二次圈矿成果_%s_%s" % (plat or "?", date or "?"))
    out_dir.mkdir(parents=True, exist_ok=True)
    comp_dwg = sys.argv[5] if len(sys.argv) > 5 and sys.argv[5] else None
    meta = {"platform": plat or "?", "date": date or "?", "density": DENSITY}
    P = _params.for_blast(date)
    print("参数：外推 %.2f m / 连接半径 %.1f m / 最小块段 %.0f m² / 接综合图 %.1f m"
          % (P["extrude_m"], P["zone_link_m"], P["min_fragment_m2"], P["merge_gap_m"]))

    comp = []
    if comp_dwg:
        from composite import load_composite_blocks
        comp = load_composite_blocks(comp_dwg)
        print("综合图历史矿块 %d 个" % len(comp))

    holes = load_holes_xls(xls)
    allh = list(holes.values())
    res = run_blast(holes, allh, P, comp, blast=date)
    ore, pending, blocks = res["ore"], res["pending"], res["blocks"]
    print("数据库: %s" % xls)
    print("炮孔 %d 个；矿孔 %d 个；主矿化带 %d 孔；孤立待取样 %d 组"
          % (len(allh), len([h for h in allh if h.grade >= 0.5]),
             len(ore), len(pending)))

    for w in res["warn"]:
        print("   [矿界自检] %s（已自动修补成单块并把矿孔包进来，建议目视复核）" % w)
    for r in res["rings"]:
        print("外围矿界面积 = %.3f m2" % r.area)
    from strip import LAST_RING
    mb = LAST_RING.get("merged_block")
    cands = [c for c in comp if mb is not None and c[2] is mb] or None
    for b in blocks:
        print("   %d 号 %s  %9.3f m2  %10.3f m3  %10.3f t  %.3f g/t  %.3f 百克  (%s)"
              % (b.no, b.label, b.area_m2, b.volume_m3, b.tonnage_t, b.grade,
                 b.metal_hg, "、".join(h.short for h in b.holes)))
    tv = sum(b.volume_m3 for b in blocks)
    tt = sum(b.tonnage_t for b in blocks)
    tm = sum(b.metal_hg for b in blocks)
    print("合计 %.3f m3 / %.3f t / %.3f 百克" % (tv, tt, tm))
    if pending:
        print("未圈闭区域（缺工程，待取样验证后再进行施工）：")
        for g in pending:
            print("   " + "、".join(h.short for h in g))

    tag = "%s平台 %s" % (meta["platform"], meta["date"])
    xlsx = out_dir / ("%s炮孔数据报告.xlsx" % tag)
    png = out_dir / ("%s炮孔数据报告.png" % tag)
    dxf = out_dir / ("%s二次圈矿矿块图.dxf" % tag)
    tds = out_dir / ("%s矿块边界线.3ds" % tag)
    write_report_xlsx(blocks, meta, xlsx, allh)
    png_used, pw, ph = write_report_png(blocks, meta, allh, png)
    write_dxf(blocks, allh, [], meta, dxf,
              report_png=png_used, report_px=(pw, ph),
              pending=[("L1", g) for g in pending], composite_blocks=comp,
              merge_candidates=cands)
    write_3ds(blocks, meta, tds, composite_blocks=comp, merge_candidates=cands)
    print("完成 -> %s" % out_dir)


if __name__ == "__main__":
    main()
