# -*- coding: utf-8 -*-
"""检查 3 块边界是否覆盖各自包含的孔（点在多边形内测试）。"""
import json

d = json.load(open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\1004_blocks.json", encoding="utf-8"))
holes = {h["id"]: (h["x"], h["y"], h["grade"]) for h in d["holes"]}

def pip(x, y, poly):
    n = len(poly)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-30) + xi):
            inside = not inside
        j = i
    return inside

out = []
for b in d["blocks"]:
    poly = b["boundary"]
    out.append("块#%s %s 边界点=%d" % (b["no"], b["grade_label"], len(poly)))
    for hid in b["holes"]:
        x, y, g = holes[hid]
        inside = pip(x, y, poly)
        # 到边界最小距离（粗略：到边线段距离）
        import math
        mind = 1e9
        for i in range(len(poly)):
            x1, y1 = poly[i]
            x2, y2 = poly[(i + 1) % len(poly)]
            # 点到线段距离
            dx, dy = x2 - x1, y2 - y1
            L2 = dx * dx + dy * dy
            t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / L2)) if L2 > 0 else 0
            px, py = x1 + t * dx, y1 + t * dy
            dist = math.hypot(x - px, y - py)
            mind = min(mind, dist)
        out.append("   %s g=%.3f 在多边形内=%s 距边界=%.2fm" % (hid, g, inside, mind))
open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\boundary_coverage.txt", "w", encoding="utf-8").write("\n".join(out))
print("done")
