# -*- coding: utf-8 -*-
"""把人工图（scan JSON）与我的 DXF 渲染到同一窗口，便于同尺度比对。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import ezdxf                   # noqa: E402
from ezdxf.addons.drawing import Frontend, RenderContext  # noqa: E402
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend  # noqa: E402

WIN = (470088, 470112, 4349744, 4349772)


def main() -> None:
    scan = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    dxf = Path(sys.argv[2])

    fig, ax = plt.subplots(figsize=(14, 14))
    for p in scan["polylines"]:
        pts = p["pts"]
        col = {"点": "#008b8b", "钻孔": "#0000cc", "爆区方格网": "#dddddd",
               "线条": "#888888"}.get(p["layer"], "#111111")
        ax.plot([q[0] for q in pts], [q[1] for q in pts], color=col, lw=0.7)
    for l in scan["lines"]:
        ax.plot([l["a"][0], l["b"][0]], [l["a"][1], l["b"][1]], color="k", lw=1.2)
    ax.set_aspect("equal")
    ax.set_xlim(WIN[0], WIN[1])
    ax.set_ylim(WIN[2], WIN[3])
    ax.set_title("MANUAL")
    fig.tight_layout()
    fig.savefig(str(dxf.with_name(dxf.stem + "_cmp_manual.png")), dpi=110, facecolor="white")
    plt.close(fig)

    doc = ezdxf.readfile(str(dxf))
    msp = doc.modelspace()
    for e in list(msp):
        if e.dxftype() == "IMAGE":
            msp.delete_entity(e)
    fig, ax = plt.subplots(figsize=(14, 14))
    Frontend(RenderContext(doc), MatplotlibBackend(ax)).draw_layout(msp, finalize=True)
    ax.set_aspect("equal")
    ax.set_xlim(WIN[0], WIN[1])
    ax.set_ylim(WIN[2], WIN[3])
    ax.set_title("MINE")
    fig.tight_layout()
    fig.savefig(str(dxf.with_name(dxf.stem + "_cmp_mine.png")), dpi=110, facecolor="white")
    plt.close(fig)
    print("saved cmp images")


if __name__ == "__main__":
    main()
