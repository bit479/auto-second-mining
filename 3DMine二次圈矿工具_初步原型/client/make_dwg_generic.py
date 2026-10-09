# -*- coding: utf-8 -*-
"""Step2 通用成果图生成器（参数化）：
用法: python make_dwg_generic.py <blocks_json> [out_dir]
  blocks_json : Step1 产出的 <blast_id>_blocks.json
  out_dir     : 输出目录，缺省 = json 同级
产出: DXF 成果图（炮孔十字+水平引线+完整工程号+分级色品位、方格中心品位、彩色矿块、矿块号引出线、报告图片）
      <blast_id>_炮孔数据报告.png / .xlsx、<blast_id>_矿块边界线.3ds
"""
from __future__ import annotations
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型")
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from mdb_loader import load_xls_blast                       # noqa: E402
from voronoi import build_voronoi_cells                     # noqa: E402

REPORT_LABEL = {"L1": "0.500-1.000", "L2": "1.000-1.500", "L3": "1.500-3.000", "L4": "3.000-999.000"}
GRADE_COLOR = {"L1": 4, "L2": 5, "L3": 1, "L4": 2}
HOLE_ACI = {0: 8, 1: 4, 2: 5, 3: 1, 4: 2}
LAYER_BY_LV = {"L1": "0.500-1.000", "L2": "1.000-1.500", "L3": "1.500-3.000", "L4": "3.000-999.000"}
LAYER_GRID = "爆区方格网"
LAYER_HOLES = "钻孔"
LAYER_MISC = "线条"
LAYER_DOTS = "点"
LAYER_REPORT = "报告"


def grade_level(g):
    if g >= 3.0:
        return "L4"
    if g >= 1.5:
        return "L3"
    if g >= 1.0:
        return "L2"
    if g >= 0.5:
        return "L1"
    return "W"


def lv_index(lv):
    return {"L1": 1, "L2": 2, "L3": 3, "L4": 4}.get(lv, 0)


def load_data(blocks_json):
    data = json.load(open(blocks_json, encoding="utf-8"))
    return data


def _pip(x, y, poly):
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


def _pip_multi(x, y, rings):
    return any(_pip(x, y, ring) for ring in rings)


def _nearest_on_poly(poly, tx, ty):
    best = None
    best_d = float("inf")
    n = len(poly)
    for i in range(n):
        p1 = poly[i]
        p2 = poly[(i + 1) % n]
        ax, ay = p1
        bx, by = p2
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 < 1e-12 else ((tx - ax) * dx + (ty - ay) * dy) / L2
        t = max(0.0, min(1.0, t))
        px, py = ax + t * dx, ay + t * dy
        d = (px - tx) ** 2 + (py - ty) ** 2
        if d < best_d:
            best_d = d
            best = (px, py)
    return best


def compute_label_targets(blocks):
    """矿块号文字位置：沿"全局中心→矿块质心"方向外推（矿块半径+30m），动态通用。"""
    all_x = [p[0] for b in blocks for ring in b["parts"] for p in ring]
    all_y = [p[1] for b in blocks for ring in b["parts"] for p in ring]
    if not all_x:
        return {}
    gcx = sum(all_x) / len(all_x)
    gcy = sum(all_y) / len(all_y)
    targets = {}
    for b in blocks:
        c = b["centroid"]
        ring = b["parts"][0]
        xs = [p[0] for p in ring]
        ys = [p[1] for p in ring]
        rx = max(max(xs) - c[0], c[0] - min(xs))
        ry = max(max(ys) - c[1], c[1] - min(ys))
        dist = math.hypot(rx, ry) + 30.0
        dx, dy = c[0] - gcx, c[1] - gcy
        if math.hypot(dx, dy) < 1e-9:
            dx, dy = 1.0, 0.0
        ux, uy = dx / math.hypot(dx, dy), dy / math.hypot(dx, dy)
        targets[b["no"]] = (c[0] + ux * dist, c[1] + uy * dist)
    return targets


