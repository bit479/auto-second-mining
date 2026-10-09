# -*- coding: utf-8 -*-
"""ezdxf 精读人工 DXF：样式字体/文字颜色高度/hatch尺寸/边界线色宽/网格线色。"""
import ezdxf
from collections import Counter

DXF = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\manual_1004.dxf"
OUT = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\manual_dxf_detail.txt"

doc = ezdxf.readfile(DXF)
msp = doc.modelspace()
L = []
L.append("=== 文字样式 ===")
for st in doc.styles:
    L.append(f"  {st.dxf.name}: font={st.dxf.font} bigfont={st.dxf.get('bigfont','')} "
             f"height={st.dxf.get('height',0)} width={st.dxf.get('width',1)}")
L.append("=== 图层 ===")
for ly in doc.layers:
    L.append(f"  {ly.dxf.name}: color={ly.dxf.color} linetype={ly.dxf.linetype} lw={ly.dxf.lineweight}")

stats = Counter()
texts = []
hatches = []
polys = []
lines = []
for e in msp:
    t = e.dxftype()
    stats[t] += 1
    if t == "TEXT":
        if len(texts) < 15:
            texts.append((e.dxf.text[:20], e.dxf.layer, e.dxf.color, e.dxf.height, e.dxf.style, tuple(e.dxf.insert)[:2]))
    elif t == "MTEXT":
        if len(texts) < 20:
            texts.append((str(e.text)[:30], e.dxf.layer, e.dxf.color, e.dxf.char_height, e.dxf.style, tuple(e.dxf.insert)[:2]))
    elif t == "HATCH":
        if len(hatches) < 8:
            try:
                ext = e.dxf.get("extents", None)
                hatches.append((e.dxf.layer, e.dxf.color, e.dxf.solid_fill, ext if ext else None))
            except Exception as ex:
                hatches.append((e.dxf.layer, e.dxf.color, "err", str(ex)))
    elif t in ("LWPOLYLINE", "POLYLINE"):
        if len(polys) < 12:
            try:
                pts = list(e.get_points())[:2]
                polys.append((e.dxf.layer, e.dxf.color, e.dxf.lineweight, len(list(e.get_points())), pts))
            except Exception as ex:
                polys.append((e.dxf.layer, e.dxf.color, "err", 0, str(ex)))
    elif t == "LINE":
        if len(lines) < 8:
            lines.append((e.dxf.layer, e.dxf.color, tuple(e.dxf.start)[:2], tuple(e.dxf.end)[:2]))

L.append("=== counts ===")
for k, v in stats.most_common():
    L.append(f"  {k}: {v}")
L.append("=== TEXT/MTEXT 抽样 ===")
for t in texts:
    L.append(f"  {t}")
L.append("=== HATCH 抽样 ===")
for h in hatches:
    L.append(f"  {h}")
L.append("=== POLYLINE 抽样 ===")
for p in polys:
    L.append(f"  {p}")
L.append("=== LINE 抽样 ===")
for ln in lines:
    L.append(f"  {ln}")

open(OUT, "w", encoding="utf-8").write("\n".join(L))
print("\n".join(L))
