# -*- coding: utf-8 -*-
"""多炮区回归出图：0915/0922/1003/1004/1008 各画一张自动圈矿结果。

用法: python review_batch.py
输出: <项目>\sample_data\output\回归_自动圈矿_<日期>.png  +  …_总览.png
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun"]
matplotlib.rcParams["axes.unicode_minus"] = False

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
COLORS = {"L4": "#f4b183", "L3": "#ffd966", "L2": "#b4a7d6", "L1": "#a9d6d0"}
DATES = ["0915", "0922", "1003", "1004", "1008"]


def run_one(date: str, comp):
    folder = DATA / ("北部山头3940平台-%s" % date)
    xls = next(iter(sorted(folder.glob("1、*.xls"))), None)
    if xls is None:
        return None
    holes = load_holes_xls(xls)
    allh = list(holes.values())
    ore, pending = pick_zone(holes)
    if len(ore) < 2:
        return None
    ring = zone_outline(ore, allh, 3.0, comp_blocks=comp, blast=date)
    if ring is None:
        return None
    blocks = average_blocks(ore, ring, 2.7)
    return {"date": date, "all": allh, "ore": ore, "ring": ring,
            "blocks": blocks, "pending": pending}


def draw(res, ax, show_all=False):
    ring = res["ring"]
    for g in getattr(ring, "geoms", [ring]):
        xs, ys = g.exterior.xy
        ax.plot(xs, ys, color="#1f4e9c", lw=0.9, ls=":", zorder=5)
    for b in res["blocks"]:
        if b.polygon is None:
            continue
        for g in getattr(b.polygon, "geoms", [b.polygon]):
            xs, ys = g.exterior.xy
            ax.fill(xs, ys, color=COLORS.get(b.level_id, "#cccccc"), alpha=0.55, zorder=2)
            ax.plot(xs, ys, color="#0b7a6b", lw=1.3, zorder=4)
        p = b.polygon.representative_point()
        ax.text(p.x, p.y, "%d号\n%.0f m³\n%.3f g/t" % (b.no, b.volume_m3, b.grade),
                ha="center", va="center", fontsize=6.5, zorder=9)
    for h in res["all"]:
        c = "#0b4f4f" if h.grade >= 0.5 else "#a0a0a0"
        ax.plot([h.x], [h.y], marker="+", ms=6 if h.grade >= 0.5 else 4,
                mew=1.2, color=c, zorder=7)
    tv = sum(b.volume_m3 for b in res["blocks"])
    ax.set_title("%s 自动圈矿：%d 个矿块，合计 %.0f m³（矿孔 %d）"
                 % (res["date"], len(res["blocks"]), tv, len(res["ore"])), fontsize=10)
    ax.set_aspect("equal")
    ax.grid(alpha=0.2)


def main() -> None:
    comp = load_composite_blocks(COMP)
    results = []
    for d in DATES:
        r = run_one(d, comp)
        if r is None:
            print("%s 跳过（缺数据）" % d)
            continue
        results.append(r)
        fig, ax = plt.subplots(figsize=(10, 12), dpi=100)
        draw(r, ax)
        fig.tight_layout()
        p = OUT / ("回归_自动圈矿_%s.png" % d)
        fig.savefig(p)
        plt.close(fig)
        print("%s -> %s" % (d, p))
    if results:
        fig, axes = plt.subplots(1, len(results), figsize=(6 * len(results), 9), dpi=90)
        for ax, r in zip(axes if hasattr(axes, "__len__") else [axes], results):
            draw(r, ax)
        fig.tight_layout()
        p = OUT / "回归_自动圈矿_总览.png"
        fig.savefig(p)
        print("总览 -> %s" % p)


if __name__ == "__main__":
    main()
