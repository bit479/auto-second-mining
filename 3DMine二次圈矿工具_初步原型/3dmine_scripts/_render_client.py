# -*- coding: utf-8 -*-
"""渲染通用 Step2 产物（全图 + 炮孔区放大）。"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend

DXF = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\sample_data\output\二次圈矿成果_3940_1004\BS-3940-1004_二次圈矿矿块图_full.dxf"
doc = ezdxf.readfile(DXF)
msp = doc.modelspace()
for e in list(msp):
    if e.dxftype() == "IMAGE":
        msp.delete_entity(e)

fig, ax = plt.subplots(figsize=(14, 9))
ax.set_aspect("equal")
ctx = RenderContext(doc)
Frontend(ctx, MatplotlibBackend(ax)).draw_layout(msp, finalize=True)
ax.set_title("client pipeline full")
fig.savefig(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\sample_data\output\二次圈矿成果_3940_1004\client_full.png", dpi=140, facecolor="white")
plt.close(fig)

fig, ax = plt.subplots(figsize=(16, 10))
ax.set_aspect("equal")
ax.set_xlim(470080, 470150)
ax.set_ylim(4349640, 4349780)
ctx2 = RenderContext(doc)
Frontend(ctx2, MatplotlibBackend(ax)).draw_layout(msp, finalize=True)
ax.set_title("client zoom")
fig.savefig(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\sample_data\output\二次圈矿成果_3940_1004\client_zoom.png", dpi=150, facecolor="white")
plt.close(fig)
print("rendered")
