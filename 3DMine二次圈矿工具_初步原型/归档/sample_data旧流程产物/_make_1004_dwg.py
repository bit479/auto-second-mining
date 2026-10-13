# -*- coding: utf-8 -*-
"""
1004 成果 DWG 生成器（对齐人工图结构）：
- 图层复刻人工：1.500-3.000(红) / 0.500-1.000(青) / 爆区方格网 / 钻孔 / 线条 / 点 / 报告
- 矿块：彩色闭合边界 + SOLID 填充（先填充后画线，网格/品位/边界均在填充之上）
- 炮孔：31 个实心圆点(钻孔层) + 孔号品位文字
- 1m 网格线(爆区方格网层) + 每个网格单元中心品位文字（全孔 voronoi 品位）
- 矿块号 MText（1号矿块…）+ 右下角数据报告 MTEXT
- 输出：DXF(R2010) -> AutoCAD COM SaveAs DWG(ac2010_dwg)
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
DXF = OUT / "1004_macro" / "3940平台 1004二次圈矿矿块图_3块版_full.dxf"
DWG = OUT / "3940平台 1004二次圈矿矿块图_3块版_2010.dwg"

REPORT_LABEL = {"L1": "0.500-1.000", "L2": "1.000-1.500", "L3": "1.500-3.000", "L4": "3.000-999.000"}
# 人工图层命名 + 3DMine 配色（ACI 色号：红=1 蓝=5 青=4 黄=2）
LAYER_BY_LV = {
    "L1": ("0.500-1.000", 4, (0, 255, 255)),
    "L2": ("1.000-1.500", 5, (0, 0, 255)),
    "L3": ("1.500-3.000", 1, (255, 0, 0)),
    "L4": ("3.000-999.000", 2, (255, 255, 0)),
}
LAYER_GRID = "爆区方格网"
LAYER_HOLES = "钻孔"
LAYER_MISC = "线条"
LAYER_DOTS = "点"
LAYER_REPORT = "报告"


def load_data():
    data = json.load(open(OUT / "1004_macro" / "1004_blocks.json", encoding="utf-8"))
    comp = load_xls_blast(XLS)
    # 全孔 voronoi（品位插值：网格单元品位 = 所在 voronoi 单元品位）
    cells_all = build_voronoi_cells(comp["X"].to_numpy(float), comp["Y"].to_numpy(float),
                                    comp["Grade"].to_numpy(float), comp["Hole_ID"].tolist())
    return data, comp, cells_all


def build_dxf(data, comp, cells_all):
    from ezdxf import new
    from ezdxf.enums import TextEntityAlignment
    doc = new("R2010")
    doc.header["$INSUNITS"] = 6  # 米
    m = data["meta"]
    for lv, (lname, aci, _rgb) in LAYER_BY_LV.items():
        doc.layers.add(lname, color=aci)
    for ln in [LAYER_GRID, LAYER_HOLES, LAYER_MISC, LAYER_DOTS, LAYER_REPORT]:
        doc.layers.add(ln, color=7)
    msp = doc.modelspace()

    xs = [h["x"] for h in data["holes"]]
    ys = [h["y"] for h in data["holes"]]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)

    # ---- 1) 矿块：先 SOLID 填充（底层），再网格、品位、边界 ----
    for b in data["blocks"]:
        lname, aci, rgb = LAYER_BY_LV[b["level"]]
        parts = b.get("parts", [b["boundary"]])
        for ring in parts:
            coords = [(p[0], p[1]) for p in ring]
            hatch = msp.add_hatch(dxfattribs={"layer": lname})
            hatch.paths.add_polyline_path(coords, is_closed=True)
            hatch.set_pattern_fill("SOLID", color=aci)

    # ---- 2) 1m 网格线 ----
    for b in data["blocks"]:
        for ln in b["grid_lines"]:
            msp.add_line((ln[0][0], ln[0][1]), (ln[1][0], ln[1][1]),
                         dxfattribs={"layer": LAYER_GRID})

    # ---- 3) 网格单元品位文字（中心点落在矿块内 -> 所在 voronoi 单元品位）----
    for b in data["blocks"]:
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
                        msp.add_text(f"{g:.2f}", dxfattribs={"layer": LAYER_DOTS, "height": 0.5},
                                     ).set_placement((cx - 0.25, cy - 0.25))
                        n_txt += 1
        print(f"[品位文字] 块#{b['no']}: {n_txt} 个")

    # ---- 4) 矿块边界（彩色粗线）----
    for b in data["blocks"]:
        lname, aci, _rgb = LAYER_BY_LV[b["level"]]
        parts = b.get("parts", [b["boundary"]])
        for ring in parts:
            msp.add_lwpolyline([(p[0], p[1]) for p in ring], close=True,
                               dxfattribs={"layer": lname, "lineweight": 40})

    # ---- 5) 炮孔：实心圆点 + 孔号品位文字 ----
    for h in data["holes"]:
        cx, cy = h["x"], h["y"]
        circ = msp.add_circle((cx, cy), 1.0, dxfattribs={"layer": LAYER_HOLES})
        # 圆内 SOLID 填充
        hatch = msp.add_hatch(dxfattribs={"layer": LAYER_HOLES})
        import math
        pts = [(cx + 1.0 * math.cos(a), cy + 1.0 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 24)]
        hatch.paths.add_polyline_path(pts, is_closed=True)
        hatch.set_pattern_fill("SOLID", color=7)
        hid = h["id"].split("-")[-1]
        msp.add_text(f"{hid} {h['grade']:.2f}", dxfattribs={"layer": LAYER_HOLES, "height": 0.8},
                     ).set_placement((cx + 1.6, cy + 1.6))

    # ---- 6) 矿块号 ----
    for b in data["blocks"]:
        cx, cy = b["centroid"]
        msp.add_mtext(f"{b['no']}号矿块", dxfattribs={"layer": LAYER_MISC, "char_height": 5.0}
                      ).set_location((cx - 4, cy - 4))

    # ---- 7) 数据报告（右下角 MTEXT，对齐人工报告格式）----
    rpt_x, rpt_y = maxx + 15, maxy - 10
    title = f"{m['platform']}平台 {m['date']}炮孔数据报告"
    rpt_lines = [title, "=" * 42,
                 f"{'体号':<4}{'品位类型':<14}{'体积m3':>9}{'重量t':>10}{'平均品位g/t':>11}{'金属量百克':>10}"]
    rows = []
    for lv in ["L4", "L3", "L2", "L1"]:
        bs = [b for b in data["blocks"] if b["level"] == lv]
        if not bs:
            continue
        for b in bs:
            rows.append((b["no"], b["grade_label"], b["volume_m3"], b["tonnage_t"],
                         b["avg_grade_g_t"], b["metal_g"] / 100.0))
        st = sum(b["tonnage_t"] for b in bs)
        sm = sum(b["metal_g"] for b in bs)
        rows.append(("小计", REPORT_LABEL[lv], sum(b["volume_m3"] for b in bs),
                     st, sm / st, sm / 100.0))
    t_all = sum(b["tonnage_t"] for b in data["blocks"])
    m_all = sum(b["metal_g"] for b in data["blocks"])
    rows.append(("合计", "", sum(b["volume_m3"] for b in data["blocks"]),
                 t_all, m_all / t_all, m_all / 100.0))
    for no, lbl, vol, ton, g, metal in rows:
        rpt_lines.append(f"{str(no):<4}{lbl:<14}{vol:>9.1f}{ton:>10.1f}{g:>11.3f}{metal:>10.2f}")
    rpt_lines.append("")
    rpt_lines.append("炮孔统计（31孔）：")
    grades = [h["grade"] for h in data["holes"]]
    rpt_lines.append(f"  ≥3.0: {sum(1 for g in grades if g >= 3.0)}孔   1.5-3: {sum(1 for g in grades if 1.5 <= g < 3)}孔")
    rpt_lines.append(f"  1-1.5: {sum(1 for g in grades if 1 <= g < 1.5)}孔   0.5-1: {sum(1 for g in grades if 0.5 <= g < 1)}孔")
    rpt_lines.append(f"  <0.5: {sum(1 for g in grades if g < 0.5)}孔")
    mtxt = msp.add_mtext("\n".join(rpt_lines), dxfattribs={"layer": LAYER_REPORT, "char_height": 1.6})
    mtxt.set_location((rpt_x, rpt_y))

    # ---- 8) 标题 ----
    msp.add_text(f"{m['platform']}平台 {m['date']} 二次圈矿矿块图（3块版）",
                 dxfattribs={"layer": LAYER_REPORT, "height": 6.0}).set_placement((minx, maxy + 8))

    doc.saveas(DXF)
    print("[DXF]", DXF)
    return DXF


def _pip_multi(x, y, rings):
    for ring in rings:
        if _pip(x, y, ring):
            return True
    return False


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


def convert_to_dwg():
    """AutoCAD COM: 打开 DXF -> SaveAs DWG(ac2010_dwg)。enum48=AC1024(R2010) 实测。"""
    import pythoncom
    import win32com.client
    pythoncom.CoInitialize()
    acad = win32com.client.Dispatch("AutoCAD.Application")
    try:
        acad.Visible = False
    except Exception:
        pass
    doc = acad.Documents.Open(str(DXF), True)
    doc.SaveAs(str(DWG), 48)  # ac2010_dwg = R2010 (AC1024)，实测确认
    print("[DWG]", DWG)
    doc.Close(False)
    try:
        acad.Quit()
    except Exception:
        pass
    pythoncom.CoUninitialize()


if __name__ == "__main__":
    data, comp, cells_all = load_data()
    build_dxf(data, comp, cells_all)
    convert_to_dwg()
    print("ALL DONE")
