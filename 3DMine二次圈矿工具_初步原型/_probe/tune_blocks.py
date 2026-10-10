# -*- coding: utf-8 -*-
"""用人工图当标准，标定"分块定档"的两个参数：最小块段面积、碎片并入规则。

评分：对同一天，看任意两个矿孔"是否在同一块"——人工图的结果和自动结果的一致率。
用法: python tune_blocks.py
"""
from __future__ import annotations

import json
import sys
from itertools import combinations
from pathlib import Path

from shapely.geometry import Point, Polygon

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))

from oreblocks import load_holes_xls                       # noqa: E402
from strip import zone_outline, average_blocks             # noqa: E402
from run_strip import pick_zone                            # noqa: E402
from composite import load_composite_blocks                # noqa: E402

DAY = ROOT.parent / "北部山头3940平台2026"
DATA = DAY / "7、单日数据"
PROBE = ROOT / "_probe"
SKIP = {"爆区方格网", "钻孔", "点", "线条", "孔口文字"}
DATES = ["0915", "0922", "1003", "1004", "1008"]


def manual_group(date, allh):
    j = json.loads((PROBE / ("manual_%s_c.json" % date)).read_text(encoding="utf-8"))
    blocks = []
    for p in j["polylines"]:
        if p["layer"] in SKIP or len(p["pts"]) < 3:
            continue
        poly = Polygon(p["pts"]).buffer(0)
        if poly.area >= 5.0:
            blocks.append(poly.buffer(0.3))
    gp = {}
    for h in allh:
        if h.grade < 0.5:
            continue
        for k, poly in enumerate(blocks):
            if poly.contains(Point(h.x, h.y)):
                gp[h.hid] = k
                break
    return gp, blocks


def agree(gp, blocks_hids):
    """blocks_hids: list[set(hid)]；返回同块/不同块的一致率。"""
    auto = {}
    for k, s in enumerate(blocks_hids):
        for hid in s:
            auto[hid] = k
    keys = [h for h in gp if h in auto]
    if len(keys) < 2:
        return None
    ok = tot = 0
    for a, b in combinations(keys, 2):
        tot += 1
        ok += int((gp[a] == gp[b]) == (auto[a] == auto[b]))
    return ok / tot


def main() -> None:
    comp = load_composite_blocks(DAY / "5、 北部山头3940平台二次圈矿矿块图-2026综合.dwg")
    cache = {}
    for d in DATES:
        xls = sorted((DATA / ("北部山头3940平台-%s" % d)).glob("1、*.xls"))[0]
        holes = load_holes_xls(xls)
        allh = list(holes.values())
        ore, _ = pick_zone(holes)
        ring = zone_outline(ore, allh, 3.0, comp_blocks=comp, blast=d)
        gp, mb = manual_group(d, allh)
        cache[d] = (ore, ring, gp, len(mb))
    print("%-8s %-8s %-6s %s" % ("最小块段", "并入规则", "平均一致率", "逐日"))
    best = None
    for frag in (0, 20, 25, 40, 50, 60, 80, 100, 120):
        for target in ("avg", "shared"):
            rates = []
            detail = []
            for d in DATES:
                ore, ring, gp, nm = cache[d]
                if len(ore) < 2:
                    continue
                blocks = average_blocks(ore, ring, 2.7, frag, target)
                r = agree(gp, [set(h.hid for h in b.holes) for b in blocks])
                if r is None:
                    continue
                rates.append(r)
                detail.append("%s %.2f(%d块/人工%d)" % (d, r, len(blocks), nm))
            if not rates:
                continue
            m = sum(rates) / len(rates)
            print("%-8s %-8s %8.3f   %s" % (frag, target, m, "  ".join(detail)))
            if best is None or m > best[0]:
                best = (m, frag, target)
    print("\n最佳: 最小块段=%s m²  并入规则=%s  一致率=%.3f" % (best[1], best[2], best[0]))


if __name__ == "__main__":
    main()
