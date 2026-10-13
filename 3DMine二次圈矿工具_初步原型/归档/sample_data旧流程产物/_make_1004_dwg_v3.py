# -*- coding: utf-8 -*-
"""
1004 成果 DWG 生成器 v3（逐项对齐人工图风格）：
1) 炮孔：SOLID 实心圆 r=0.5（d=1m 匹配人工 1m 宽），颜色按品位档（废孔8灰/0.5-1 4青/1-1.5 5蓝/1.5-3 1红/≥3 2黄），层"钻孔"；附孔号+品位小字
2) 品位文字：按品位档着色（1.5-3 红/0.5-1 青/1-1.5 蓝/≥3 黄），h=0.2，位置=网格单元左下+(0.15,0.45)，样式 txt.shx（人工 3dmine_textStyle_1 同款）
3) 矿块：无填充（无 hatch，去除斜线），彩色闭合边界线（品位层），线宽 0.3mm
4) 网格线：层"爆区方格网"，颜色按品位档（人工实测 1.5-3 区域红 199 条/0.5-1 区域青 728 条）
5) 中文正常：标题/矿块号/报告文字用 txt.shx+gbcbig.shx 样式（修复问号）
6) 报告：PNG 图片插入图右下角（用户要求图片格式）
7) 矿块号：文字放矿块外 + 引出线（Line 从矿块边界→文字），避免遮挡
输出：DXF -> AutoCAD DWG(AC1024 R2010) + .3ds 矿块边界线 + 报告 PNG
"""
from __future__ import annotations
import json, sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型")
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
OUT = ROOT / "output"

from mdb_loader import load_xls_blast                       # noqa: E402
from voronoi import build_voronoi_cells                     # noqa: E402

XLS = Path(r"D:\WK\N CRT\北部山头3940平台2026\7、单日数据\北部山头3940平台-1004\1、3940平台 炮孔数据库1004.xls")
MACRO = OUT / "1004_macro"
DXF = MACRO / "3940平台 1004二次圈矿矿块图_3块版_full.dxf"
DWG = OUT / "3940平台 1004二次圈矿矿块图_3块版_2010.dwg"
REPORT_PNG = MACRO / "1004炮孔数据报告.png"
THREEDS = OUT / "1004_macro" / "3940平台 1004矿块边界线.3ds"

REPORT_LABEL = {"L1": "0.500-1.000", "L2": "1.000-1.500", "L3": "1.500-3.000", "L4": "3.000-999.000"}
GRADE_COLOR = {"L1": 4, "L2": 5, "L3": 1, "L4": 2}   # 品位档 ACI 色号（3DMine 配色）
HOLE_COLOR = {0: 8, 1: 4, 2: 5, 3: 1, 4: 2}          # 炮孔按品位档色
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
    return "W"  # 废孔


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


