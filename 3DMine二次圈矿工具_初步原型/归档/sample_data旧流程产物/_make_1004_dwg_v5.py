# -*- coding: utf-8 -*-
"""
1004 成果 DWG 生成器 v5（修正 3 点）：
1) 炮孔引线：从孔位中心 45° 斜向延伸 5m（明显斜线），工程号+品位大字放末端
2) 矿块号：引线起点严格取各自矿块边界上离文字最近的点，文字贴近矿块，杜绝跨块混淆
3) 品位小字：h=0.3 方格中心分级色（更清晰可见）
输出：DXF + .3ds + 报告PNG
"""
from __future__ import annotations
import json, sys, math
from pathlib import Path

import numpy as np

ROOT = Path(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型")
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
OUT = ROOT / "output"

from mdb_loader import load_xls_blast                       # noqa: E402
from voronoi import build_voronoi_cells                     # noqa: E402

XLS = Path(r"D:\WK\N CRT\北部山头3940平台2026\7、单日数据\北部山头3940平台-1004\1、3940平台 炮孔数据库1004.xls")
MACRO = OUT / "1004_macro"
DXF = MACRO / "3940平台 1004二次圈矿矿块图_3块版_full.dxf"
REPORT_PNG = MACRO / "1004炮孔数据报告_v5.png"
THREEDS = MACRO / "3940平台 1004矿块边界线.3ds"

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


def load_data():
    data = json.load(open(MACRO / "1004_blocks.json", encoding="utf-8"))
    comp = load_xls_blast(XLS)
    cells_all = build_voronoi_cells(comp["X"].to_numpy(float), comp["Y"].to_numpy(float),
                                    comp["Grade"].to_numpy(float), comp["Hole_ID"].tolist())
    return data, comp, cells_all


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


def _grade_at(x, y, cells_all):
    for c in cells_all:
        if _pip(x, y, list(c.polygon.exterior.coords)):
            return c.grade
    return None


def _pip_multi(x, y, rings):
    return any(_pip(x, y, ring) for ring in rings)


def _nearest_on_poly(poly, tx, ty):
    """返回多边形边界上离 (tx,ty) 最近的点。"""
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


def make_report_png(data):
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
    fig.savefig(REPORT_PNG, dpi=150, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print("[报告PNG]", REPORT_PNG)


def build_dxf(data, comp, cells_all):
    from ezdxf import new
    doc = new("R2010")
    doc.header["$INSUNITS"] = 6
    m = data["meta"]
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

    # ---- 矿块边界（无填充，彩色闭合线）----
    for b in data["blocks"]:
        lname = LAYER_BY_LV[b["level"]]
        aci = GRADE_COLOR[b["level"]]
        parts = b.get("parts", [b["boundary"]])
        for ring in parts:
            msp.add_lwpolyline([(p[0], p[1]) for p in ring], close=True,
                               dxfattribs={"layer": lname, "color": aci, "lineweight": 30})

    # ---- 网格线（品位色）----
    for b in data["blocks"]:
        aci = GRADE_COLOR[b["level"]]
        for ln in b["grid_lines"]:
            msp.add_line((ln[0][0], ln[0][1]), (ln[1][0], ln[1][1]),
                         dxfattribs={"layer": LAYER_GRID, "color": aci})

    # ---- 网格品位文字：方格中心 (cx, cy)，h=0.3 分级色 ----
    for b in data["blocks"]:
        aci = GRADE_COLOR[b["level"]]
        parts = b.get("parts", [b["boundary"]])
        rings = [[(p[0], p[1]) for p in ring] for ring in parts]
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
                    g = _grade_at(cx, cy, cells_all)
                    if g is not None:
                        msp.add_text(f"{g:.2f}",
                                     dxfattribs={"layer": LAYER_DOTS, "color": aci,
                                                 "height": 0.3, "style": "CN_TTF"},
                                     ).set_placement((cx, cy))
                        n_txt += 1
        print(f"[品位文字] 块#{b['no']}: {n_txt} 个（方格中心 color={aci} h=0.3）")

    # ---- 炮孔：十字 + 长斜引线（45°, 5m）+ 完整工程号 + 品位大字（分级色）----
    for h in data["holes"]:
        cx, cy = h["x"], h["y"]
        lv = grade_level(h["grade"])
        aci = HOLE_ACI.get(lv_index(lv), 8)
        arm = 0.8
        # 十字（坐标点）
        msp.add_line((cx - arm, cy), (cx + arm, cy), dxfattribs={"layer": LAYER_HOLES, "color": aci})
        msp.add_line((cx, cy - arm), (cx, cy + arm), dxfattribs={"layer": LAYER_HOLES, "color": aci})
        # 长斜引线：孔位中心 45° 延伸 5m（明显斜线）
        ex = cx + 3.536
        ey = cy + 3.536
        msp.add_line((cx, cy), (ex, ey), dxfattribs={"layer": LAYER_HOLES, "color": aci})
        # 完整工程号（数据表编号），色138，h=0.4
        msp.add_text(h["id"],
                     dxfattribs={"layer": LAYER_HOLES, "color": 138, "height": 0.4,
                                 "style": "CN_TTF"},
                     ).set_placement((ex + 0.4, ey))
        # 品位大字 h=0.7，按分级色
        msp.add_text(f"{h['grade']:.2f}",
                     dxfattribs={"layer": LAYER_HOLES, "color": aci, "height": 0.7,
                                 "style": "CN_TTF"},
                     ).set_placement((ex + 0.4, ey + 1.0))

    # ---- 矿块号：引线起点取各自矿块边界最近点，文字贴近矿块 ----
    label_target = {1: (470068.00, 4349642.00), 2: (470128.00, 4349732.00), 3: (470132.00, 4349698.00)}
    for b in data["blocks"]:
        no = b["no"]
        parts = b.get("parts", [b["boundary"]])
        rings = [[(p[0], p[1]) for p in ring] for ring in parts]
        tx, ty = label_target.get(no, b["centroid"])
        # 引线起点 = 该矿块边界上离文字最近的点
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

    # ---- 报告 PNG 图片 ----
    img_def = doc.add_image_def(str(REPORT_PNG), size_in_pixel=(1350, 1000))
    img = msp.add_image(img_def, insert=(maxx + 40, maxy - 60),
                        size_in_units=(47.25, 35.0),
                        dxfattribs={"layer": LAYER_REPORT})
    img.dxf.image_size = (47.25, 35.0)

    # ---- 标题 ----
    msp.add_text(f"{m['platform']}平台 {m['date']} 二次圈矿矿块图（3块版）",
                 dxfattribs={"layer": LAYER_REPORT, "height": 6.0, "style": "CN_SHX"},
                 ).set_placement((minx, maxy + 8))

    doc.saveas(DXF)
    print("[DXF]", DXF)


def write_3ds(data):
    m = data["meta"]
    bench_z = m["bench_z"]
    lines = [f"C:\\<path>\\{THREEDS.name}, 3DMine String File", "",
             "file_version=3DMine_2009", "",
             "1,7,0,1.00,1.00,1.00,0,0.5,0,Continuous,1", "",
             "0,0,0,0,0,0,0,0,", ""]
    for b in data["blocks"]:
        parts = b.get("parts", [b["boundary"]])
        for ring in parts:
            for p in ring:
                lines.append(f"1,{p[1]:.6f},{p[0]:.6f},{bench_z:.6f},")
            p0 = ring[0]
            lines.append(f"1,{p0[1]:.6f},{p0[0]:.6f},{bench_z:.6f},")
        lines += ["", "0,0.000000,0.000000,0.000000,-1,,1.000000,0.000000,-1.000000,-1.000000,-1.000000", ""]
    THREEDS.write_text("\n".join(lines), encoding="gbk")
    print("[3DS]", THREEDS)


if __name__ == "__main__":
    data, comp, cells_all = load_data()
    make_report_png(data)
    build_dxf(data, comp, cells_all)
    write_3ds(data)
    print("DXF+3DS READY, DWG 用转换脚本")
