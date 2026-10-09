# -*- coding: utf-8 -*-
"""检查 blocks.json 矿块间是否重叠（交集面积/重叠率），并输出每块外环顶点步长（检测圆弧）。"""
import json, sys
from shapely.geometry import Polygon

def ring_from(part):
    return Polygon(part)

def main():
    d = json.load(open(sys.argv[1], encoding="utf-8"))
    polys = []
    for b in d["blocks"]:
        poly = None
        for part in b["parts"]:
            p = ring_from(part)
            poly = p if poly is None else poly.union(p)
        polys.append((b["no"], b["grade_label"], poly))
    # 重叠检查
    print("== 块间重叠（交集面积 > 0.01 视为重叠）==")
    any_ov = False
    for i in range(len(polys)):
        for j in range(i + 1, len(polys)):
            inter = polys[i][2].intersection(polys[j][2]).area
            if inter > 0.01:
                any_ov = True
                print(f"  #{polys[i][0]} 与 #{polys[j][0]} 重叠 {inter:.2f} m2 "
                      f"({inter/polys[i][2].area*100:.1f}% / {inter/polys[j][2].area*100:.1f}%)")
    if not any_ov:
        print("  无重叠 ✓")
    # 顶点步长检查（圆弧 = 连续密集等距点）
    print("== 边界顶点步长（米）==")
    for no, lv, poly in polys:
        for gi, part in enumerate(poly.geoms if poly.geom_type == "MultiPolygon" else [poly]):
            cs = list(part.exterior.coords)
            steps = [round(((cs[k][0]-cs[k-1][0])**2 + (cs[k][1]-cs[k-1][1])**2) ** 0.5, 2)
                     for k in range(1, len(cs))]
            small = [s for s in steps if s < 0.05]
            print(f"  #{no} ({lv}) part{gi}: {len(cs)-1} 点, 步长 {min(steps)}~{max(steps)} m, "
                  f"<0.05m 点数 {len(small)}" + ("（疑似圆弧）" if len(small) > 5 else ""))

if __name__ == "__main__":
    main()
