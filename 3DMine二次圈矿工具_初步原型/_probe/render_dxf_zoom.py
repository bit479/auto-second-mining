# -*- coding: utf-8 -*-
"""把成果 DXF 的某个范围内实体渲染成 PNG（放大看细节：十字/引线/品位字/矿块号/表）。"""
import sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
src=Path(sys.argv[1]); dst=Path(sys.argv[2])
x0,x1,y0,y1=[float(v) for v in sys.argv[3:7]]
figw=float(sys.argv[7]) if len(sys.argv)>7 else 14.0
doc=ezdxf.readfile(str(src)); msp=doc.modelspace()
h=figw*(y1-y0)/max(1e-9,(x1-x0))
fig=plt.figure(figsize=(figw,h),dpi=110); ax=fig.add_axes([0.01,0.01,0.98,0.98])
ax.set_axis_off()
Frontend(RenderContext(doc), MatplotlibBackend(ax)).draw_layout(msp, finalize=False)
ax.set_xlim(x0,x1); ax.set_ylim(y0,y1); ax.set_aspect("equal", adjustable="box")
fig.savefig(str(dst),dpi=110,facecolor="white"); print("出图 ->",dst)
