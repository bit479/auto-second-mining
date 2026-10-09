# -*- coding: utf-8 -*-
"""局部放大渲染：炮孔十字/工程号/品位标注 + 方格中心品位文字。"""
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

fig, ax = plt.subplots(figsize=(16, 12))
ax.set_aspect("equal")
# 左下炮孔密集区（#1 区域）
ax.set_xlim(470080, 470118)
ax.set_ylim(4349645, 4349700)
ctx = RenderContext(doc)
backend = MatplotlibBackend(ax)
Frontend(ctx, backend).draw_layout(msp, finalize=True)
ax.set_title("v4 zoom #1 holes area")
fig.savefig(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\v4_zoom_holes.png", dpi=150, facecolor="white")
print("saved zoom holes")

fig2, ax2 = plt.subplots(figsize=(16, 12))
ax2.set_aspect("equal")
ax2.set_xlim(470103, 470122)
ax2.set_ylim(4349712, 4349736)
ctx2 = RenderContext(doc)
backend2 = MatplotlibBackend(ax2)
Frontend(ctx2, backend2).draw_layout(msp, finalize=True)
ax2.set_title("v4 zoom #2 holes area")
fig2.savefig(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\v4_zoom_holes2.png", dpi=150, facecolor="white")
print("saved zoom holes2")
