# -*- coding: utf-8 -*-
"""分簇差异对照：把自动分簇跟人工图的"每块装了哪些孔"逐块比一遍。

用法: python cluster_diff.py <平台> <炮区> [炮区...]

输出四类差异：
  · 人工圈了、我们没圈
  · 我们圈了、人工没圈
  · 分组不同（同一批孔被切/并得不一样）
  · 逐一列出两边的孔组，便于人工指定 cluster_same / cluster_solo / cluster_exclude
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))
sys.path.insert(0, str(ROOT / "_probe"))

from shapely.geometry import Point, Polygon                       # noqa: E402

from oreblocks import load_holes_xls                             # noqa: E402
from pipeline import run_blast                                   # noqa: E402
from composite import load_composite_blocks                      # noqa: E402
import params as _params                                         # noqa: E402
import baseline as _bl                                           # noqa: E402

DAY = ROOT.parent
PLATFORM_DIRS = {"3940": DAY / "北部山头3940平台2026",
                 "3960": DAY / "北部山头3960平台2026"}
SKIP = {"爆区方格网", "钻孔", "点", "线条", "孔口文字"}


def key(s: str) -> int:
    d = "".join(c for c in s if c.isdigit())
    return int(d) if d else 0


def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__)
        return
    plat, dates = sys.argv[1], sys.argv[2:]
    day = PLATFORM_DIRS[plat]
    comp = load_composite_blocks(next(iter(day.glob("*综合*.dwg")), None))
    data = day / "7、单日数据"
    for d in dates:
        folder = next(x for x in data.iterdir() if x.name.endswith("-" + d))
        xls = (sorted(folder.glob("1、*.xls")) or sorted(folder.glob("*.xls")))[0]
        holes = load_holes_xls(xls)
        allh = list(holes.values())
        j = json.loads(_bl.scan_path(plat, d).read_text(encoding="utf-8"))
        man = []
        for p in j["polylines"]:
            if p["layer"] in SKIP or len(p["pts"]) < 3:
                continue
            poly = Polygon(p["pts"]).buffer(0)
            if poly.area >= 5.0:
                ins = sorted({h.short for h in allh if poly.contains(Point(h.x, h.y))},
                             key=key)
                man.append((poly.area, ins))
        man.sort(key=lambda t: -t[0])
        res = run_blast(holes, allh, _params.for_blast(d, platform=plat),
                        comp, blast=d)
        ours = sorted([(b.area_m2, sorted({h.short for h in b.holes}, key=key))
                       for b in res["blocks"]], key=lambda t: -t[0])
        man_holes = {h for _, g in man for h in g}
        our_holes = {h for _, g in ours for h in g}
        print("===== %s-%s  人工 %d 块 / 自动 %d 块" % (plat, d, len(man), len(ours)))
        if man_holes - our_holes:
            print("  人工圈了、我们没圈：%s" % "、".join(sorted(man_holes - our_holes, key=key)))
        if our_holes - man_holes:
            print("  我们圈了、人工没圈：%s" % "、".join(sorted(our_holes - man_holes, key=key)))
        print("  人工：")
        for a, g in man:
            print("    %6.0f m²  %s" % (a, "、".join(g) or "（无孔）"))
        print("  自动：")
        for a, g in ours:
            print("    %6.0f m²  %s" % (a, "、".join(g) or "（无孔）"))


if __name__ == "__main__":
    main()
