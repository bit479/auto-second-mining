# -*- coding: utf-8 -*-
"""v5 渲染预览：全图 + 炮孔区局部放大。"""
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

# 全图
fig, ax = plt.subplots(figsize=(14, 9))
ax.set_aspect("equal")
ctx = RenderContext(doc)
Frontend(ctx, MatplotlibBackend(ax)).draw_layout(msp, finalize=True)
ax.set_title("1004 v5 full")
fig.savefig(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\v5_full.png", dpi=140, facecolor="white")
plt.close(fig)

# 炮孔区放大（#1 左下 + #2 右上）
fig, ax = plt.subplots(figsize=(16, 10))
ax.set_aspect("equal")
ax.set_xlim(470080, 470140)
ax.set_ylim(4349640, 4349740)
ctx2 = RenderContext(doc)
Frontend(ctx2, MatplotlibBackend(ax)).draw_layout(msp, finalize=True)
ax.set_title("v5 zoom holes+blocks")
fig.savefig(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\v5_zoom.png", dpi=150, facecolor="white")
plt.close(fig)

# 品位文字放大（#3 中部网格，看小字）
fig, ax = plt.subplots(figsize=(16, 10))
ax.set_aspect("equal")
ax.set_xlim(470095, 470116)
ax.set_ylim(4349685, 4349705)
ctx3 = RenderContext(doc)
Frontend(ctx3, MatplotlibBackend(ax)).draw_layout(msp, finalize=True)
ax.set_title("v5 zoom grade text")
fig.savefig(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\v5_zoom_grade.png", dpi=150, facecolor="white")
plt.close(fig)
print("rendered v5_full / v5_zoom / v5_zoom_grade")
