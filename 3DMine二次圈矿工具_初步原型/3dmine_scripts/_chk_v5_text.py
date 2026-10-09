# -*- coding: utf-8 -*-
"""确认 v5 DXF 品位小字(h=0.3, CN_TTF) 与测试渲染器文字。"""
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DXF = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\3940平台 1004二次圈矿矿块图_3块版_full.dxf"
doc = ezdxf.readfile(DXF)
msp = doc.modelspace()
small = [e for e in msp if e.dxftype() == "TEXT" and abs(e.dxf.height - 0.3) < 0.01]
print("品位小字(h=0.3):", len(small))
print("样式统计:", {})
from collections import Counter
print("样式:", Counter(e.dxf.style for e in small))
print("样例:", [(e.dxf.text, e.dxf.color, e.dxf.style, (round(e.dxf.insert.x, 2), round(e.dxf.insert.y, 2))) for e in small[:6]])

# 渲染测试：只画品位文字（不含其他）
fig, ax = plt.subplots(figsize=(12, 10))
ax.set_aspect("equal")
ax.set_xlim(470095, 470099)
ax.set_ylim(4349690, 4349694)
ctx = RenderContext(doc)
from ezdxf.addons.drawing.properties import Properties
# 手动画品位文字实体
for e in small:
    p = Properties.from_entity(ctx, e)
    ax.text(e.dxf.insert.x, e.dxf.insert.y, e.dxf.text, fontsize=8, color="yellow")
ax.set_title("manual grade text plot")
fig.savefig(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\v5_manual_text.png", dpi=200, facecolor="white")
plt.close(fig)
print("saved manual text plot")
