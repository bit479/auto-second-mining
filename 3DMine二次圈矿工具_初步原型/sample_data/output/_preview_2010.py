# -*- coding: utf-8 -*-
"""预览图：矿块填充色 + 边界 + 炮孔 + 网格品位文字（对齐 DWG 内容）。"""
import json
import numpy as np
from pathlib import Path

OUT = Path(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output")
data = json.load(open(OUT / "1004_macro" / "1004_blocks.json", encoding="utf-8"))

from matplotlib import pyplot as plt
from matplotlib.patches import Polygon as MplPolygon
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

color_plot = {"L1": "cyan", "L2": "blue", "L3": "red", "L4": "yellow"}
fig, ax = plt.subplots(figsize=(13, 10))
for b in data["blocks"]:
    parts = b.get("parts", [b["boundary"]])
    for ring in parts:
        ext = np.asarray(ring)
        ax.add_patch(MplPolygon(ext, closed=True, facecolor=color_plot[b["level"]],
                                edgecolor="black", lw=2.2, alpha=0.55))
    cx, cy = b["centroid"]
    ax.text(cx, cy, f"{b['no']}号矿块\n{b['avg_grade_g_t']:.3f} g/t", fontsize=12,
            ha="center", va="center", fontweight="bold",
            bbox=dict(facecolor="white", alpha=0.85, edgecolor="none", pad=1.5))
# 炮孔
for h in data["holes"]:
    ax.plot(h["x"], h["y"], "ko", ms=5, mfc="black")
    ax.text(h["x"] + 1.5, h["y"] + 1.5, f"{h['grade']:.2f}", fontsize=7, color="black")
ax.set_title("3940平台 1004 二次圈矿矿块图（DWG 2010 预览：矿块分色填充+炮孔品位+网格）", fontsize=12)
ax.set_aspect("equal")
fig.tight_layout()
png = OUT / "1004_macro" / "3940平台 1004二次圈矿矿块图_2010_预览.png"
fig.savefig(png, dpi=130)
plt.close(fig)
print("[PNG]", png.name)
