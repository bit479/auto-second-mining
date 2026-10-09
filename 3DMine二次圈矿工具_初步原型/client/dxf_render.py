# -*- coding: utf-8 -*-
"""把 Step2 产出的 full.dxf 渲染成 PNG（含炮孔十字/水平引线/品位文字/矿块边界/矿块号），供验收。"""
import sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

import ezdxf

def load_font():
    for cand in [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf",
                 r"C:\Windows\Fonts\simsun.ttc"]:
        p = Path(cand)
        if p.exists():
            try:
                font_manager.fontManager.addfont(str(p))
                return font_manager.FontProperties(fname=str(p)).get_name()
            except Exception:
                continue
    return None

def main():
    dxf_path = sys.argv[1]
    out = sys.argv[2]
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()
    fn = load_font()
    fig, ax = plt.subplots(figsize=(16, 11))
    lines = texts = 0
    for e in msp:
        t = e.dxftype()
        if t == "LINE":
            p = e.dxf.start
            q = e.dxf.end
            col = e.dxf.color
            ax.plot([p.x, q.x], [p.y, q.y], "-", color=f"C{col % 10}", lw=0.7, zorder=2)
            lines += 1
        elif t in ("TEXT", "MTEXT"):
            p = e.dxf.insert
            s = e.dxf.text if t == "TEXT" else e.text
            s = (s or "").replace("\n", " ").strip()
            h = e.dxf.height if t == "TEXT" else 1.0
            col = e.dxf.color
            ax.text(p.x, p.y, s, fontsize=min(max(h * 3.0, 3), 12), color=f"C{col % 10}",
                    fontproperties=font_manager.FontProperties(fname=None, family=fn) if fn else None,
                    zorder=4, va="bottom")
            texts += 1
    ax.set_aspect("equal")
    ax.grid(True, ls=":", alpha=0.3)
    ax.set_title(f"{Path(dxf_path).stem}  ({lines} lines / {texts} texts)", fontsize=12)
    fig.tight_layout()
    fig.savefig(out, dpi=110, facecolor="white", bbox_inches="tight")
    print("saved:", out, "| lines:", lines, "texts:", texts)

if __name__ == "__main__":
    main()
