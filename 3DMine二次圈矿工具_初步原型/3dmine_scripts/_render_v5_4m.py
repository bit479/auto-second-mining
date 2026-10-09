# -*- coding: utf-8 -*-
"""v5 超放大：4m 范围看品位小字。"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend

DXF = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\3940平台 1004二次圈矿矿块图_3块版_full.dxf"
doc = ezdxf.readfile(DXF)
msp = doc.modelspace()
for e in list(msp):
    if e.dxftype() == "IMAGE":
        msp.delete_entity(e)

fig, ax = plt.subplots(figsize=(12, 10))
ax.set_aspect("equal")
ax.set_xlim(470095, 470099)
ax.set_ylim(4349690, 4349694)
ctx = RenderContext(doc)
Frontend(ctx, MatplotlibBackend(ax)).draw_layout(msp, finalize=True)
ax.set_title("v5 4m zoom: grade text in cells")
fig.savefig(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\v5_zoom_4m.png", dpi=200, facecolor="white")
plt.close(fig)
print("saved v5_zoom_4m")