def make_report_png(data, report_png, report_xlsx):
    from matplotlib import pyplot as plt
    import matplotlib
    matplotlib.use("Agg")
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
    plt.rcParams["axes.unicode_minus"] = False
    m = data["meta"]
    rows = [["类型", "体号", "体积m3", "重量t", "平均品位", "金属量百克"]]
    for lv in ["L4", "L3", "L2", "L1"]:
        bs = [b for b in data["blocks"] if b["level"] == lv]
        if not bs:
            continue
        for b in bs:
            rows.append([REPORT_LABEL[lv], b["no"], round(b["volume_m3"], 1), round(b["tonnage_t"], 1),
                         round(b["avg_grade_g_t"], 3), round(b["metal_g"] / 100.0, 2)])
        st = sum(b["tonnage_t"] for b in bs)
        sm = sum(b["metal_g"] for b in bs)
        rows.append(["小计", "", round(sum(b["volume_m3"] for b in bs), 1), round(st, 1),
                     round(sm / st, 3), round(sm / 100.0, 2)])
    t_all = sum(b["tonnage_t"] for b in data["blocks"])
    m_all = sum(b["metal_g"] for b in data["blocks"])
    rows.append(["合计", "", round(sum(b["volume_m3"] for b in data["blocks"]), 1), round(t_all, 1),
                 round(m_all / t_all, 3), round(m_all / 100.0, 2)])
    grades = [h["grade"] for h in data["holes"]]
    stat_lines = [
        f"{m['platform']}平台 {m['date']} 炮孔统计（{len(grades)}孔）：",
        f">=3: {sum(1 for g in grades if g>=3)}   1.5-3: {sum(1 for g in grades if 1.5<=g<3)}   "
        f"1-1.5: {sum(1 for g in grades if 1<=g<1.5)}   "
        f"0.5-1: {sum(1 for g in grades if 0.5<=g<1)}   <0.5: {sum(1 for g in grades if g<0.5)}",
    ]
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.axis("off")
    tbl = ax.table(cellText=rows, loc="center", cellLoc="center")
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(11)
    tbl.scale(1.25, 1.5)
    for (r, c), cell in tbl.get_celld().items():
        if r == 0:
            cell.set_facecolor("#4472C4")
            cell.set_text_props(color="white", weight="bold")
        elif rows[r] and rows[r][0] in ("小计", "合计"):
            cell.set_facecolor("#D9E2F3")
    ax.text(0.02, 0.03, "\n".join(stat_lines), transform=ax.transAxes, fontsize=10,
            ha="left", va="bottom")
    fig.tight_layout()
    fig.savefig(report_png, dpi=150, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print("[报告PNG]", report_png)
    try:
        import pandas as pd
        out_rows = []
        for lv in ["L4", "L3", "L2", "L1"]:
            bs = [b for b in data["blocks"] if b["level"] == lv]
            if not bs:
                continue
            for b in bs:
                out_rows.append({"类型": REPORT_LABEL[lv], "体号": b["no"],
                                 "体积(m3)": round(b["volume_m3"], 1),
                                 "重量(t)": round(b["tonnage_t"], 1),
                                 "平均品位(g/t)": round(b["avg_grade_g_t"], 3),
                                 "金属量(百克)": round(b["metal_g"] / 100.0, 2)})
            st = sum(b["tonnage_t"] for b in bs)
            sm = sum(b["metal_g"] for b in bs)
            out_rows.append({"类型": "小计", "体号": "",
                             "体积(m3)": round(sum(b["volume_m3"] for b in bs), 1),
                             "重量(t)": round(st, 1), "平均品位(g/t)": round(sm / st, 3),
                             "金属量(百克)": round(sm / 100.0, 2)})
        out_rows.append({"类型": "合计", "体号": "",
                         "体积(m3)": round(sum(b["volume_m3"] for b in data["blocks"]), 1),
                         "重量(t)": round(t_all, 1), "平均品位(g/t)": round(m_all / t_all, 3),
                         "金属量(百克)": round(m_all / 100.0, 2)})
        pd.DataFrame(out_rows).to_excel(report_xlsx, index=False)
        print("[报告XLSX]", report_xlsx)
    except Exception as ex:
        print("[报告XLSX] 跳过:", ex)


def build_dxf(data, dxf_path):
    from ezdxf import new
    doc = new("R2010")
    doc.header["$INSUNITS"] = 6
    for lv, lname in LAYER_BY_LV.items():
        doc.layers.add(lname, color=GRADE_COLOR[lv])
    for ln in [LAYER_GRID, LAYER_HOLES, LAYER_MISC, LAYER_DOTS, LAYER_REPORT]:
        doc.layers.add(ln, color=7)
    cn_style = doc.styles.add("CN_SHX", font="txt.shx")
    cn_style.dxf.bigfont = "gbcbig.shx"
    simsun = doc.styles.add("CN_TTF", font="simsunb.ttf")
    msp = doc.modelspace()

    xs = [h["x"] for h in data["holes"]]
    ys = [h["y"] for h in data["holes"]]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)

    # 矿块边界（彩色闭合线，无填充）
    for b in data["blocks"]:
        lname = LAYER_BY_LV[b["level"]]
        aci = GRADE_COLOR[b["level"]]
        for ring in b["parts"]:
            msp.add_lwpolyline([(p[0], p[1]) for p in ring], close=True,
                               dxfattribs={"layer": lname, "color": aci, "lineweight": 30})

    # 网格线
    for b in data["blocks"]:
        aci = GRADE_COLOR[b["level"]]
        for ln in b["grid_lines"]:
            msp.add_line((ln[0][0], ln[0][1]), (ln[1][0], ln[1][1]),
                         dxfattribs={"layer": LAYER_GRID, "color": aci})

    # 网格品位文字：方格中心 h=0.3 分级色（TTF 保证渲染/CAD 均可见）
    grade_by_xy = {}
    for h in data["holes"]:
        grade_by_xy[(round(h["x"], 3), round(h["y"], 3))] = h["grade"]
    cells = None
    try:
        comp = load_xls_blast(Path(data["meta"].get("_xls", ""))) if data["meta"].get("_xls") else None
    except Exception:
        comp = None
    if comp is not None:
        cells = build_voronoi_cells(comp["X"].to_numpy(float), comp["Y"].to_numpy(float),
                                    comp["Grade"].to_numpy(float), comp["Hole_ID"].tolist())

    def grade_at(x, y, rings):
        if cells is not None:
            for c in cells:
                if _pip(x, y, list(c.polygon.exterior.coords)):
                    return c.grade
            return None
        # 无 xls 时用孔品位近似（中心点落在孔单元内则用最近孔品位）
        best = None
        best_d = 1e18
        for h in data["holes"]:
            d = (h["x"] - x) ** 2 + (h["y"] - y) ** 2
            if d < best_d:
                best_d = d
                best = h["grade"]
        return best

    for b in data["blocks"]:
        aci = GRADE_COLOR[b["level"]]
        rings = b["parts"]
        x0 = min(p[0] for ring in rings for p in ring)
        x1 = max(p[0] for ring in rings for p in ring)
        y0 = min(p[1] for ring in rings for p in ring)
        y1 = max(p[1] for ring in rings for p in ring)
        cxs = np.arange(np.floor(x0) + 0.5, x1, 1.0)
        cys = np.arange(np.floor(y0) + 0.5, y1, 1.0)
        n_txt = 0
        for cx in cxs:
            for cy in cys:
                if _pip_multi(cx, cy, rings):
                    g = grade_at(cx, cy, rings)
                    if g is not None:
                        msp.add_text(f"{g:.2f}",
                                     dxfattribs={"layer": LAYER_DOTS, "color": aci,
                                                 "height": 0.3, "style": "CN_TTF"},
                                     ).set_placement((cx, cy))
                        n_txt += 1
        print(f"[品位文字] 块#{b['no']}: {n_txt} 个（方格中心 color={aci} h=0.3）")

    # 炮孔：十字 + 水平引线（横线，向右 5m）+ 完整工程号 + 品位大字（分级色）
    for h in data["holes"]:
        cx, cy = h["x"], h["y"]
        lv = grade_level(h["grade"])
        aci = HOLE_ACI.get(lv_index(lv), 8)
        arm = 0.8
        msp.add_line((cx - arm, cy), (cx + arm, cy), dxfattribs={"layer": LAYER_HOLES, "color": aci})
        msp.add_line((cx, cy - arm), (cx, cy + arm), dxfattribs={"layer": LAYER_HOLES, "color": aci})
        ex = cx + 5.0
        ey = cy
        msp.add_line((cx, cy), (ex, ey), dxfattribs={"layer": LAYER_HOLES, "color": aci})
        msp.add_text(h["id"],
                     dxfattribs={"layer": LAYER_HOLES, "color": 138, "height": 0.4,
                                 "style": "CN_TTF"},
                     ).set_placement((ex + 0.4, ey))
        msp.add_text(f"{h['grade']:.2f}",
                     dxfattribs={"layer": LAYER_HOLES, "color": aci, "height": 0.7,
                                 "style": "CN_TTF"},
                     ).set_placement((ex + 0.4, ey + 1.0))

    # 矿块号：引线起点取各自矿块边界最近点，文字动态外推
    targets = compute_label_targets(data["blocks"])
    for b in data["blocks"]:
        no = b["no"]
        rings = b["parts"]
        tx, ty = targets.get(no, b["centroid"])
        best = None
        best_d = float("inf")
        for ring in rings:
            pt = _nearest_on_poly(ring, tx, ty)
            if pt:
                d = (pt[0] - tx) ** 2 + (pt[1] - ty) ** 2
                if d < best_d:
                    best_d = d
                    best = pt
        fromx, fromy = best if best else b["centroid"]
        msp.add_mtext(f"{no}号矿块", dxfattribs={"layer": LAYER_MISC, "style": "CN_SHX",
                                                "char_height": 4.0}).set_location((tx, ty))
        msp.add_line((fromx, fromy), (tx, ty), dxfattribs={"layer": LAYER_MISC, "color": 7})
        print(f"[矿块号] #{no}: 引线 ({fromx:.2f},{fromy:.2f}) -> ({tx:.2f},{ty:.2f})")

    doc.saveas(dxf_path)
    print("[DXF]", dxf_path)


