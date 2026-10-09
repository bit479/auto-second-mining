# -*- coding: utf-8 -*-
"""
1004 三块版成果生成：读 1004_macro/1004_blocks.json（已按用户合并规则圈连）
-> DXF 矿块图（分图层着色+矿块号） + 4 档 .str 矿界线 + 报告 xlsx/csv + 汇总文本
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from shapely.geometry import Polygon, LineString

ROOT = Path(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型")
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
OUT = ROOT / "output"

from dxf_writer import write_dxf, LAYER_LEVELS            # noqa: E402
from str_writer import write_str                           # noqa: E402

REPORT_LABEL = {"L1": "0.500-1.000", "L2": "1.000-1.500", "L3": "1.500-3.000", "L4": "3.000-999.000"}
BLOCK_ORDER = ["L4", "L3", "L2", "L1"]

data = json.load(open(OUT / "1004_macro" / "1004_blocks.json", encoding="utf-8"))
m = data["meta"]
bench_z = m["bench_z"]

blocks = []
for b in data["blocks"]:
    poly = Polygon(b["boundary"])
    blocks.append({
        "level_id": b["level"], "block_no": b["no"], "polygon": poly,
        "label": "%d\n%s g/t" % (b["no"], b["grade_label"]),
        "grade_label": b["grade_label"],
        "area_m2": b["area_m2"], "volume_m3": b["volume_m3"], "tonnage_t": b["tonnage_t"],
        "avg_grade_g_t": b["avg_grade_g_t"], "metal_g": b["metal_g"], "cell_count": b["cell_count"],
        "holes": b["holes"],
    })

grid_lines = {b["no"]: [LineString(ln) for ln in b["grid_lines"]] for b in data["blocks"]}

# 1) DXF 矿块图
dxf_path = write_dxf(
    OUT / f"{m['platform']}平台 {m['date']}二次圈矿矿块图_3块版.dxf",
    blocks=blocks, grid_lines=grid_lines,
    title=f"{m['platform']}平台 {m['date']} 二次圈矿矿块图（3块版：可采合并）",
)
print("[DXF]", dxf_path.name)

# 2) 4 档 .str（每档一个矿界线文件；本数据 L4/L2 无独立块）
for lv in ["L1", "L2", "L3", "L4"]:
    bs = [b for b in blocks if b["level_id"] == lv]
    if not bs:
        continue
    polys = [np.asarray(b["polygon"].exterior.coords) for b in bs]
    code = {lv: i for i, lv in enumerate(["L1", "L2", "L3", "L4"], 1)}[lv]
    fname = f"{m['blast_id']}_{lv}_grade.str"
    write_str(polys, OUT / "1004_macro" / fname, bench_z=bench_z, code=code)
    print("[STR]", fname, "(%d 条闭合界线)" % len(polys))

# 3) 报告（对齐人工版式）
rows = []
for lv in BLOCK_ORDER:
    bs = [b for b in blocks if b["level_id"] == lv]
    if not bs:
        continue
    for b in bs:
        rows.append({"类型": REPORT_LABEL[lv], "体号": b["block_no"], "体积": round(b["volume_m3"], 3),
                     "重量（t）": round(b["tonnage_t"], 3), "平均品位(Au)": round(b["avg_grade_g_t"], 3),
                     "金属量（百克）": round(b["metal_g"] / 100.0, 3)})
    st = sum(b["tonnage_t"] for b in bs)
    sm = sum(b["metal_g"] for b in bs)
    rows.append({"类型": "小计", "体号": None, "体积": round(sum(b["volume_m3"] for b in bs), 3),
                 "重量（t）": round(st, 3), "平均品位(Au)": round(sm / st, 3),
                 "金属量（百克）": round(sm / 100.0, 3)})
t_all = sum(b["tonnage_t"] for b in blocks)
m_all = sum(b["metal_g"] for b in blocks)
rows.append({"类型": "合计", "体号": None, "体积": round(sum(b["volume_m3"] for b in blocks), 3),
             "重量（t）": round(t_all, 3), "平均品位(Au)": round(m_all / t_all, 3),
             "金属量（百克）": round(m_all / 100.0, 3)})

pd.DataFrame(rows).to_csv(OUT / "1004_macro" / "3940平台 1004炮孔数据报告_3块版.csv",
                          index=False, encoding="utf-8-sig")
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
wb = Workbook()
ws = wb.active
ws.title = "Sheet1"
ws.append([f"{m['platform']}平台 {m['date']}炮孔数据报告（3块版）"])
ws["A1"].font = Font(bold=True, size=14)
ws.append(["类型", "体号", "体积", "重量（t）", "平均品位(Au)", "金属量（百克）"])
for r in rows:
    ws.append([r["类型"], r["体号"], r["体积"], r["重量（t）"], r["平均品位(Au)"], r["金属量（百克）"]])
for row in ws.iter_rows(min_row=2):
    for cell in row:
        cell.alignment = Alignment(horizontal="center")
xlsx_path = OUT / "1004_macro" / "3940平台 1004炮孔数据报告_3块版.xlsx"
wb.save(str(xlsx_path))
print("[XLSX]", xlsx_path.name)

# 4) 汇总文本（粘贴 CAD 用）
lines = [f"{'体号':<6}{'品位类型':<14}{'面积m2':>8}{'体积m3':>10}"
         f"{'重量t':>10}{'平均品位g/t':>12}{'金属量g':>10}  炮孔数  炮孔号"]
for b in blocks:
    holes_s = "、".join(h.split("-")[-1] for h in b["holes"])
    lines.append(f"#{b['block_no']:<5}{b['grade_label']:<14}{b['area_m2']:>8.0f}"
                 f"{b['volume_m3']:>10.0f}{b['tonnage_t']:>10.0f}{b['avg_grade_g_t']:>12.3f}"
                 f"{b['metal_g']:>10.0f}  {b['cell_count']:<6}{holes_s}")
(OUT / "1004_macro" / "3940平台 1004矿块汇总（粘贴CAD）_3块版.txt").write_text(
    "\n".join(lines), encoding="utf-8")
print("[TXT] 矿块汇总已输出")

# 5) 验证图（3 块 + 炮孔品位 + 网格示意）
from matplotlib import pyplot as plt
from matplotlib.patches import Polygon as MplPolygon
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False
color_plot = {"L1": "cyan", "L2": "blue", "L3": "red", "L4": "yellow"}
fig, ax = plt.subplots(figsize=(12, 9.5))
for b in blocks:
    ext = np.asarray(b["polygon"].exterior.coords)
    ax.add_patch(MplPolygon(ext, closed=True, facecolor=color_plot[b["level_id"]],
                            edgecolor="black", lw=1.8, alpha=0.6))
    cx, cy = b["polygon"].representative_point().coords[0]
    ax.text(cx, cy, f"#{b['block_no']}\n{b['avg_grade_g_t']:.3f} g/t", fontsize=10,
            ha="center", va="center", fontweight="bold",
            bbox=dict(facecolor="white", alpha=0.85, edgecolor="none", pad=1.0))
for h in data["holes"]:
    ax.plot(h["x"], h["y"], "k.", ms=4)
    ax.text(h["x"] + 1.5, h["y"] + 1.5, f"{h['grade']:.2f}", fontsize=6.5, color="dimgray")
# 矿块1 网格示意
b0 = data["blocks"][0]
for ln in b0["grid_lines"][:0]:
    pass
ax.set_title(f"{m['platform']}平台 {m['date']} 二次圈矿 3块版（用户合并规则）", fontsize=13)
ax.set_aspect("equal")
fig.tight_layout()
png = OUT / "1004_macro" / "3940平台 1004二次圈矿验证图_3块版_v6.png"
fig.savefig(png, dpi=150)
plt.close(fig)
print("[PNG]", png.name)
print("ALL DONE")
