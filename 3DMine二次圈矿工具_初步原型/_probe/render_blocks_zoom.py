# -*- coding: utf-8 -*-
"""只画矿块轮廓的局部放大图（审图用：看清块与块的接缝，不受文字干扰）。

用法: python render_blocks_zoom.py <a.dxf> <out.png> x0 x1 y0 y1 [figw]
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon
import ezdxf

BLOCK_LAYERS = ("0.500-1.000", "1.000-1.500", "1.500-3.000", "3.000-999.000")
ACI = {1: "#ff0000", 2: "#ffff00", 4: "#00ffff", 5: "#0000ff"}


def main():
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    x0, x1, y0, y1 = [float(v) for v in sys.argv[3:7]]
    figw = float(sys.argv[7]) if len(sys.argv) > 7 else 12.0
    doc = ezdxf.readfile(str(src))
    msp = doc.modelspace()
    fig, ax = plt.subplots(figsize=(figw, max(3.0, figw * (y1 - y0) / (x1 - x0))),
                           dpi=150)
    for e in msp:
        if e.dxftype() != "LWPOLYLINE" or e.dxf.layer not in BLOCK_LAYERS:
            continue
        pts = [(p[0], p[1]) for p in e.get_points()]
        col = ACI.get(e.dxf.color, "#333333")
        ax.add_patch(MplPolygon(pts, closed=True, facecolor=col, alpha=0.18,
                                edgecolor=col, linewidth=1.6))
    # 矿块号：文字 + 引线（引线起点应在本块内部中心）
    labels = [e for e in msp if e.dxftype() == "MTEXT"
              and str(e.text).endswith("号矿块")]
    for e in msp:
        if e.dxftype() != "LINE" or e.dxf.layer != "0":
            continue
        a, b = e.dxf.start, e.dxf.end
        for lab in labels:
            ins = lab.dxf.insert
            if ((abs(a[0] - ins[0]) < 0.01 and abs(a[1] - ins[1]) < 0.01)
                    or (abs(b[0] - ins[0]) < 0.01 and abs(b[1] - ins[1]) < 0.01)):
                ax.plot([a[0], b[0]], [a[1], b[1]], color="#444444",
                        linewidth=1.4, zorder=5)
                break
    for lab in labels:
        ins = lab.dxf.insert
        ax.text(ins[0], ins[1], str(lab.text), fontsize=11,
                family="Microsoft YaHei", color="black", va="top", zorder=6)
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, linewidth=0.3, alpha=0.4)
    ax.ticklabel_format(useOffset=False, style="plain")
    fig.savefig(str(dst), bbox_inches="tight", facecolor="white")
    print("出图 ->", dst)


if __name__ == "__main__":
    main()
