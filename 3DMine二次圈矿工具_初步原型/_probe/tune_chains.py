# -*- coding: utf-8 -*-
"""用人工图**贪心标定**每个炮区的左右链。

做法：从自动分链出发，对"没进任何链"的孔逐个试——放进左链 / 右链 / 不放，
取让"矿界 vs 人工块并集 的 IoU"最大的那个；反复迭代。

用法: python tune_chains.py [日期...]        # 缺省跑 0915/1008/1003/1004
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))

from shapely.geometry import Polygon                            # noqa: E402
from shapely.ops import unary_union                            # noqa: E402

from oreblocks import load_holes_xls                           # noqa: E402
from pipeline import pick_zone                                 # noqa: E402
from strip import zone_chains, zone_outline                     # noqa: E402
from composite import load_composite_blocks                    # noqa: E402
import params as _params                                       # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DAY = ROOT.parent / "北部山头3940平台2026"
DATA = DAY / "7、单日数据"
PROBE = ROOT / "_probe"
SKIP = {"爆区方格网", "钻孔", "点", "线条", "孔口文字"}


def manual_poly(date):
    j = json.loads((PROBE / ("manual_%s_c.json" % date)).read_text(encoding="utf-8"))
    polys = []
    for p in j["polylines"]:
        if p["layer"] in SKIP or len(p["pts"]) < 3:
            continue
        poly = Polygon(p["pts"]).buffer(0)
        if poly.area >= 5.0:
            polys.append(poly)
    return unary_union(polys)


def build(ore, allh, comp, P, date, ml, mr):
    return zone_outline(ore, allh, P["extrude_m"], comp_blocks=comp,
                        merge_gap=P["merge_gap_m"], blast=date,
                        simplify=P["simplify_m"],
                        alpha_k=P.get("ring_alpha_k", 0.0),
                        chain_left=ml, chain_right=mr)


def score(ring, man):
    if ring is None or ring.is_empty:
        return 0.0
    return ring.intersection(man).area / ring.union(man).area


def main() -> None:
    dates = [a for a in sys.argv[1:] if not a.startswith("-")] or \
        ["0915", "1008", "1003", "1004"]
    comp = load_composite_blocks(DAY / "5、 北部山头3940平台二次圈矿矿块图-2026综合.dwg")
    for d in dates:
        xls = sorted((DATA / ("北部山头3940平台-%s" % d)).glob("1、*.xls"))[0]
        holes = load_holes_xls(xls)
        allh = list(holes.values())
        P = _params.for_blast(d)
        ore, _ = pick_zone(holes, adjacent_max=P["zone_link_m"])
        man = manual_poly(d)
        ml = list(P.get("chain_left") or [])
        mr = list(P.get("chain_right") or [])
        ring0 = build(ore, allh, comp, P, d, ml, mr)
        best = score(ring0, man)
        left, right, _, _, _ = zone_chains(ore, allh, manual_left=ml, manual_right=mr)
        inchain = set(ore[j].short for j in left) | set(ore[j].short for j in right)
        cand = [h.short for h in ore if h.short not in inchain]
        print("== %s  初始 IoU %.3f（人工块并集 %.0f m²，矿界 %.0f m²）"
              % (d, best, man.area, ring0.area if ring0 else 0))
        print("   自动没进链的孔:", "、".join(cand) or "（无）")
        changed = True
        while changed and cand:
            changed = False
            for name in list(cand):
                for tgt in ("L", "R"):
                    tl = ml + [name] if tgt == "L" else list(ml)
                    tr = mr + [name] if tgt == "R" else list(mr)
                    io = score(build(ore, allh, comp, P, d, tl, tr), man)
                    if io > best + 1e-4:
                        best, ml, mr = io, tl, tr
                        changed = True
                if name in ml or name in mr:
                    cand.remove(name)
        print("   标定后 IoU %.3f；左链追加 %s；右链追加 %s"
              % (best, "、".join(ml) or "（无）", "、".join(mr) or "（无）"))
        print("   可写进参数： \"%s\": {\"chain_left\": %s, \"chain_right\": %s}"
              % (d, json.dumps(ml, ensure_ascii=False),
                 json.dumps(mr, ensure_ascii=False)))


if __name__ == "__main__":
    main()
