# -*- coding: utf-8 -*-
"""人工图 vs 自动圈矿 逐日对照（0915/0922/1003/1004/1008）。

人工块 = 人工 DWG 扫描结果里面积 ≥5 m² 的折线（排除爆区方格网/钻孔/点/线条图层）。
输出: <项目>\sample_data\output\对照_<日期>.png
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun"]
matplotlib.rcParams["axes.unicode_minus"] = False
from shapely.geometry import Polygon                     # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))

from oreblocks import load_holes_xls                       # noqa: E402
from strip import zone_outline, average_blocks             # noqa: E402
from run_strip import pick_zone                            # noqa: E402
from composite import load_composite_blocks                # noqa: E402

DAY = ROOT.parent / "北部山头3940平台2026"
DATA = DAY / "7、单日数据"
COMP = DAY / "5、 北部山头3940平台二次圈矿矿块图-2026综合.dwg"
OUT = ROOT / "sample_data" / "output"
PROBE = ROOT / "_probe"
SKIP = {"爆区方格网", "钻孔", "点", "线条", "孔口文字"}
COLORS = {"L4": "#f4b183", "L3": "#ffd966", "L2": "#b4a7d6", "L1": "#a9d6d0"}
DATES = ["0915", "0922", "1003", "1004", "1008"]


def manual_blocks(date):
    j = json.loads((PROBE / ("manual_%s_c.json" % date)).read_text(encoding="utf-8"))
    out = []
    for p in j["polylines"]:
        if p["layer"] in SKIP or len(p["pts"]) < 3:
            continue
        poly = Polygon(p["pts"]).buffer(0)
        if poly.area >= 5.0:
            out.append((p["layer"], poly))
    out.sort(key=lambda t: -t[1].area)
    return out


def auto_blocks(date, comp):
    folder = DATA / ("北部山头3940平台-%s" % date)
    xls = sorted(folder.glob("1、*.xls"))[0]
    holes = load_holes_xls(xls)
    allh = list(holes.values())
    ore, pending = pick_zone(holes)
    ring = zone_outline(ore, allh, 3.0, comp_blocks=comp, blast=date)
    blocks = average_blocks(ore, ring, 2.7)
    return allh, ore, ring, blocks


def draw_manual(ax, man, title):
    for i, (layer, p) in enumerate(man):
        xs, ys = p.exterior.xy
        ax.fill(xs, ys, color="#ffd9d9", alpha=0.8, zorder=2)
        ax.plot(xs, ys, color="#c00000", lw=1.4, zorder=4)
        c = p.representative_point()
        ax.text(c.x, c.y, "%.0f" % p.area, ha="center", va="center",
                fontsize=7, color="#8b0000", zorder=6)
    ax.set_title(title, fontsize=10)
    ax.set_aspect("equal")
    ax.grid(alpha=0.2)


def draw_auto(ax, allh, ring, blocks, title):
    for b in blocks:
        if b.polygon is None:
            continue
        for g in getattr(b.polygon, "geoms", [b.polygon]):
            xs, ys = g.exterior.xy
            ax.fill(xs, ys, color=COLORS.get(b.level_id, "#ccc"), alpha=0.6, zorder=2)
            ax.plot(xs, ys, color="#0b7a6b", lw=1.3, zorder=4)
        c = b.polygon.representative_point()
        ax.text(c.x, c.y, "%d号\n%.0f m³\n%.2f" % (b.no, b.volume_m3, b.grade),
                ha="center", va="center", fontsize=6, zorder=9)
    for h in allh:
        ax.plot([h.x], [h.y], marker="+", ms=5, mew=1.1,
                color="#0b4f4f" if h.grade >= 0.5 else "#a8a8a8", zorder=7)
    ax.set_title(title, fontsize=10)
    ax.set_aspect("equal")
    ax.grid(alpha=0.2)


def main() -> None:
    comp = load_composite_blocks(COMP)
    print("%-6s %-22s %-22s" % ("炮区", "人工块面积(m²)", "自动块面积(m²)"))
    for d in DATES:
        man = manual_blocks(d)
        allh, ore, ring, blocks = auto_blocks(d, comp)
        ma = "、".join("%.0f" % p.area for _, p in man)
        aa = "、".join("%.0f" % b.area_m2 for b in blocks)
        print("%-6s %-22s %-22s  人工合计%.0f  自动合计%.0f  (矿界%.0f)"
              % (d, ma, aa, sum(p.area for _, p in man),
                 sum(b.area_m2 for b in blocks), ring.area))
        fig, axes = plt.subplots(1, 2, figsize=(20, 10), dpi=95)
        draw_manual(axes[0], man, "%s 人工图（%d 块）" % (d, len(man)))
        draw_auto(axes[1], allh, ring, blocks,
                  "%s 自动（%d 块，合计 %.0f m³）"
                  % (d, len(blocks), sum(b.volume_m3 for b in blocks)))
        fig.tight_layout()
        p = OUT / ("对照_%s.png" % d)
        fig.savefig(p)
        plt.close(fig)
        print("   ->", p)


if __name__ == "__main__":
    main()
