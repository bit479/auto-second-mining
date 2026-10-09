# -*- coding: utf-8 -*-
import json

data = json.load(open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\1004_blocks.json", encoding="utf-8"))
for b in data["blocks"]:
    tv, tf = b["tri_verts"], b["tri_faces"]
    ta = 0.0
    for f in tf:
        a, bb, c = tv[f[0]], tv[f[1]], tv[f[2]]
        ta += abs((bb[0] - a[0]) * (c[1] - a[1]) - (bb[1] - a[1]) * (c[0] - a[0])) / 2.0
    print("block", b["no"], b["grade_label"], "verts=%d faces=%d area=%.1f tri_area=%.1f diff=%.2f%% grid=%d"
          % (len(tv), len(tf), b["area_m2"], ta, abs(ta - b["area_m2"]) / b["area_m2"] * 100, len(b["grid_lines"])))
