# -*- coding: utf-8 -*-
"""验证 v3 DXF：炮孔 hatch/品位文字/矿块边界/样式/图片/引出线。"""
import ezdxf
from collections import Counter

DXF = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\3940平台 1004二次圈矿矿块图_3块版_full.dxf"
doc = ezdxf.readfile(DXF)
msp = doc.modelspace()

out = []
stats = Counter()
hatch_colors = Counter()
text_colors = Counter()
text_heights = Counter()
grid_colors = Counter()
for e in msp:
    t = e.dxftype()
    stats[t] += 1
    if t == "HATCH":
        hatch_colors[e.dxf.color] += 1
    elif t == "TEXT":
        text_colors[e.dxf.color] += 1
        text_heights[round(e.dxf.height, 3)] += 1
    elif t == "LINE":
        pass
    elif t in ("LWPOLYLINE", "POLYLINE") and e.dxf.layer == "爆区方格网":
        grid_colors[e.dxf.color] += 1
out.append("== 实体统计 ==")
for k, v in stats.most_common():
    out.append(f"  {k}: {v}")
out.append(f"== HATCH 颜色分布（炮孔品位色）== {dict(hatch_colors)}")
out.append(f"== TEXT 颜色分布（品位文字色）== {dict(text_colors)}")
out.append(f"== TEXT 高度分布 == {dict(text_heights)}")
out.append(f"== 网格线颜色分布 == {dict(grid_colors)}")
out.append("== 样式 ==")
for st in doc.styles:
    out.append(f"  {st.dxf.name}: font={st.dxf.font} bigfont={st.dxf.get('bigfont','')}")
out.append("== 矿块边界图层 ==")
for e in msp:
    if e.dxftype() in ("LWPOLYLINE", "POLYLINE") and e.dxf.layer in ("1.500-3.000", "0.500-1.000"):
        out.append(f"  layer={e.dxf.layer} color={e.dxf.color} npts={len(list(e.get_points()))}")
        break
out.append("== 矿块号 MTEXT + 引出线 LINE ==")
for e in msp:
    if e.dxftype() == "MTEXT":
        out.append(f"  MTEXT: {str(e.text)[:15]} at {tuple(e.dxf.insert)[:2]}")
for e in msp:
    if e.dxftype() == "LINE":
        out.append(f"  LINE: {tuple(e.dxf.start)[:2]} -> {tuple(e.dxf.end)[:2]}")
out.append("== 图片 ==")
for e in msp:
    if e.dxftype() == "IMAGE":
        out.append(f"  IMAGE at {tuple(e.dxf.insert)[:2]}, size={tuple(e.dxf.image_size)}")
out.append("== 标题 ==")
for e in msp:
    if e.dxftype() == "TEXT" and "二次圈矿" in e.dxf.text:
        out.append(f"  {e.dxf.text}")
print("\n".join(out))
open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\verify_v3.txt", "w", encoding="utf-8").write("\n".join(out))
