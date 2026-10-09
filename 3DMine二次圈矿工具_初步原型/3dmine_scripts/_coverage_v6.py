# -*- coding: utf-8 -*-
"""v6 边界覆盖验证：每个块的所有孔必须在块内。"""
import json, math

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
    parts = b.get("parts", [b["boundary"]])
    n_parts = len(parts)
    out.append("块#%s %s 部件数=%d 面积=%.0f 品位=%.3f" % (b["no"], b["grade_label"], n_parts, b["area_m2"], b["avg_grade_g_t"]))
    for hid in b["holes"]:
        x, y, g = holes[hid]
        in_any = any(pip(x, y, p) for p in parts)
        # 距块边界最小距离（全部件）
        mind = 1e9
        for p in parts:
            for i in range(len(p)):
                x1, y1 = p[i]
                x2, y2 = p[(i + 1) % len(p)]
                dx, dy = x2 - x1, y2 - y1
                L2 = dx * dx + dy * dy
                t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / L2)) if L2 > 0 else 0
                px, py = x1 + t * dx, y1 + t * dy
                mind = min(mind, math.hypot(x - px, y - py))
        flag = "OK" if in_any else "!!OUT!!"
        out.append("   %s g=%.3f %s (距边界 %.1fm)" % (hid, g, flag, mind))
# 全部 23 矿孔都在块内？
all_in = set()
for b in d["blocks"]:
    for hid in b["holes"]:
        all_in.add(hid)
out.append("")
out.append("入块孔数=%d" % len(all_in))
for h in d["holes"]:
    if h["grade"] >= 0.5 and h["id"] not in all_in:
        out.append("  MISSING: %s g=%.3f" % (h["id"], h["grade"]))
out.append("全部≥0.5孔已入块: %s" % (len(all_in) == 23))
open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\coverage_v6.txt", "w", encoding="utf-8").write("\n".join(out))
print("done")
