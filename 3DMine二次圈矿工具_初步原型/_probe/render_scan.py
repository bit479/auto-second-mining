# -*- coding: utf-8 -*-
"""把 scan_manual_dwg.py 抽出的 JSON 画成图，便于看清人工图结构。

用法: python render_scan.py <scan.json> <out.png>
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

LAYER_STYLE = {
    "0": ("#222222", 1.4),
    "0.500-1.000": ("#00b6b6", 2.0),
    "1.000-1.500": ("#2b5cff", 2.0),
    "1.500-3.000": ("#e01b1b", 2.0),
    "3.000-999.000": ("#e0c000", 2.0),
    "爆区方格网": ("#bdbdbd", 0.5),
    "钻孔": ("#008b8b", 0.8),
    "点": ("#ff8800", 0.6),
    "线条": ("#666666", 0.8),
}


def main() -> None:
    src = Path(sys.argv[1])
    out = Path(sys.argv[2])
    d = json.loads(src.read_text(encoding="utf-8"))

    fig, ax = plt.subplots(figsize=(16, 12))
    for p in d["polylines"]:
        pts = p["pts"]
        color, lw = LAYER_STYLE.get(p["layer"], ("#999999", 0.6))
        ax.plot([q[0] for q in pts], [q[1] for q in pts], color=color, lw=lw)
    for l in d["lines"]:
        ax.plot([l["a"][0], l["b"][0]], [l["a"][1], l["b"][1]], color="#000000", lw=1.6)
    for h in d["hatches"]:
        if "cx" in h:
            ax.plot(h["cx"], h["cy"], marker="+", color="#008b8b", ms=6, mew=1.2)

    by_h = defaultdict(list)
    for t in d["texts"]:
        by_h[(t["layer"], t["h"])].append(t)
    for (layer, h), items in by_h.items():
        col = "#0a7d00" if h >= 0.4 else "#aa0000"
        if h >= 3.0:
            col = "#0000cc"
        for t in items:
            ax.text(t["pos"][0], t["pos"][1], t["txt"], fontsize=(6 if h < 0.3 else 7),
                    color=col, ha="left", va="center")
    for t in d["texts"]:
        if t["kind"] == "AcDbMText":
            ax.text(t["pos"][0], t["pos"][1], t["txt"], fontsize=11, color="#cc00cc")

    ax.set_aspect("equal")
    ax.grid(True, lw=0.2, alpha=0.3)
    ax.set_title(src.name)
    fig.tight_layout()
    fig.savefig(out, dpi=130, facecolor="white")
    print("saved", out)


if __name__ == "__main__":
    main()
