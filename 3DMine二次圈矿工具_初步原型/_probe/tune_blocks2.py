# -*- coding: utf-8 -*-
"""用 5 张人工图标定"最小块段面积"和"相邻块合并阈值"。

判据（不拍数值、只认数据）：
  ① 主判据：任意两个矿孔"是否在同一块"与人工图的一致率（越高越好）；
  ② 次判据：自动块数与人工块数是否相等（个数对上优先）。

用法: python tune_blocks2.py
"""
from __future__ import annotations

import json
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))

from shapely.geometry import Point, Polygon                      # noqa: E402

from oreblocks import load_holes_xls                            # noqa: E402
from pipeline import run_blast                                  # noqa: E402
from composite import load_composite_blocks                     # noqa: E402
import params as _params                                        # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DAY = ROOT.parent / "北部山头3940平台2026"
DATA = DAY / "7、单日数据"
PROBE = ROOT / "_probe"
SKIP = {"爆区方格网", "钻孔", "点", "线条", "孔口文字"}
DATES = ["0915", "0922", "1003", "1004", "1008"]


def manual_groups(date):
    import baseline as _bl
    j = json.loads(_bl.scan_path("3940", date).read_text(encoding="utf-8"))
    polys = []
    for p in j["polylines"]:
        if p["layer"] in SKIP or len(p["pts"]) < 3:
            continue
        poly = Polygon(p["pts"]).buffer(0)
        if poly.area >= 5.0:
            polys.append(poly.buffer(0.3))
    xls = sorted((DATA / ("北部山头3940平台-%s" % date)).glob("1、*.xls"))[0]
    holes = load_holes_xls(xls)
    gp = {}
    for h in holes.values():
        if h.grade < 0.5:
            continue
        for k, poly in enumerate(polys):
            if poly.contains(Point(h.x, h.y)):
                gp[h.short] = k
                break
    return gp, len(polys)


def agree(gp, blocks):
    auto = {}
    for k, b in enumerate(blocks):
        for h in b.holes:
            auto[h.short] = k
    keys = [k for k in gp if k in auto]
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
        gp, nb = manual_groups(d)
        cache[d] = (holes, list(holes.values()), gp, nb)
    print("%-8s %-8s %-8s %-8s %s" % ("最小块段", "合并阈值", "一致率", "块数对上", "逐日"))
    best = None
    for frag in (20, 30, 40, 50, 60, 80):
        for gap in (0.0, 0.3, 0.5, 0.7, 0.9):
            rates, hits, detail = [], 0, []
            for d in DATES:
                holes, allh, gp, nb = cache[d]
                P = dict(_params.for_blast(d, platform="3940"))
                P["min_fragment_m2"] = float(frag)
                P["block_merge_gap"] = float(gap)
                res = run_blast(holes, allh, P, comp, blast=d)
                r = agree(gp, res["blocks"])
                if r is None:
                    continue
                rates.append(r)
                same = len(res["blocks"]) == nb
                hits += int(same)
                detail.append("%s %.2f(%d/%d%s)" % (d, r, len(res["blocks"]), nb,
                                                    "" if same else "✗"))
            if not rates:
                continue
            m = sum(rates) / len(rates)
            print("%-8s %-8s %8.3f %5d/%-3d %s" % (frag, gap, m, hits, len(rates),
                                                   "  ".join(detail)))
            score = (hits, m)
            if best is None or score > best[0]:
                best = (score, frag, gap)
    print("\n最佳：最小块段 %s m²，合并阈值 %s（块数对上 %d 个炮区，一致率 %.3f）"
          % (best[1], best[2], best[0][0], best[0][1]))


if __name__ == "__main__":
    main()
