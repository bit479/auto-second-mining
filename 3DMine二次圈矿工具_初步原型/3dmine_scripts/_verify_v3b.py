# -*- coding: utf-8 -*-
"""最终验证：IMAGE 尺寸 + 网格线颜色抽查。"""
import ezdxf
from collections import Counter

DXF = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\3940平台 1004二次圈矿矿块图_3块版_full.dxf"
doc = ezdxf.readfile(DXF)
msp = doc.modelspace()

for e in msp:
    if e.dxftype() == "IMAGE":
        print("IMAGE insert:", tuple(e.dxf.insert)[:2])
        print("IMAGE image_size:", tuple(e.dxf.image_size)[:2])
        print("IMAGE layer:", e.dxf.layer)

grid_colors = Counter()
hole_text = 0
for e in msp:
    if e.dxftype() == "LINE":
        grid_colors[e.dxf.color] += 1
print("LINE colors:", dict(grid_colors))
for e in msp:
    if e.dxftype() == "TEXT" and e.dxf.height == 0.8:
        hole_text += 1
print("孔号文字数:", hole_text)
