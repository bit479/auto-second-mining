# -*- coding: utf-8 -*-
"""自检：出图时确实参考综合图，但只并"与当日矿块直接相接"的那一块。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))
sys.path.insert(0, str(ROOT / "_probe"))

import baseline as _bl                                   # noqa: E402
import params as _params                                 # noqa: E402
from composite import load_composite_blocks, merge_outline  # noqa: E402
from oreblocks import load_holes_xls                     # noqa: E402
from pipeline import run_blast                           # noqa: E402
from strip import LAST_RING                              # noqa: E402

checks = []


def check(ok, msg):
    print(("  ✓ " if ok else "  ✗ ") + msg)
    checks.append(bool(ok))


def run_case(plat, date):
    pdir = ROOT.parent / ("北部山头%s平台2026" % plat)
    folder = _bl.blast_dir(plat, date)
    holes = load_holes_xls(sorted(folder.glob("1、*.xls"))[0])
    comp = load_composite_blocks(sorted(pdir.glob("*综合*.dwg"))[0])
    P = dict(_params.for_blast(date, platform=plat))
    res = run_blast(holes, list(holes.values()), P, comp, blast=date)
    return res, comp, P


def main():
    for plat, date in (("3940", "0915"), ("3940", "1003"), ("3940", "1004"),
                       ("3940", "1008")):
        print("== %s-%s" % (plat, date))
        res, comp, P = run_case(plat, date)
        gap = float(P.get("merge_gap_m", 4.5))
        check(abs(gap - 4.5) < 1e-9, "接综合图间距 = 4.5 m")
        mb = LAST_RING.get("merged_block")
        check(mb is not None, "矿界阶段确实读取并贴合了综合图")
        cands = [c for c in comp if mb is not None and c[2] is mb] or None
        counts = [merge_outline(b.polygon, cands, gap)[1] for b in res["blocks"]]
        check(max(counts or [0]) <= 1,
              "每个当日矿块最多并 1 个历史块（实际 %s）" % counts)
        if date == "1008":
            check(abs(mb.area - 82.254) < 1.0,
                  "1008 并入的是 82 m² 那块（实际 %.2f）" % mb.area)
            far = min((b.polygon.distance(p) for b in res["blocks"]
                       for lay, _c, p in comp if abs(p.area - 725.2) < 1.0),
                      default=999)
            check(far > 4.0, "725 m² 大块没有并入（最近 %.2f m）" % far)
    failed = checks.count(False)
    print("\n%d/%d 通过" % (len(checks) - failed, len(checks)))
    print("结论：" + ("全部通过 ✓" if not failed else "有 %d 项没通过" % failed))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())

