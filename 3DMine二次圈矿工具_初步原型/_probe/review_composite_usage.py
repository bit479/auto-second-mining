# -*- coding: utf-8 -*-
"""审图：自动矿块 + 综合图历史块（灰）+ 实际并入的那一块（橙）。

用法: python _probe\review_composite_usage.py <平台> <日期>
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))
sys.path.insert(0, str(ROOT / "_probe"))

import baseline as _bl                                   # noqa: E402
import params as _params                                 # noqa: E402
from composite import load_composite_blocks, merge_outline  # noqa: E402
from oreblocks import load_holes_xls                     # noqa: E402
from pipeline import run_blast                           # noqa: E402
from strip import LAST_RING                              # noqa: E402

matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
matplotlib.rcParams["axes.unicode_minus"] = False


def main():
    plat = sys.argv[1] if len(sys.argv) > 1 else "3940"
    date = sys.argv[2] if len(sys.argv) > 2 else "1008"
    pdir = ROOT.parent / ("北部山头%s平台2026" % plat)
    folder = _bl.blast_dir(plat, date)
    holes = load_holes_xls(sorted(folder.glob("1、*.xls"))[0])
    allh = list(holes.values())
    comp = load_composite_blocks(sorted(pdir.glob("*综合*.dwg"))[0])
    P = dict(_params.for_blast(date, platform=plat))
    res = run_blast(holes, allh, P, comp, blast=date)
    mb = LAST_RING.get("merged_block")
    cands = [c for c in comp if mb is not None and c[2] is mb] or None
    gap = float(P.get("merge_gap_m", 4.5))

    fig, ax = plt.subplots(figsize=(12, 12), dpi=130)
    for lay, _col, p in comp:
        x, y = p.exterior.xy
        ax.plot(x, y, color="#a0a0a0", lw=0.7, alpha=0.8)
    if mb is not None:
        x, y = mb.exterior.xy
        ax.fill(x, y, color="#ffb347", alpha=0.25)
        ax.plot(x, y, color="#e67e00", lw=2.2, label="实际并入综合图的历史块 %.1f m²" % mb.area)

    for b in res["blocks"]:
        mo, n = merge_outline(b.polygon, cands, gap)
        if mo is None:
            continue
        for g in ([mo] if mo.geom_type == "Polygon" else list(mo.geoms)):
            x, y = g.exterior.xy
            ax.plot(x, y, color="#008000", lw=2.0)
        c = mo.representative_point()
        ax.annotate("%d号 出图轮廓 %.0f m²（并 %d 块）" % (b.no, mo.area, n),
                    (c.x, c.y), color="#006000", fontsize=9)

    for h in allh:
        ax.plot(h.x, h.y, "o", color=("#d62728" if h.grade >= 0.5 else "#333333"), ms=4)
        ax.annotate(h.short.split("-")[-1], (h.x, h.y), fontsize=7)

    ax.set_aspect("equal")
    ax.grid(alpha=0.25)
    ax.set_title("%s-%s 自动圈矿 + 综合图参考（灰=综合图，橙=实际并入，绿=出图轮廓）"
                 % (plat, date))
    ax.legend(loc="best")
    out = ROOT / "sample_data" / "output" / ("审图_综合图参考_%s-%s.png" % (plat, date))
    fig.savefig(out, bbox_inches="tight")
    print("->", out)
    print("并入历史块：", "无" if mb is None else "%.2f m²" % mb.area)


if __name__ == "__main__":
    main()