def write_3ds(data, threeds):
    m = data["meta"]
    bench_z = m["bench_z"]
    # 对齐 3DMine 人工选择集 .3ds 结构：文件头 → 对象头(品位档+矿块号) → 平面边界环(Z=0)
    # → 环结束行 → 顶面环(Z=平台标高) → 对象结束行
    lines = [f"{threeds}, 3DMine String File", "file_version=3DMine_2009"]
    for b in data["blocks"]:
        lines += [f"1,7,0,1.00,1.00,1.00,0,0.5,0,Continuous,{b['grade_label']}",
                  f"2,7,0,1.00,1.00,1.00,0,0.5,0,Continuous,{b['no']}",
                  "0,0,0,0,0,0,0,0,"]
        for ring in b["parts"]:
            # 平面边界环（Z=0）
            for p in ring:
                lines.append(f"1,{p[1]:.6f},{p[0]:.6f},0.000000,")
            p0 = ring[0]
            lines.append(f"1,{p0[1]:.6f},{p0[0]:.6f},0.000000,")
            # 环结束（续下一个环）
            lines.append("0,0.000000,0.000000,0.000000,0,,1.000000,0.000000,0.000000,1.000000,1.000000")
            # 顶面环（Z=平台标高，与平面同 XY）
            for p in ring:
                lines.append(f"2,{p[1]:.6f},{p[0]:.6f},{bench_z:.6f},")
            p0 = ring[0]
            lines.append(f"2,{p0[1]:.6f},{p0[0]:.6f},{bench_z:.6f},")
            # 对象结束（-1）
            lines.append("0,0.000000,0.000000,0.000000,-1,,1.000000,0.000000,-1.000000,-1.000000,-1.000000")
        lines.append("")
    threeds.write_text("\n".join(lines), encoding="gbk")
    print("[3DS]", threeds)


def main():
    blocks_json = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\sample_data\output\1004_macro\1004_blocks.json")
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else blocks_json.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    data = load_data(blocks_json)
    blast_id = data["meta"]["blast_id"]
    dxf_path = out_dir / f"{blast_id}_二次圈矿矿块图_full.dxf"
    report_png = out_dir / f"{blast_id}_炮孔数据报告.png"
    report_xlsx = out_dir / f"{blast_id}_炮孔数据报告.xlsx"
    threeds = out_dir / f"{blast_id}_矿块边界线.3ds"
    print(f"[Step2] blocks: {blocks_json}")
    make_report_png(data, report_png, report_xlsx)
    build_dxf(data, dxf_path)
    write_3ds(data, threeds)
    print("[Step2] 完成（DWG 由 Step3 转换）")


if __name__ == "__main__":
    main()
