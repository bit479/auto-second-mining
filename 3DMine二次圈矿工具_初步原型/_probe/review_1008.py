# -*- coding: utf-8 -*-
"""1008 评审出图：自动圈矿（条带法 + 配方品位界限）vs 人工图 3 个矿块。

人工基准 = 用户 DWG 里的 3 条闭合块线（_probe/manual_1008_c.json 里面积
最大的 3 条：164.86 / 115.20 / 64.91 m²，合计 344.97）。

用法: python review_1008.py [tag]
输出: <1008输出目录>/BLOCKS_review_<tag>.png
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei",
                                          "DengXian", "SimSun"]
matplotlib.rcParams["axes.unicode_minus"] = False
from shapely.geometry import Polygon

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))

from oreblocks import load_holes_xls                       # noqa: E402
from strip import zone_outline, average_blocks, zone_chains, LAST_RING  # noqa: E402
from run_strip import pick_zone                            # noqa: E402
from composite import load_composite_blocks                # noqa: E402

D = Path(r"D:\WK\N CRT\北部山头3940平台2026")
DB = D / r"7、单日数据\北部山头3940平台-1008\1、3940平台 炮孔数据库1008.xls"
OUT = DB.parent / "二次圈矿成果_3940_1008_strip"
COMP = D / "5、 北部山头3940平台二次圈矿矿块图-2026综合.dwg"
MANUAL = ROOT / "_probe" / "manual_1008_c.json"

COLORS = {"L4": "#f4b183", "L3": "#ffd966", "L2": "#b4a7d6", "L1": "#a9d6d0"}


def manual_blocks():
    d = json.loads(MANUAL.read_text(encoding="utf-8"))
    out = []
    for p in d["polylines"]:
        if len(p["pts"]) < 3:
            continue
        poly = Polygon(p["pts"]).buffer(0)
        if poly.area >= 3.0:
            out.append((p["layer"], poly))
    out.sort(key=lambda t: -t[1].area)
    return out


def main() -> None:
    tag = sys.argv[1] if len(sys.argv) > 1 else "auto"
    holes = load_holes_xls(DB)
    allh = list(holes.values())
    ore, pending = pick_zone(holes)
    comp = load_composite_blocks(COMP)
    outline = zone_outline(ore, allh, 3.0, comp_blocks=comp, blast="1008")
    blocks = average_blocks(ore, outline, 2.7)
    man = manual_blocks()
    man_area = sum(p.area for _, p in man)

    left, right, c, u, v = zone_chains(ore, allh)
    print("矿孔 %d（左链 %s | 右链 %s）"
          % (len(ore), "、".join(ore[j].short for j in left),
             "、".join(ore[j].short for j in right)))
    print("自动矿界 %.3f m²   人工 3 块合计 %.3f m²  （差 %+.2f%%）"
          % (outline.area, man_area, 100 * (outline.area - man_area) / man_area))
    print("%-18s %9s %9s %9s %11s %8s  %s"
          % ("块", "自动m²", "人工m²", "面积差%", "体积m³", "品位", "孔"))
    for b in blocks:
        m, best = None, 0.0
        for layer, p in man:
            ov = p.intersection(b.polygon).area
            if ov > best:
                m, best = p, ov
        ma = m.area if m is not None else float("nan")
        print("%-18s %9.3f %9.3f %9s %11.3f %8.3f  %s"
              % ("%d 号 %s" % (b.no, b.label), b.area_m2, ma,
                 ("%+.1f" % (100 * (b.area_m2 - ma) / ma)) if m is not None else "-",
                 b.volume_m3, b.grade, "、".join(h.short for h in b.holes)))
    print("合计体积 %.3f m³" % sum(b.volume_m3 for b in blocks))

    fig, ax = plt.subplots(figsize=(11, 12.5), dpi=110)
    for b in blocks:
        for g in getattr(b.polygon, "geoms", [b.polygon]):
            xs, ys = g.exterior.xy
            ax.fill(xs, ys, color=COLORS.get(b.level_id, "#cccccc"), alpha=0.5, zorder=2)
            ax.plot(xs, ys, color="#0b7a6b", lw=1.7, zorder=4)
    for i, (layer, p) in enumerate(man):
        xs, ys = p.exterior.xy
        ax.plot(xs, ys, color="#d62728", lw=1.3, ls="--", zorder=6,
                label="人工图矿块" if i == 0 else None)
        c0 = p.representative_point()
        ax.text(c0.x, c0.y - 2.2, "人工 %.1f m²" % p.area, color="#d62728",
                fontsize=7, ha="center", zorder=9)
    for k, g in enumerate(getattr(outline, "geoms", [outline])):
        ox, oy = g.exterior.xy
        ax.plot(ox, oy, color="#1f4e9c", lw=0.9, ls=":", zorder=5,
                label="自动矿界" if k == 0 else None)
    mb = LAST_RING.get("merged_block")
    if mb is not None:
        xs, ys = mb.exterior.xy
        ax.plot(xs, ys, color="#ff7f0e", lw=1.0, ls="-.", zorder=5, label="并入的综合图块")
    for h in allh:
        cch = "#0b4f4f" if h.grade >= 0.5 else "#9a9a9a"
        ax.plot([h.x], [h.y], marker="+", ms=9, mew=1.5, color=cch, zorder=7)
        ax.annotate("%s %.2f" % (h.short, h.grade), (h.x, h.y),
                    textcoords="offset points", xytext=(4, 3), fontsize=5.5,
                    color=cch, zorder=8)
    for b in blocks:
        if b.polygon is None:
            continue
        p = b.polygon.representative_point()
        ax.text(p.x, p.y, "%d 号\n%s\n%.0f m³\n%.3f g/t"
                % (b.no, b.label, b.volume_m3, b.grade),
                ha="center", va="center", fontsize=8, zorder=9)
    ax.set_aspect("equal")
    ax.legend(loc="lower right", fontsize=8)
    ax.set_title("1008 自动圈矿评审 %s（红虚线=人工图矿块）" % tag)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    out = OUT / ("BLOCKS_review_%s.png" % tag)
    fig.savefig(out)
    print("出图 -> %s" % out)


if __name__ == "__main__":
    main()
