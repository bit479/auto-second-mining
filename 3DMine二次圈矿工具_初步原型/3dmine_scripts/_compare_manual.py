# -*- coding: utf-8 -*-
"""人工 vs 自动化圈矿对比：边界范围/面积/品位/体积/报告。"""
import json
import ezdxf

ROOT = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型"
MANUAL = ROOT + r"\output\1004_macro\manual_1004.dxf"
DATA = json.load(open(ROOT + r"\output\1004_macro\1004_blocks.json", encoding="utf-8"))

# 人工边界（层 1.500-3.000 的 polyline = 1.5-3 块；层 0 的 29 点青 = 0.5-1 块）
doc = ezdxf.readfile(MANUAL)
msp = doc.modelspace()
manual_polys = []
for e in msp:
    if e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
        layer = e.dxf.layer
        if layer in ("1.500-3.000", "0") and len(list(e.get_points())) > 5:
            pts = [(p[0], p[1]) for p in e.get_points()]
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            manual_polys.append((layer, e.dxf.color, len(pts),
                                 (min(xs), max(xs), min(ys), max(ys))))

print("=== 人工矿块边界（DXF）===")
for p in manual_polys:
    print(f"  layer={p[0]} color={p[1]} npts={p[2]} x[{p[3][0]:.1f},{p[3][1]:.1f}] y[{p[3][2]:.1f},{p[3][3]:.1f}]")

print("\n=== 我的 v6.1 矿块 ===")
for b in DATA["blocks"]:
    rings = b.get("parts", [b["boundary"]])
    allx = [p[0] for r in rings for p in r]
    ally = [p[1] for r in rings for p in r]
    print(f"  #{b['no']} {b['grade_label']} 品位{b['avg_grade_g_t']:.3f} "
          f"面积{b['area_m2']:.1f}m2 体积{b['volume_m3']:.1f}m3 重量{b['tonnage_t']:.1f}t "
          f"金属量{b['metal_g']:.1f}g 孔数{len(b['holes'])} "
          f"x[{min(allx):.1f},{max(allx):.1f}] y[{min(ally):.1f},{max(ally):.1f}] "
          f"孔:{[h.split('-')[-1] for h in b['holes']]}")

print("\n=== 对比 ===")
print("人工: 体1 1.5-3 904.777m3/2442.898t/1.545/37.743百克; 体2 0.5-1 7799.447/20937.818/0.69186/144.861; "
      "体3 1.5-3 1142.139/3083.777/1.84796/56.987; 合计 9846.363m3/26464.493t/0.90533")
print("v6.1: #1 1.5-3 2025.9/5469.8/1.705/93.28; #2 1.5-3 841.8/2272.8/1.55/35.24; "
      "#3 0.5-1 7961.3/21495.4/0.683/146.91; 合计 10829/29238/0.942")
