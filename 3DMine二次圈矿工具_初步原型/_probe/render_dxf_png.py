# -*- coding: utf-8 -*-
"""把成果 DXF 渲染成 PNG（ezdxf 绘图后端，支持 LWPOLYLINE/HATCH/IMAGE）。

用法: python render_dxf_png.py <a.dxf> <out.png> [dpi]
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend


def main() -> None:
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    dpi = int(sys.argv[3]) if len(sys.argv) > 3 else 110
    doc = ezdxf.readfile(str(src))
    msp = doc.modelspace()
    fig = plt.figure(figsize=(13, 15), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    Frontend(RenderContext(doc), MatplotlibBackend(ax)).draw_layout(msp, finalize=True)
    fig.savefig(str(dst), dpi=dpi, facecolor="white")
    print("出图 -> %s" % dst)


if __name__ == "__main__":
    main()
