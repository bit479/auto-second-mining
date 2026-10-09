# -*- coding: utf-8 -*-
"""精读人工 DXF 炮孔标注：color=138 的 TEXT 内容/位置/高度/样式 + 是否有十字线。"""
import ezdxf

DXF = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\manual_1004.dxf"
doc = ezdxf.readfile(DXF)
msp = doc.modelspace()

out = []
out.append("=== 炮孔标注 TEXT（color=138 及其他非常规色）===")
n = 0
for e in msp:
    if e.dxftype() == "TEXT" and e.dxf.color == 138:
        n += 1
        out.append(f"  [{n}] '{e.dxf.text[:40]}' color={e.dxf.color} h={e.dxf.height:.3f} "
                   f"style={e.dxf.style} pos=({e.dxf.insert[0]:.3f},{e.dxf.insert[1]:.3f})")
out.append(f"共 {n} 个 color=138 文字")
out.append("")
out.append("=== 黄色(2)/蓝色(5) TEXT（≥3/1-1.5 品位）===")
for e in msp:
    if e.dxftype() == "TEXT" and e.dxf.color in (2, 5):
        out.append(f"  '{e.dxf.text[:40]}' color={e.dxf.color} h={e.dxf.height:.3f} "
                   f"pos=({e.dxf.insert[0]:.3f},{e.dxf.insert[1]:.3f})")
out.append("")
out.append("=== 红色(1) TEXT 位置分布（前 12 个）===")
k = 0
for e in msp:
    if e.dxftype() == "TEXT" and e.dxf.color == 1:
        k += 1
        if k <= 12:
            out.append(f"  '{e.dxf.text[:20]}' h={e.dxf.height:.3f} "
                       f"pos=({e.dxf.insert[0]:.3f},{e.dxf.insert[1]:.3f})")
out.append("")
out.append("=== 十字线检测：短 LINE（长度<5m）===")
short_lines = 0
for e in msp:
    if e.dxftype() == "LINE":
        dx = e.dxf.end[0] - e.dxf.start[0]
        dy = e.dxf.end[1] - e.dxf.start[1]
        length = (dx * dx + dy * dy) ** 0.5
        if length < 5:
            short_lines += 1
            if short_lines <= 12:
                out.append(f"  LINE len={length:.2f} ({e.dxf.start[0]:.2f},{e.dxf.start[1]:.2f})->"
                           f"({e.dxf.end[0]:.2f},{e.dxf.end[1]:.2f}) color={e.dxf.color}")
out.append(f"短 LINE 总数: {short_lines}")
open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\manual_hole_annot.txt", "w", encoding="utf-8").write("\n".join(out))
print("\n".join(out))