def make_report_png(data):
    """报告表格 -> PNG 图片（白底）。"""
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
    # 统计信息作为表格下方文字，不混入表格
    stat_lines = [
        f"{m['platform']}平台 {m['date']} 炮孔统计（31孔）：",
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
    return REPORT_PNG


def build_dxf(data, comp, cells_all):
    from ezdxf import new
    doc = new("R2010")
    doc.header["$INSUNITS"] = 6
    m = data["meta"]
    # 图层
    for lv, lname in LAYER_BY_LV.items():
        doc.layers.add(lname, color=GRADE_COLOR[lv])
    for ln in [LAYER_GRID, LAYER_HOLES, LAYER_MISC, LAYER_DOTS, LAYER_REPORT]:
        doc.layers.add(ln, color=7)
    # 中文样式（txt.shx + gbcbig.shx —— 修复中文问号）
    cn_style = doc.styles.add("CN_SHX", font="txt.shx")
    cn_style.dxf.bigfont = "gbcbig.shx"
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

    # ---- 网格品位文字（品位色、小字、单元左下+偏移）----
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
                                                 "height": 0.2, "style": "CN_SHX"},
                                     ).set_placement((cx + 0.15, cy + 0.45))
                        n_txt += 1
        print(f"[品位文字] 块#{b['no']}: {n_txt} 个（color={aci}）")

    # ---- 炮孔：SOLID 实心圆 r=0.5（品位色）+ 孔号品位文字 ----
    for h in data["holes"]:
        cx, cy = h["x"], h["y"]
        lv = grade_level(h["grade"])
        aci = HOLE_COLOR.get({"L1": 1, "L2": 2, "L3": 3, "L4": 4}.get(lv, 0), 8)
        hatch = msp.add_hatch(dxfattribs={"layer": LAYER_HOLES})
        import math
        pts = [(cx + 0.5 * math.cos(a), cy + 0.5 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 24)]
        hatch.paths.add_polyline_path(pts, is_closed=True)
        hatch.set_pattern_fill("SOLID", color=aci)
        hid = h["id"].split("-")[-1]
        msp.add_text(f"{hid} {h['grade']:.2f}",
                     dxfattribs={"layer": LAYER_HOLES, "color": 7, "height": 0.8, "style": "CN_SHX"},
                     ).set_placement((cx + 1.2, cy + 1.2))

    # ---- 矿块号：矿块外 + 引出线（人工布局坐标）----
    label_pos = {1: (470054.52, 4349738.98), 2: (470134.55, 4349705.37), 3: (470125.82, 4349664.04)}
    lead_from = {1: (470093.89, 4349657.99), 2: (470110.31, 4349698.22), 3: (470093.89, 4349657.99)}
    for b in data["blocks"]:
        no = b["no"]
        lx, ly = label_pos.get(no, b["centroid"])
        msp.add_mtext(f"{no}号矿块", dxfattribs={"layer": LAYER_MISC, "style": "CN_SHX",
                                                "char_height": 5.0}).set_location((lx, ly))
        # 引出线：矿块边界上最近点 -> 文字
        fromx, fromy = lead_from.get(no, b["centroid"])
        msp.add_line((fromx, fromy), (lx, ly), dxfattribs={"layer": LAYER_MISC, "color": 7})

    # ---- 报告 PNG 图片（image_size 设为米单位，避免 1350m 巨大）----
    img_def = doc.add_image_def(str(REPORT_PNG), size_in_pixel=(1350, 1000))
    img = msp.add_image(img_def, insert=(maxx + 40, maxy - 60),
                        size_in_units=(47.25, 35.0),
                        dxfattribs={"layer": LAYER_REPORT})
    img.dxf.image_size = (47.25, 35.0)

    # ---- 标题（中文字体）----
    msp.add_text(f"{m['platform']}平台 {m['date']} 二次圈矿矿块图（3块版）",
                 dxfattribs={"layer": LAYER_REPORT, "height": 6.0, "style": "CN_SHX"},
                 ).set_placement((minx, maxy + 8))

    doc.saveas(DXF)
    print("[DXF]", DXF)
    return DXF


def _pip_multi(x, y, rings):
    return any(_pip(x, y, ring) for ring in rings)


def write_3ds(data):
    """矿块边界线 .3ds（3DMine_2009 文本格式，GBK 编码）。"""
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
            # 闭合重复首点
            p0 = ring[0]
            lines.append(f"1,{p0[1]:.6f},{p0[0]:.6f},{bench_z:.6f},")
        lines += ["", "0,0.000000,0.000000,0.000000,-1,,1.000000,0.000000,-1.000000,-1.000000,-1.000000", ""]
    THREEDS.write_text("\n".join(lines), encoding="gbk")
    print("[3DS]", THREEDS)


def convert_to_dwg():
    import os, subprocess, time
    import win32com.client
    import pythoncom
    ACAD_EXE = r"E:\gzRJ\CAD\AutoCAD 2023\acad.exe"
    os.system("taskkill /IM acad.exe /F >nul 2>nul")
    time.sleep(3)
    subprocess.Popen([ACAD_EXE], cwd=os.path.dirname(ACAD_EXE))
    pythoncom.CoInitialize()
    acad = None
    for i in range(90):
        try:
            acad = win32com.client.Dispatch("AutoCAD.Application")
            print(f"COM ready {i*2}s")
            break
        except Exception:
            time.sleep(2)
    if acad is None:
        print("FAIL: AutoCAD COM not ready")
        return False
    try:
        acad.Visible = False
    except Exception:
        pass
    acad.Documents.Open(str(DXF), True)
    doc = acad.ActiveDocument
    if os.path.exists(DWG):
        os.remove(DWG)
    doc.SaveAs(str(DWG), 48)  # AC1024 R2010
    with open(DWG, "rb") as fp:
        head = fp.read(6).decode("ascii", errors="ignore")
    print("[DWG]", DWG, "版本头:", head, "大小:", os.path.getsize(DWG))
    doc.Close(False)
    pythoncom.CoUninitialize()
    return head == "AC1024"


if __name__ == "__main__":
    data, comp, cells_all = load_data()
    make_report_png(data)
    build_dxf(data, comp, cells_all)
    write_3ds(data)
    convert_to_dwg()
    print("ALL DONE")
