# -*- coding: utf-8 -*-
"""检查 blocks json 各矿块 parts 环数与孔位/工程号。"""
import json

DATA = json.load(open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\1004_blocks.json", encoding="utf-8"))
for b in DATA["blocks"]:
    parts = b.get("parts", [b["boundary"]])
    print(f"块#{b['no']} {b['grade_label']}: parts={len(parts)} 环")
    for i, ring in enumerate(parts):
        print(f"  环{i}: {len(ring)} 点 x[{min(p[0] for p in ring):.1f},{max(p[0] for p in ring):.1f}] "
              f"y[{min(p[1] for p in ring):.1f},{max(p[1] for p in ring):.1f}]")
    print(f"  孔: {b['holes']}")
print("\n=== holes ===")
for h in DATA["holes"]:
    print(f"  {h['id']}: x={h['x']:.2f} y={h['y']:.2f} grade={h['grade']:.3f}")
