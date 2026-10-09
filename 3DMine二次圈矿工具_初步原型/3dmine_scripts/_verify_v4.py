# -*- coding: utf-8 -*-
"""v4 实体验证：十字线/工程号/品位大字/方格中心/矿块号引线。"""
import ezdxf
from collections import Counter

DXF = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\3940平台 1004二次圈矿矿块图_3块版_full.dxf"
doc = ezdxf.readfile(DXF)
msp = doc.modelspace()

out = []
stats = Counter()
for e in msp:
    stats[e.dxftype()] += 1
out.append(f"实体统计: {dict(stats)}")

# 工程号（完整 ID）
ids = [e.dxf.text for e in msp if e.dxftype() == "TEXT" and e.dxf.text.startswith("BS-3940")]
out.append(f"完整工程号 TEXT: {len(ids)} 个")
out.append(f"  样例: {ids[:3]}")

# 品位大字 h=0.7
big = [(e.dxf.text, e.dxf.color, e.dxf.height) for e in msp
       if e.dxftype() == "TEXT" and abs(e.dxf.height - 0.7) < 0.01]
out.append(f"品位大字 h=0.7: {len(big)} 个  颜色分布: {Counter(c for _, c, _ in big)}")
out.append(f"  样例: {big[:6]}")

# 品位文字（h=0.2）位置：应接近整数+0.5（方格中心）
small = [(e.dxf.text, e.dxf.color, round(e.dxf.insert[0], 3), round(e.dxf.insert[1], 3)) for e in msp
         if e.dxftype() == "TEXT" and abs(e.dxf.height - 0.2) < 0.01]
out.append(f"品位小字 h=0.2: {len(small)} 个")
out.append(f"  样例位置: {small[:5]}")
# 检查是否在 0.5 网格上
on_center = sum(1 for t, c, x, y in small if abs(x - round(x)) < 0.01 and abs(y - round(y)) < 0.01)
frac = sum(1 for t, c, x, y in small if abs(x - round(x) - 0.5) < 0.01 and abs(y - round(y) - 0.5) < 0.01)
out.append(f"  在整数线上: {on_center}  在方格中心(.5): {frac}")

# 十字线：钻孔层 LINE（十字2 + 引出线1 = 93）
hole_lines = [e for e in msp if e.dxftype() == "LINE" and e.dxf.layer == "钻孔"]
out.append(f"钻孔层 LINE: {len(hole_lines)}（31孔×3=93）")
# 矿块号引线（线条层 LINE = 3）
lead = [e for e in msp if e.dxftype() == "LINE" and e.dxf.layer == "线条"]
out.append(f"矿块号引线（线条层）: {len(lead)}")
for e in lead:
    out.append(f"  {tuple(e.dxf.start)[:2]} -> {tuple(e.dxf.end)[:2]}")

print("\n".join(out))
open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\verify_v4.txt", "w", encoding="utf-8").write("\n".join(out))
