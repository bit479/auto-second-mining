# -*- coding: utf-8 -*-
"""生成 VBA 友好的圈矿数据文件（1004_blocks.json -> 文本，VBA Line Input 读取）。"""
import json
from pathlib import Path

OUT = Path(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro")
data = json.load(open(OUT / "1004_blocks.json", encoding="utf-8"))
m = data["meta"]
z = m["bench_z"]
h = m["bench_height_m"]
dens = m["density_ore_t_m3"]

lines = []
lines.append("PLATFORM,%s" % m["platform"])
lines.append("DATE,%s" % m["date"])
lines.append("BENCH_Z,%.2f" % z)
lines.append("HEIGHT,%.2f" % h)
lines.append("DENSITY,%.3f" % dens)
# 炮孔
for hd in data["holes"]:
    lines.append("HOLE,%s,%.3f,%.3f,%.2f,%.3f" % (hd["id"], hd["x"], hd["y"], z, hd["grade"]))
# 矿块：边界/网格/标注/数据
for b in data["blocks"]:
    no = b["no"]
    lines.append("BLOCK,%d,%s,%.3f,%.3f" % (no, b["grade_label"], b["avg_grade_g_t"], b["area_m2"]))
    for (x, y) in b["boundary"]:
        lines.append("POLY,%d,%.3f,%.3f" % (no, x, y))
    lines.append("POLYEND,%d" % no)
    for ln in b["grid_lines"]:
        lines.append("GRID,%d,%.3f,%.3f,%.3f,%.3f" % (no, ln[0][0], ln[0][1], ln[1][0], ln[1][1]))
    lines.append("LABEL,%d,%.3f,%.3f" % (no, b["centroid"][0], b["centroid"][1]))
    vol = b["area_m2"] * h
    ton = vol * dens
    metal = b["avg_grade_g_t"] * ton
    lines.append("DATA,%d,%.3f,%.3f,%.3f,%.3f,%.3f,%d" % (
        no, b["area_m2"], vol, ton, b["avg_grade_g_t"], metal, b["cell_count"]))

f = OUT / "1004_vba_data.txt"
f.write_text("\n".join(lines), encoding="utf-8")
print("wrote", f, len(lines), "lines")
