# -*- coding: utf-8 -*-
"""渲染 blocks.json 为矿块图预览（炮孔 + 分级边界 + 矿块号），供验收对比。"""
import sys, json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPoly

LV_COLOR = {"L1": "cyan", "L2": "blue", "L3": "red", "L4": "gold"}

def main():
    js = sys.argv[1]
    out = sys.argv[2]
    d = json.load(open(js, encoding="utf-8"))
    fig, ax = plt.subplots(figsize=(14, 10))
    holes = d["holes"]
    for h in holes:
        g = h["grade"]
        col = "gray" if g < 0.5 else (LV_COLOR["L1"] if g < 1 else LV_COLOR["L2"] if g < 1.5 else LV_COLOR["L3"] if g < 3 else LV_COLOR["L4"])
        ax.plot(h["x"], h["y"], "o", ms=6, color=col, zorder=3)
        ax.annotate(f"{h['id'].split('-')[-1]}\n{g:.2f}", (h["x"], h["y"]),
                    textcoords="offset points", xytext=(6, 6), fontsize=6, color="k")
    for b in d["blocks"]:
        col = LV_COLOR.get(b["level"], "black")
        for part in b["parts"]:
            xs = [p[0] for p in part]
            ys = [p[1] for p in part]
            ax.plot(xs, ys, "-", color=col, lw=2, zorder=2)
            ax.add_patch(MplPoly(list(zip(xs, ys)), fill=True, alpha=0.06, color=col))
        cx, cy = b["centroid"]
        ax.annotate(f"#{b['no']} {b['grade_label']}\n{b['avg_grade_g_t']:.3f} g/t {b['area_m2']:.0f}m2",
                    (cx, cy), ha="center", fontsize=10, color="black",
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=col, alpha=0.9), zorder=4)
    ax.set_aspect("equal")
    ax.grid(True, ls=":", alpha=0.4)
    ax.set_title(f"{d['meta']['blast_id']}  程序圈矿（Alpha Shape 凹包 + 全孔品位加权）", fontsize=13)
    fig.savefig(out, dpi=110, facecolor="white", bbox_inches="tight")
    print("saved:", out)

if __name__ == "__main__":
    main()
