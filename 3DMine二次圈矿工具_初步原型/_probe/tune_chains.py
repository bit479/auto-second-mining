# -*- coding: utf-8 -*-
"""用人工图**贪心标定**每个炮区的"外推距离 + 左右链"。

做法：对每个候选外推距离，从自动分链出发，把"没进任何链"的孔逐个试放进左链/右链，
取"矿界 vs 人工块并集 的 IoU"最大的组合；最后在所有外推距离里挑 IoU 最好的那个。

用法:
  python tune_chains.py 0915 1003            # 只标链
  python tune_chains.py 0922 --extrude 5.0 6.0 7.0 8.0 9.0   # 联搜外推距离
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
from strip import zone_chains, zone_outline, average_blocks     # noqa: E402
from composite import load_composite_blocks                    # noqa: E402
import params as _params                                       # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DAY = ROOT.parent / "北部山头3940平台2026"
DATA = DAY / "7、单日数据"
PROBE = ROOT / "_probe"
SKIP = {"爆区方格网", "钻孔", "点", "线条", "孔口文字"}
MV = {"0915": 13497.316, "0922": 7075.279, "1003": 9435.031,
      "1004": 9846.363, "1008": 3951.494}


def manual_poly(date: str):
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
    """按给定参数跑**整个炮区**（含孤立小组），返回 (所有带矿界的并集, 矿块)。"""
    from pipeline import run_blast
    holes = {h.hid: h for h in allh}
    P2 = dict(P)
    P2["chain_left"], P2["chain_right"] = list(ml), list(mr)
    res = run_blast(holes, allh, P2, comp, blast=date)
    if not res["rings"]:
        return None, []
    ring = res["rings"][0]
    for rr in res["rings"][1:]:
        ring = ring.union(rr)
    return ring, res["blocks"]


def score(ring, man):
    if ring is None or ring.is_empty:
        return 0.0
    return ring.intersection(man).area / ring.union(man).area


def tune_one(date: str, comp, grid=None):
    xls = sorted((DATA / ("北部山头3940平台-%s" % date)).glob("1、*.xls"))[0]
    holes = load_holes_xls(xls)
    allh = list(holes.values())
    P0 = _params.for_blast(date, platform="3940")
    ore, _ = pick_zone(holes, adjacent_max=P0["zone_link_m"])
    man = manual_poly(date)
    best = None
    for ex in (grid or [P0["extrude_m"]]):
        P = dict(P0)
        P["extrude_m"] = float(ex)
        ml, mr = list(P0.get("chain_left") or []), list(P0.get("chain_right") or [])
        ring, blocks = build(ore, allh, comp, P, date, ml, mr)
        if ring is None:
            continue
        sc = score(ring, man)
        left, right, _, _, _ = zone_chains(ore, allh, manual_left=ml, manual_right=mr)
        inchain = set(ore[j].short for j in left) | set(ore[j].short for j in right)
        cand = [h.short for h in ore if h.short not in inchain]
        moved = True
        while moved and cand:
            moved = False
            for name in list(cand):
                for tl, tr in ((ml + [name], mr), (ml, mr + [name])):
                    rr, _ = build(ore, allh, comp, P, date, tl, tr)
                    s2 = score(rr, man)
                    if s2 > sc + 1e-4:
                        sc, ml, mr, moved = s2, tl, tr, True
                if name in ml or name in mr:
                    cand.remove(name)
        _, blocks = build(ore, allh, comp, P, date, ml, mr)
        tv = sum(b.volume_m3 for b in blocks)
        mv = MV.get(date)
        dev = (tv - mv) / mv if mv else 0.0
        print("   外推 %4.1f m → IoU %.3f  体积 %9.1f (%+6.1f%%)  %d 块"
              % (ex, sc, tv, dev * 100, len(blocks)))
        if best is None or sc > best[0]:
            best = (sc, float(ex), ml, mr, tv, dev, len(blocks))
    return best


def main() -> None:
    argv = sys.argv[1:]
    grid = None
    if "--extrude" in argv:
        i = argv.index("--extrude")
        grid = [float(x) for x in argv[i + 1:] if not x.startswith("-")]
        argv = argv[:i]
    dates = [a for a in argv if not a.startswith("-")] or ["0915", "1008", "1003", "1004"]
    comp = load_composite_blocks(DAY / "5、 北部山头3940平台二次圈矿矿块图-2026综合.dwg")
    for d in dates:
        print("================ %s" % d)
        b = tune_one(d, comp, grid)
        if b is None:
            print("   没算出来")
            continue
        sc, ex, ml, mr, tv, dev, nb = b
        print("   最佳：外推 %.1f m  IoU %.3f  体积 %.1f (%+.1f%%)  %d 块"
              % (ex, sc, tv, dev * 100, nb))
        print("   可写进参数： \"%s\": {\"extrude_m\": %.1f, \"chain_left\": %s,"
              " \"chain_right\": %s}"
              % (d, ex, json.dumps(ml, ensure_ascii=False),
                 json.dumps(mr, ensure_ascii=False)))


if __name__ == "__main__":
    main()
