# -*- coding: utf-8 -*-
"""用 ezdxf matplotlib backend 渲染生成 DXF 预览图。"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend

DXF = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\3940平台 1004二次圈矿矿块图_3块版_full.dxf"
PNG = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\3940平台 1004二次圈矿矿块图_v3预览.png"

doc = ezdxf.readfile(DXF)
msp = doc.modelspace()
# 预览时临时移除 IMAGE（报告图单独看），不保存
for e in list(msp):
    if e.dxftype() == "IMAGE":
        msp.delete_entity(e)
fig, ax = plt.subplots(figsize=(16, 12))
ax.set_aspect("equal")
ctx = RenderContext(doc)
backend = MatplotlibBackend(ax)
Frontend(ctx, backend).draw_layout(msp, finalize=True)
ax.set_title("1004 ErCiQuanKuang v4 preview (final)")
fig.savefig(PNG, dpi=130, facecolor="white")
print("saved", PNG)
