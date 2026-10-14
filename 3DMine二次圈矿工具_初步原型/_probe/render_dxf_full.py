# -*- coding: utf-8 -*-
"""成果 DXF → PNG（几何用 ezdxf 后端画，TEXT/MTEXT 另外用 matplotlib 叠一层，
因为 ezdxf 的 matplotlib 后端画不出我们的 TTF 中文样式，审图时会看不到标注）。

用法: python render_dxf_full.py <a.dxf> <out.png> [x0 x1 y0 y1] [figw]
"""
import sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend

src, dst = Path(sys.argv[1]), Path(sys.argv[2])
box = [float(v) for v in sys.argv[3:7]] if len(sys.argv) > 6 else None
figw = float(sys.argv[7]) if len(sys.argv) > 7 else 14.0
doc = ezdxf.readfile(str(src)); msp = doc.modelspace()
if box is None:
    from ezdxf import bbox as _bb
    e = _bb.extents(msp)
    box = [e.extmin.x, e.extmax.x, e.extmin.y, e.extmax.y]
x0, x1, y0, y1 = box
fig = plt.figure(figsize=(figw, max(4.0, figw * (y1 - y0) / max(1e-9, x1 - x0))), dpi=130)
ax = fig.add_axes([0.01, 0.01, 0.98, 0.98]); ax.set_axis_off()
Frontend(RenderContext(doc), MatplotlibBackend(ax)).draw_layout(msp, finalize=False)
# 叠字：按图纸单位换算成 points（1 pt = 1/72 inch；fig 宽度 figw inch 对应 (x1-x0) 米）
pt_per_m = figw * 72.0 / (x1 - x0)
for e in msp:
    try:
        if e.dxftype() == "TEXT":
            ax.text(e.dxf.insert[0], e.dxf.insert[1], e.dxf.text,
                    fontsize=max(1.0, e.dxf.height * pt_per_m * 0.75),
                    rotation=e.dxf.rotation, ha="left", va="baseline",
                    color="k", family="Microsoft YaHei")
        elif e.dxftype() == "MTEXT":
            txt = e.plain_text() if hasattr(e, "plain_text") else e.text
            p = e.dxf.insert
            ax.text(p[0], p[1], txt, fontsize=max(1.0, e.dxf.char_height * pt_per_m * 0.75),
                    ha="left", va="top", color="k", family="Microsoft YaHei")
    except Exception:
        pass
ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect("equal", adjustable="box")
fig.savefig(str(dst), facecolor="white"); print("出图 ->", dst)
