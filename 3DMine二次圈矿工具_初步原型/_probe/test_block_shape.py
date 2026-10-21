# -*- coding: utf-8 -*-
"""自检：自动矿块必须是"连成一片 + 边界抽稀 + 面积口径不变"。

针对 2026-10-21 用户反馈的两个典型：
  3960-0922：原来被切成 3 片、一个块 454 个顶点；
  3960-1007：原来被切成 2 片、一个块 215 个顶点。
"""
from __future__ import annotations

import sys
from pathlib import Path

from shapely.geometry import Point

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))
sys.path.insert(0, str(ROOT / "_probe"))

import baseline as _bl                                  # noqa: E402
import params as _params                                # noqa: E402
from composite import load_composite_blocks             # noqa: E402
from oreblocks import load_holes_xls                    # noqa: E402
from pipeline import run_blast                          # noqa: E402

CASES = [("3960", "0922"), ("3960", "1007")]
checks = []


def check(ok, msg):
    print(("  ✓ " if ok else "  ✗ ") + msg)
    checks.append(bool(ok))


def run_case(plat, date):
    pdir = ROOT.parent / ("北部山头%s平台2026" % plat)
    folder = _bl.blast_dir(plat, date)
    xls = sorted(folder.glob("1、*.xls"))[0]
    holes = load_holes_xls(xls)
    allh = list(holes.values())
    comp = load_composite_blocks(sorted(pdir.glob("*综合*.dwg"))[0])
    return run_blast(holes, allh, dict(_params.for_blast(date, platform=plat)),
                     comp, blast=date)


def main():
    for plat, date in CASES:
        print("== %s-%s" % (plat, date))
        res = run_case(plat, date)
        b = res["blocks"][0]
        g = b.polygon
        check(g.geom_type == "Polygon", "1 号块是一个连通 Polygon（不是 MultiPolygon）")
        n = len(g.exterior.coords)
        check(n < 100, "轮廓顶点 %d 个（<100，已抽稀）" % n)
        check(all(g.buffer(1e-6).contains(Point(h.x, h.y)) for h in b.holes),
              "块内矿孔都还在轮廓内")
        vol = sum(x.volume_m3 for x in res["blocks"])
        mv = _bl.manual_volume(plat, date)
        if mv:
            d = (vol - mv) / mv * 100.0
            check(abs(d) <= 5.0, "合计体积偏差 %+.1f%%（≤±5%%）" % d)
    failed = checks.count(False)
    print("\n%d/%d 通过" % (len(checks) - failed, len(checks)))
    print("结论：" + ("全部通过 ✓" if not failed else "有 %d 项没通过" % failed))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
