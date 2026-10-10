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
from strip import average_blocks, zone_outline                 # noqa: E402

DENSITY = 2.7


def parse_tag(name: str):
    m = re.search(r"(\d{3,4})\s*平台", name)
    plat = m.group(1) if m else ""
    rest = name[m.end():] if m else name
    d = re.search(r"(\d{4})(?=\.\w+$|[^0-9]|$)", rest)
    return plat, (d.group(1) if d else "")


def pick_zone(holes, gap=1.0, adjacent_max=8.8):
    """返回 (主矿化带矿孔, 待取样孤立孔组)。"""
    ore = [h for h in holes.values() if h.grade >= 0.5]
    kept = []
    for h in ore:
        if any(abs(h.x - k.x) < gap and abs(h.y - k.y) < gap for k in kept):
            continue
        kept.append(h)
    groups, used = [], [False] * len(kept)
    for i in range(len(kept)):
        if used[i]:
            continue
        g = [kept[i]]
        used[i] = True
        changed = True
        while changed:
            changed = False
            for j in range(len(kept)):
                if used[j]:
                    continue
                if any(math.hypot(a.x - kept[j].x, a.y - kept[j].y) <= adjacent_max
                       for a in g):
                    g.append(kept[j])
                    used[j] = True
                    changed = True
        groups.append(g)
    groups.sort(key=len, reverse=True)
    return (groups[0] if groups else []), groups[1:]


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

    holes = load_holes_xls(xls)
    allh = list(holes.values())
    ore, pending = pick_zone(holes)
    print("数据库: %s" % xls)
    print("炮孔 %d 个；矿孔 %d 个；主矿化带 %d 孔；孤立待取样 %d 组"
          % (len(allh), len([h for h in allh if h.grade >= 0.5]),
             len(ore), len(pending)))

    comp = []
    if comp_dwg:
        from composite import load_composite_blocks
        comp = load_composite_blocks(comp_dwg)
        print("综合图历史矿块 %d 个" % len(comp))

    outline = zone_outline(ore, allh, 3.0, comp_blocks=comp, blast=date)
    print("外围矿界面积 = %.3f m2" % (outline.area if outline else 0))
    # 分块定档（人工口径）：同档连通块 → <40 m² 的碎片并入邻块 → 按块平均品位定档
    blocks = average_blocks(ore, outline, DENSITY)
    # 只并"矿界南端真正接上的那一块"历史矿块（避免把综合图的大轮廓一起吞进来）
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
