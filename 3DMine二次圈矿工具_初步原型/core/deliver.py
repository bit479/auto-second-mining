# -*- coding: utf-8 -*-
"""三件套生成：报告 xlsx / 矿界图 DXF / 矿块边界 .3ds

绘图细则来自人工图实测：
  十字 "+"    ±0.5m 两条线（层 点）
  轨迹线       孔口向西 1.2m 水平线（层 钻孔）
  工程号       孔口偏移 (-2.28, +0.40)，h=0.4，颜色 138（层 钻孔）
  品位         孔口偏移 (-3.19, -0.35)，h=0.7，按档着色（层 钻孔）
  1m 方格      按矿界裁剪后的 1×1 闭合小多边形（层 爆区方格网）
  方格品位     方格中心，h=0.1333，按档着色
  矿块号       "n号矿块" h=3.0 + 斜向引线（从本块内部中心出发）
  报告表       矢量 LINE + TEXT（手机 CAD 看图王也能显示，不再依赖外部 PNG）
"""
from __future__ import annotations

import math
from pathlib import Path

from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import polylabel, unary_union

from composite import load_composite_blocks, merge_outline      # noqa: E402

LEVEL_COLOR = {"L1": 4, "L2": 5, "L3": 1, "L4": 2}          # AutoCAD 色号（青/蓝/红/黄）
LEVEL_RGB = {"L1": (0, 255, 255), "L2": (0, 0, 255),
             "L3": (255, 0, 0), "L4": (255, 255, 0)}
HID_COLOR = 138          # 工程号 ACI 色号（人工图实测）
HID_TRUE_COLOR = 0x004C4C   # 工程号/十字 真彩色 RGB(0,76,76)（用户指定）
CROSS_HALF = 0.5         # 十字半臂长(m)：用户指定十字总长 1.0 m
TRAIL_LEN = 1.2          # 轨迹线长度(m)：人工图实测 1.2 m
GRID_RULE = "center"     # 方格取舍：只保留格心落在矿界内的格（与人工图一致）
LABEL_H_M = 3.0          # 矿块号文字高度(m)：用户 2026-10-14 定"字号还是用 3.0"


def level_id_of(grade: float):
    if grade >= 3.0:
        return "L4"
    if grade >= 1.5:
        return "L3"
    if grade >= 1.0:
        return "L2"
    if grade >= 0.5:
        return "L1"
    return None


def grid_cells(poly: Polygon, size: float = 1.0, origin=None, rule: str = None):
    """按矿界裁剪的 1×1 m 方格（闭合小多边形）。

    origin=(x0,y0) 为方格原点；人工图的规律是**取矿界包围盒左下角**。
    rule="center" 时只保留方格中心落在矿界内的格（与人工图一致）。
    """
    out = []
    rule = rule or GRID_RULE
    minx, miny, maxx, maxy = poly.bounds
    if origin is None:
        gx0 = math.floor(minx / size) * size
        gy0 = math.floor(miny / size) * size
    else:
        ox, oy = origin
        gx0 = ox + math.floor((minx - ox) / size) * size
        gy0 = oy + math.floor((miny - oy) / size) * size
    x = gx0
    while x < maxx:
        y = gy0
        while y < maxy:
            c = box(x, y, x + size, y + size)
            inter = c.intersection(poly)
            keep = (not inter.is_empty and inter.area > 1e-9)
            if keep and rule == "center":
                keep = poly.contains(c.centroid)
            if keep:
                if inter.geom_type == "Polygon":
                    out.append(inter)
                else:
                    for g in getattr(inter, "geoms", []):
                        if g.geom_type == "Polygon" and g.area > 1e-9:
                            out.append(g)
            y += size
        x += size
    return out


# ---------------------------------------------------------------- 报告 xlsx
def grade_stats(holes):
    """炮孔品位统计：>=3 / 1.5-3 / 1-1.5 / 0.5-1 / <0.5 孔数。"""
    return {
        ">=3": sum(1 for h in holes if h.grade >= 3.0),
        "1.5-3": sum(1 for h in holes if 1.5 <= h.grade < 3.0),
        "1-1.5": sum(1 for h in holes if 1.0 <= h.grade < 1.5),
        "0.5-1": sum(1 for h in holes if 0.5 <= h.grade < 1.0),
        "<0.5": sum(1 for h in holes if h.grade < 0.5),
    }


def write_report_xlsx(blocks, meta, path: Path, holes=None) -> None:
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    title = "%s平台 %s炮孔数据报告" % (meta["platform"], meta["date"])
    ws["A1"] = title
    ws.merge_cells("A1:F1")
    ws["A1"].font = Font(bold=True, size=12)
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")

    head = ["类型", "体号", "体积", "重量", "平均品位(Au)", "金属量（百克）"]
    for i, h in enumerate(head, 1):
        c = ws.cell(row=2, column=i, value=h)
        c.font = Font(bold=True)
        c.alignment = Alignment(horizontal="center", vertical="center")
        # 用户 2026-10-15：报告里**不要单元格底纹**（原来是浅蓝/浅灰）
        c.fill = PatternFill(fill_type=None)

    thin = Side(style="thin", color="000000")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    r = 3
    totals = [0.0, 0.0, 0.0]
    for lid in ("L4", "L3", "L2", "L1"):
        bs = [b for b in blocks if b.level_id == lid]
        if not bs:
            continue
        sv = st = sm = 0.0
        for b in bs:
            ws.cell(row=r, column=1, value=b.label)
            ws.cell(row=r, column=2, value=b.no)
            ws.cell(row=r, column=3, value=round(b.volume_m3, 3))
            ws.cell(row=r, column=4, value=round(b.tonnage_t, 3))
            ws.cell(row=r, column=5, value=round(b.grade, 3))
            ws.cell(row=r, column=6, value=round(b.metal_hg, 3))
            sv += b.volume_m3
            st += b.tonnage_t
            sm += b.metal_hg
            r += 1
        ws.cell(row=r, column=1, value="小计")
        ws.cell(row=r, column=3, value=round(sv, 3))
        ws.cell(row=r, column=4, value=round(st, 3))
        ws.cell(row=r, column=5, value=round(sm * 100.0 / st, 3) if st else 0)
        ws.cell(row=r, column=6, value=round(sm, 3))
        for c in range(1, 7):
            ws.cell(row=r, column=c).fill = PatternFill(fill_type=None)
        r += 1
        totals[0] += sv
        totals[1] += st
        totals[2] += sm

    ws.cell(row=r, column=1, value="合计")
    ws.cell(row=r, column=3, value=round(totals[0], 3))
    ws.cell(row=r, column=4, value=round(totals[1], 3))
    ws.cell(row=r, column=5, value=round(totals[2] * 100.0 / totals[1], 3) if totals[1] else 0)
    ws.cell(row=r, column=6, value=round(totals[2], 3))
    for c in range(1, 7):
        ws.cell(row=r, column=c).font = Font(bold=True)
    last_row = r

    if holes:
        r += 2
        ws.cell(row=r, column=1, value="炮孔品位统计（孔数）").font = Font(bold=True)
        r += 1
        st = grade_stats(holes)
        ws.cell(row=r, column=1, value="≥3")
        ws.cell(row=r, column=2, value=st[">=3"])
        ws.cell(row=r, column=3, value="1.5-3")
        ws.cell(row=r, column=4, value=st["1.5-3"])
        ws.cell(row=r, column=5, value="1-1.5")
        ws.cell(row=r, column=6, value=st["1-1.5"])
        r += 1
        ws.cell(row=r, column=1, value="0.5-1")
        ws.cell(row=r, column=2, value=st["0.5-1"])
        ws.cell(row=r, column=3, value="<0.5")
        ws.cell(row=r, column=4, value=st["<0.5"])
        ws.cell(row=r, column=5, value="合计孔数")
        ws.cell(row=r, column=6, value=len(holes))
        last_row = r

    for row in ws.iter_rows(min_row=2, max_row=last_row, min_col=1, max_col=6):
        for cell in row:
            cell.border = border
            # 用户 2026-10-19：报告表按 Excel 默认风格，所有文字居中
            cell.alignment = Alignment(horizontal="center", vertical="center")
            if cell.column >= 3:
                cell.number_format = "0.000"
    for col, w in zip("ABCDEF", (14, 8, 12, 12, 14, 14)):
        ws.column_dimensions[col].width = w
    wb.save(str(path))


# ---------------------------------------------------------------- DXF
def _report_rows(blocks):
    """报告主表的行（含小计/合计），xlsx / xls / 分表三种导出共用。"""
    rows = []
    for lid in ("L4", "L3", "L2", "L1", "L0"):
        bs = [b for b in blocks if b.level_id == lid]
        if not bs:
            continue
        for b in bs:
            rows.append([b.label, b.no, b.volume_m3, b.tonnage_t, b.grade, b.metal_hg])
        st = sum(b.tonnage_t for b in bs)
        sm = sum(b.metal_hg for b in bs)
        rows.append(["小计", "", sum(b.volume_m3 for b in bs), st,
                     (sm * 100.0 / st if st else 0), sm])
    tt = sum(b.tonnage_t for b in blocks)
    tm = sum(b.metal_hg for b in blocks)
    rows.append(["合计", "", sum(b.volume_m3 for b in blocks), tt,
                 (tm * 100.0 / tt if tt else 0), tm])
    return rows


def write_report_xls(blocks, meta, path: Path, holes=None) -> None:
    """再出一份**旧版 .xls**（内容与 xlsx 相同）——有些流程只认 .xls（用户 2026-10-18 要的）。"""
    import xlwt
    wb = xlwt.Workbook(encoding="utf-8")
    ws = wb.add_sheet("Sheet1")
    style_title = xlwt.easyxf("font: bold on, height 260; align: horiz center")
    style_head = xlwt.easyxf("font: bold on; align: horiz center; borders: left thin,"
                             " right thin, top thin, bottom thin")
    style_cell = xlwt.easyxf("align: horiz center; borders: left thin, right thin,"
                             " top thin, bottom thin")
    style_num = xlwt.easyxf("align: horiz center; borders: left thin, right thin,"
                            " top thin, bottom thin", num_format_str="0.000")
    ws.write_merge(0, 0, 0, 5, "%s平台 %s炮孔数据报告" % (meta["platform"], meta["date"]),
                   style_title)
    head = ["类型", "体号", "体积", "重量", "平均品位(Au)", "金属量（百克）"]
    for c, h in enumerate(head):
        ws.write(1, c, h, style_head)
    for r, row in enumerate(_report_rows(blocks), start=2):
        for c, v in enumerate(row):
            if c >= 2 and isinstance(v, (int, float)):
                ws.write(r, c, round(float(v), 6), style_num)
            else:
                ws.write(r, c, v if v is not None else "", style_cell)
    ws.col(0).width = 3600
    ws.col(2).width = 3000
    ws.col(3).width = 3000
    ws.col(4).width = 3200
    ws.col(5).width = 3600
    wb.save(str(path))


def write_report_split(blocks, meta, folder: Path, holes=None):
    """每块一份 xlsx，放进「炮孔数据报告分表」文件夹（照 3DMine 分表的版式：
    标题「3DMine 炮孔数据库报告」+ 表头 + 该块一行 + 小计 + 总计）。"""
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    thin = Side(style="thin", color="000000")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    out = []
    for b in blocks:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Sheet1"
        ws["A1"] = "3DMine 炮孔数据库报告"
        ws.merge_cells("A1:F1")
        ws["A1"].font = Font(bold=True, size=12)
        ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
        for i, h in enumerate(["类型", "体号", "体积", "重量", "平均品位(Au)", "金属量"], 1):
            c = ws.cell(row=2, column=i, value=h)
            c.font = Font(bold=True)
            c.alignment = Alignment(horizontal="center")
            c.fill = PatternFill(fill_type=None)
        vals = [b.label, b.no, round(b.volume_m3, 3), round(b.tonnage_t, 3),
                round(b.grade, 3), round(b.metal_hg, 3)]
        for i, v in enumerate(vals, 1):
            ws.cell(row=3, column=i, value=v)
        ws.cell(row=4, column=1, value="小计")
        for col, v in ((3, vals[2]), (4, vals[3]), (5, vals[4]), (6, vals[5])):
            ws.cell(row=4, column=col, value=v)
        ws.cell(row=5, column=1, value="总计")
        for col, v in ((3, vals[2]), (4, vals[3]), (5, vals[4]), (6, vals[5])):
            ws.cell(row=5, column=col, value=v)
        for row in ws.iter_rows(min_row=2, max_row=5, min_col=1, max_col=6):
            for c in row:
                c.border = border
                c.alignment = Alignment(horizontal="center")
                c.fill = PatternFill(fill_type=None)
        ws.column_dimensions["A"].width = 18
        for col in "CDEF":
            ws.column_dimensions[col].width = 14
        p = folder / ("%s号矿块 %s %s.xlsx" % (b.no, b.label, meta["date"]))
        wb.save(str(p))
        out.append(p)
    return out


def write_report_png(blocks, meta, holes, path: Path, dpi: int = 150) -> tuple:
    """把报告表格画成 PNG（用于粘贴进 CAD 图）。返回像素尺寸 (w, h)。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun"]
    plt.rcParams["axes.unicode_minus"] = False

    rows = [["类型", "体号", "体积", "重量", "平均品位(Au)", "金属量（百克）"]]
    for lid in ("L4", "L3", "L2", "L1"):
        bs = [b for b in blocks if b.level_id == lid]
        if not bs:
            continue
        for b in bs:
            rows.append([b.label, str(b.no), "%.3f" % b.volume_m3, "%.3f" % b.tonnage_t,
                         "%.3f" % b.grade, "%.3f" % b.metal_hg])
        st = sum(b.tonnage_t for b in bs)
        sm = sum(b.metal_hg for b in bs)
        rows.append(["小计", "", "%.3f" % sum(b.volume_m3 for b in bs), "%.3f" % st,
                     "%.3f" % (sm * 100.0 / st if st else 0), "%.3f" % sm])
    tt = sum(b.tonnage_t for b in blocks)
    tm = sum(b.metal_hg for b in blocks)
    rows.append(["合计", "", "%.3f" % sum(b.volume_m3 for b in blocks), "%.3f" % tt,
                 "%.3f" % (tm * 100.0 / tt if tt else 0), "%.3f" % tm])

    # 主表 + 下面一张小的"炮孔品位统计"表（主表保持与人工报告版式一致）
    st = grade_stats(holes) if holes else {}
    st_rows = [["炮孔品位统计", "≥3", "1.5-3", "1-1.5", "0.5-1", "<0.5", "合计"],
               ["孔数", str(st.get(">=3", 0)), str(st.get("1.5-3", 0)),
                str(st.get("1-1.5", 0)), str(st.get("0.5-1", 0)),
                str(st.get("<0.5", 0)),
                str(sum(st.values())) if st else "0"]]
    h_main = 0.42 * len(rows) + 1.6
    fig, ax = plt.subplots(figsize=(9, h_main + (0.8 if st else 0.0)))
    ax.axis("off")
    ax.set_title("%s平台 %s炮孔数据报告" % (meta["platform"], meta["date"]),
                 fontsize=13, pad=10)
    tbl = ax.table(cellText=rows, cellLoc="center",
                   bbox=[0.0, 0.16 if st else 0.0, 1.0, 0.78 if st else 1.0])
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9)
    for (r0, c0), cell in tbl.get_celld().items():
        if r0 == 0:
            cell.set_facecolor("none")          # 用户要求：单元格不要底纹
            cell.set_text_props(weight="bold")
        elif rows[r0][0] in ("小计", "合计"):
            cell.set_facecolor("none")
    if st:
        t2 = ax.table(cellText=st_rows, cellLoc="center",
                      bbox=[0.14, 0.0, 0.72, 0.085])
        t2.auto_set_font_size(False)
        t2.set_fontsize(8.5)
        for (r0, c0), cell in t2.get_celld().items():
            if r0 == 0:
                cell.set_facecolor("none")
                cell.set_text_props(weight="bold")
    # 只露出标题 + 表格（裁掉四周空白）
    out = path
    try:
        fig.savefig(str(out), dpi=dpi, facecolor="white",
                    bbox_inches="tight", pad_inches=0.02)
    except PermissionError:
        out = path.with_name(path.stem + "_new" + path.suffix)
        fig.savefig(str(out), dpi=dpi, facecolor="white",
                    bbox_inches="tight", pad_inches=0.02)
        print("    %s 被占用，已另存为 %s" % (path.name, out.name))
    w, h = fig.canvas.get_width_height()
    plt.close(fig)
    # 再裁掉四周空白：只留标题 + 表格
    try:
        from PIL import Image, ImageChops
        im = Image.open(out).convert("RGB")
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bbox = ImageChops.difference(im, bg).getbbox()
        if bbox:
            pad = 6
            bbox = (max(0, bbox[0] - pad), max(0, bbox[1] - pad),
                    min(im.size[0], bbox[2] + pad), min(im.size[1], bbox[3] + pad))
            im = im.crop(bbox)
            im.save(out)
            w, h = im.size
    except Exception as exc:
        print("    报告图裁剪跳过:", exc)
    return out, w, h


def _nearest_hole_grade(cell: Polygon, holes):
    c = cell.representative_point()
    best, bd = None, 1e18
    for h in holes:
        d = (h.x - c.x) ** 2 + (h.y - c.y) ** 2
        if d < bd:
            bd, best = d, h
    return best


BLANK_LAYER = "缺工程待取样"
COMPOSITE_LAYER = "综合图_历史矿块"
BLANK_NOTE = "（缺工程，待取样验证后再进行施工）"

# 报告表（矢量）：列宽合计 40 m，与原来贴图宽度一致；行高/字高按图面比例定
TABLE_COL_W = (6.0, 5.0, 7.0, 7.0, 8.0, 7.0)
TABLE_ROW_H = 1.3
TABLE_TEXT_H = 0.8
TABLE_TITLE_H = 1.6


def _table_data(blocks, holes):
    """成果图里那张报告表的行（全部是字符串，跟 PNG 报告版式一致）。"""
    rows = [["类型", "体号", "体积", "重量", "平均品位(Au)", "金属量（百克）"]]
    for lid in ("L4", "L3", "L2", "L1"):
        bs = [b for b in blocks if b.level_id == lid]
        if not bs:
            continue
        for b in bs:
            rows.append([b.label, str(b.no), "%.3f" % b.volume_m3,
                         "%.3f" % b.tonnage_t, "%.3f" % b.grade,
                         "%.3f" % b.metal_hg])
        st = sum(b.tonnage_t for b in bs)
        sm = sum(b.metal_hg for b in bs)
        rows.append(["小计", "", "%.3f" % sum(b.volume_m3 for b in bs),
                     "%.3f" % st, "%.3f" % (sm * 100.0 / st if st else 0),
                     "%.3f" % sm])
    tt = sum(b.tonnage_t for b in blocks)
    tm = sum(b.metal_hg for b in blocks)
    rows.append(["合计", "", "%.3f" % sum(b.volume_m3 for b in blocks),
                 "%.3f" % tt, "%.3f" % (tm * 100.0 / tt if tt else 0),
                 "%.3f" % tm])
    st = grade_stats(holes) if holes else {}
    stat_rows = [["≥3", "1.5-3", "1-1.5", "0.5-1", "<0.5", "合计"],
                 [str(st.get(">=3", 0)), str(st.get("1.5-3", 0)),
                  str(st.get("1-1.5", 0)), str(st.get("0.5-1", 0)),
                  str(st.get("<0.5", 0)),
                  str(sum(st.values())) if st else "0"]]
    return rows, stat_rows


def _table_height(rows, stat_rows):
    """矢量报告表总高（米），第 4 步给矿块号避让用。"""
    if not stat_rows:
        return TABLE_TITLE_H + 1.2 + TABLE_ROW_H * len(rows)
    return (TABLE_TITLE_H + 1.2 + TABLE_ROW_H * len(rows)
            + 1.8 + TABLE_TITLE_H * 0.8 + 0.5
            + TABLE_ROW_H * len(stat_rows))


def _text_width(s, h):
    """估算文字宽度（中文按 1 个字高，西文/数字按 0.58 个字高）。"""
    return sum(h if ord(ch) > 127 else h * 0.58 for ch in str(s))


def _draw_report_table(msp, x0, y_top, rows, stat_rows, title):
    """把报告表画成 LINE + TEXT 矢量实体（不引用外部图片）。"""
    total_w = sum(TABLE_COL_W)
    xs = [x0]
    for w in TABLE_COL_W:
        xs.append(xs[-1] + w)
    attrib = {"layer": "0", "color": 7, "style": "CN_TTF"}

    def cell_text(s, cx, cy, h, bold=False):
        s = str(s)
        w = _text_width(s, h)
        msp.add_text(s, dxfattribs=dict(attrib, height=h)).set_placement(
            (cx - w / 2.0, cy - h * 0.5))

    # 标题（Excel 默认风格：跨整表居中）
    msp.add_text(title, dxfattribs=dict(attrib, height=TABLE_TITLE_H)
                 ).set_placement(
                     (x0 + (total_w - _text_width(title, TABLE_TITLE_H)) / 2.0,
                      y_top - TABLE_TITLE_H))
    y = y_top - TABLE_TITLE_H - 1.2

    # 主表
    n = len(rows)
    for i in range(n + 1):
        yy = y - i * TABLE_ROW_H
        msp.add_line((x0, yy), (x0 + total_w, yy),
                     dxfattribs={"layer": "0", "color": 8, "lineweight": 13})
    for xx in xs:
        msp.add_line((xx, y), (xx, y - n * TABLE_ROW_H),
                     dxfattribs={"layer": "0", "color": 8, "lineweight": 13})
    for i, row in enumerate(rows):
        cy = y - (i + 0.5) * TABLE_ROW_H
        h = TABLE_TEXT_H
        for j, val in enumerate(row):
            if val == "":
                continue
            cell_text(val, (xs[j] + xs[j + 1]) / 2.0, cy, h)
    y -= n * TABLE_ROW_H

    if stat_rows:
        # 炮孔品位统计：小标题 + 两行（列宽与主表一致）
        y -= 1.8
        sub = "炮孔品位统计（孔数）"
        sub_h = TABLE_TITLE_H * 0.8
        msp.add_text(sub, dxfattribs=dict(attrib, height=sub_h)
                     ).set_placement(
                         (x0 + (total_w - _text_width(sub, sub_h)) / 2.0,
                          y - sub_h))
        y -= TABLE_TITLE_H * 0.8 + 0.5
        m = len(stat_rows)
        for i in range(m + 1):
            yy = y - i * TABLE_ROW_H
            msp.add_line((x0, yy), (x0 + total_w, yy),
                         dxfattribs={"layer": "0", "color": 8, "lineweight": 13})
        for xx in xs:
            msp.add_line((xx, y), (xx, y - m * TABLE_ROW_H),
                         dxfattribs={"layer": "0", "color": 8, "lineweight": 13})
        for i, row in enumerate(stat_rows):
            cy = y - (i + 0.5) * TABLE_ROW_H
            for j, val in enumerate(row):
                cell_text(val, (xs[j] + xs[j + 1]) / 2.0, cy, TABLE_TEXT_H)
        y -= m * TABLE_ROW_H
    return y


def write_dxf(blocks, holes_all, cells, meta, path: Path,
              report_png: Path = None, report_px=None,
              pending=None, composite_blocks=None, merge_gap: float = 4.5,
              check_merge: bool = True, merge_candidates=None,
              draw_composite: bool = False) -> None:
    from ezdxf import new

    doc = new("R2010")
    doc.header["$INSUNITS"] = 6
    for lid, name in (("L1", "0.500-1.000"), ("L2", "1.000-1.500"),
                      ("L3", "1.500-3.000"), ("L4", "3.000-999.000")):
        doc.layers.add(name, color=LEVEL_COLOR[lid])
    for n in ("爆区方格网", "钻孔", "点", BLANK_LAYER, COMPOSITE_LAYER):
        if n not in doc.layers:
            doc.layers.add(n, color=7)
    cn = doc.styles.add("CN_TTF", font="simsunb.ttf")
    cn.dxf.bigfont = ""
    msp = doc.modelspace()

    layer_of = {"L1": "0.500-1.000", "L2": "1.000-1.500",
                "L3": "1.500-3.000", "L4": "3.000-999.000"}
    # 0) 综合图历史矿块（细线参照）+ 当日矿块与综合图合并后的轮廓
    merged_outlines = []
    # 用户 2026-10-15：**最终成果图里不要画综合图的边界**（那 85 条灰线参照），
    # 只保留"当日矿块（含并进来的历史块）"的彩色轮廓。要参照时把 draw_composite 打开。
    if composite_blocks and draw_composite:
        for _, col, p in composite_blocks:
            rings = [p.exterior] + list(p.interiors)
            for r in rings:
                msp.add_lwpolyline([(x, y) for x, y, *_ in r.coords], close=True,
                                   dxfattribs={"layer": COMPOSITE_LAYER, "color": 9})
    # 合并候选：默认全部历史块；给了 merge_candidates 就只用这些
    # （1008：只并"当日矿界真正接上的那一块"，否则会把综合图的大轮廓也吞进来）
    cands = merge_candidates if merge_candidates is not None else composite_blocks
    if check_merge and cands:
        for b in blocks:
            mo, n = merge_outline(b.polygon, cands, merge_gap)
            merged_outlines.append(mo)
            if n:
                print("    %d 号矿块与综合图 %d 个历史矿块合并（间距≤%.1fm）" % (b.no, n, merge_gap))
    else:
        merged_outlines = [b.polygon for b in blocks]
    # 方格相位：人工图以"矿界包围盒左下角"为原点
    if blocks:
        minx = min(b.polygon.bounds[0] for b in blocks if b.polygon is not None)
        miny = min(b.polygon.bounds[1] for b in blocks if b.polygon is not None)
        grid_origin = (minx, miny)
    else:
        grid_origin = (0.0, 0.0)
    # 1) 矿界（彩色闭合线）
    for b, outline in zip(blocks, merged_outlines):
        if outline is None:
            continue
        polys = list(outline.geoms) if outline.geom_type == "MultiPolygon" else [outline]
        for p in polys:
            msp.add_lwpolyline([(x, y) for x, y in p.exterior.coords], close=True,
                               dxfattribs={"layer": layer_of[b.level_id],
                                           "color": LEVEL_COLOR[b.level_id],
                                           "lineweight": 30})

    # 0b) 空白区（孤立有品位孔，缺工程待取样）
    if pending:
        for lid, g in pending:
            for h in g:
                c = Point(h.x, h.y).buffer(3.0, resolution=24)
                msp.add_lwpolyline([(x, y) for x, y in c.exterior.coords], close=True,
                                   dxfattribs={"layer": BLANK_LAYER, "color": 6})
                msp.add_text("%s %.2f  %s" % (h.hid, h.grade_disp, BLANK_NOTE),
                             dxfattribs={"layer": BLANK_LAYER, "color": 6,
                                         "height": 0.8, "style": "CN_TTF"},
                             ).set_placement((h.x - 2.28, h.y - 3.2))

    # 2) 1m 方格 + 方格中心品位
    n_grid = 0
    for b in blocks:
        if b.polygon is None:
            continue
        color = LEVEL_COLOR[b.level_id]
        for cellp in grid_cells(b.polygon, 1.0, grid_origin):
            msp.add_lwpolyline([(x, y) for x, y in cellp.exterior.coords], close=True,
                               dxfattribs={"layer": "爆区方格网", "color": color})
            n_grid += 1
            hh = _nearest_hole_grade(cellp, b.holes)
            if hh is not None:
                c = cellp.representative_point()
                msp.add_text("%.2f" % hh.grade_disp,
                             dxfattribs={"layer": "0", "color": color,
                                         "height": 0.1333, "style": "CN_TTF"},
                             ).set_placement((c.x - 0.16, c.y - 0.07))

    # 3) 炮孔符号 + 工程号 + 品位
    for h in holes_all:
        lid = level_id_of(h.grade)
        aci = LEVEL_COLOR.get(lid, 8)     # 废孔 8（灰）
        # 十字：颜色 = 工程号色(138)，半臂 CROSS_HALF
        msp.add_line((h.x - CROSS_HALF, h.y), (h.x + CROSS_HALF, h.y),
                     dxfattribs={"layer": "点", "color": HID_COLOR,
                                 "true_color": HID_TRUE_COLOR})
        msp.add_line((h.x, h.y - CROSS_HALF), (h.x, h.y + CROSS_HALF),
                     dxfattribs={"layer": "点", "color": HID_COLOR,
                                 "true_color": HID_TRUE_COLOR})
        # 轨迹线：向西 TRAIL_LEN，颜色 = 该孔品位档色（废孔 8）
        msp.add_line((h.x, h.y), (h.x - TRAIL_LEN, h.y),
                     dxfattribs={"layer": "钻孔", "color": aci, "lineweight": 35})
        # 工程号
        msp.add_text(h.hid, dxfattribs={"layer": "钻孔", "color": HID_COLOR,
                                        "true_color": HID_TRUE_COLOR,
                                        "height": 0.4, "style": "CN_TTF"},
                     ).set_placement((h.x - 2.28, h.y + 0.40))
        # 品位（分级色）
        msp.add_text("%.2f" % h.grade_disp,
                     dxfattribs={"layer": "钻孔", "color": aci,
                                 "height": 0.7, "style": "CN_TTF"},
                     ).set_placement((h.x - 3.19, h.y - 0.35))

    # 4) 矿块号：斜引线 + 文字（互不重叠）
    label_maxx = -1e18          # 由下面的循环填；第 6 步画报告表时用它避让
    table_rows, table_stat_rows = _table_data(blocks, holes_all)
    table_w = sum(TABLE_COL_W)
    table_h = _table_height(table_rows, table_stat_rows)
    if blocks:
        minx, miny, maxx, maxy = _bounds(holes_all)
        # 报告表占的矩形（第 6 步画的 40 m 宽矢量表）：矿块号不能压上去
        table = (maxx + 3.0, maxy - table_h - 2.0,
                 maxx + 5.0 + table_w + 2.0, maxy + 2.0)
        # 图名占的矩形（第 5 步放在 (minx, maxy+12)）：矿块号也别压上去
        title = "%s平台 %s二次圈矿矿块图" % (meta["platform"], meta["date"])
        title_rect = (minx - 1.0, maxy + 12.0 - 1.0,
                      minx + 5.2 * len(title) + 1.0, maxy + 12.0 + 6.2)

        def hits(x0, y0, half_w, half_h):
            """文字框（x0±half_w, y0±half_h）是否压到东西。"""
            r = (x0 - half_w, y0 - half_h, x0 + half_w, y0 + half_h)
            blockers = []
            if table is not None:
                blockers.append(table)
            if title_rect is not None:
                blockers.append(title_rect)
            for o in blockers:
                if r[0] < o[2] and r[2] > o[0] and r[1] < o[3] and r[3] > o[1]:
                    return True
            for px, py in placed:
                if abs(x0 - px) < half_w * 2 + 4.0 and abs(y0 - py) < half_h * 2 + 1.0:
                    return True
            return False

        def inside_blocks(x0, y0, half_w, half_h):
            """文字框是否压在"图上画出来的东西"上（人工图把矿块号放在图外，不遮图面）。

            注意要连**合并后的轮廓**（画在图上的那条彩色闭合线，＝矿块 ∪ 接上的历史矿块）
            一起避让——只避让"矿块本体"是不够的：1008 的 1 号块接了历史块之后轮廓变大，
            号就压在那条线里面了（DXF 自检发现）。
            """
            from shapely.geometry import box as _box
            r = _box(x0 - half_w, y0 - half_h, x0 + half_w, y0 + half_h)
            for b in blocks:
                if b.polygon is not None and not b.polygon.is_empty and b.polygon.intersects(r):
                    return True
            for mo in merged_outlines:
                if mo is None or mo.is_empty:
                    continue
                for g in ([mo] if mo.geom_type == "Polygon" else list(mo.geoms)):
                    if g.intersects(r):
                        return True
            return False

        allpts = [pt for b in blocks if b.polygon is not None
                  for pt in b.polygon.convex_hull.exterior.coords]
        gcx = sum(p[0] for p in allpts) / len(allpts)
        gcy = sum(p[1] for p in allpts) / len(allpts)
        placed = []
        label_maxx = -1e18
        for b in blocks:
            if b.polygon is None:
                continue
            # "n号矿块" 4 个字：宽约 4×字高、高约字高
            hw, hh = 2.2 * LABEL_H_M, 0.6 * LABEL_H_M
            # 引线起点取"矿块主体（最大那片）的最深内部点"——representative_point
            # 在多片矿块上可能落到 0.09 m² 的细条里，看起来就像贴着两块交界。
            main = (max(b.polygon.geoms, key=lambda g: g.area)
                    if b.polygon.geom_type == "MultiPolygon" else b.polygon)
            try:
                cen = polylabel(main, tolerance=0.05)
            except Exception:
                cen = main.representative_point()
            dx, dy = cen.x - gcx, cen.y - gcy
            if abs(dx) < 1e-6 and abs(dy) < 1e-6:
                dx, dy = 1.0, 0.0
            L = math.hypot(dx, dy)
            ux, uy = dx / L, dy / L
            d = math.sqrt(b.polygon.area) * 0.9 + 8.0
            # 先按"远离整组矿块质心"的方向放；压到报告图/别的标注就试反向，
            # 最后再沿垂直方向挪，保证标注重开（用户要求"文字不重合就行"、
            # "引线必须从本块边界出发"，人工图是把号放在图外一侧的）。
            tx = ty = None
            dirs = ((ux, uy), (-uy, ux), (uy, -ux), (-ux, -uy))
            for relax in (0, 1):               # relax=1 时允许压在矿块上（兜底）
                for vx, vy in dirs:
                    for k in range(1, 26):
                        cx = cen.x + vx * (d + k * 2.0)
                        cy = cen.y + vy * (d + k * 2.0)
                        if hits(cx, cy, hw, hh):
                            continue
                        if not relax and inside_blocks(cx, cy, hw, hh):
                            continue
                        tx, ty = cx, cy
                        break
                    if tx is not None:
                        break
                if tx is not None:
                    break
            if tx is None:
                tx, ty = cen.x + ux * d, cen.y + uy * d
            placed.append((tx, ty))
            # 记下标注占到的最东边，报告图插到它右边（不然会互相压）
            label_maxx = max(label_maxx, tx + hw)
            # 引线起点：本块内部中心（用户 2026-10-19：不能落在两块交界处）
            bx, by = cen.x, cen.y
            msp.add_line((bx, by), (tx, ty),
                         dxfattribs={"layer": "0", "color": 7})
            msp.add_mtext("%d号矿块" % b.no,
                          dxfattribs={"layer": "0", "style": "CN_TTF",
                                      "char_height": LABEL_H_M}).set_location((tx, ty))

    # 5) 图名
    minx, miny, maxx, maxy = _bounds(holes_all)
    msp.add_text(title,
                 dxfattribs={"layer": "0", "color": 7, "height": 5.0,
                             "style": "CN_TTF"},
                 ).set_placement((minx, maxy + 12))

    # 6) 报告表：矢量 LINE + TEXT（贴在图右侧）
    #    用户 2026-10-19：手机 CAD 看图王看不到外部 PNG 参照，只显示文件路径，
    #    所以成果图里画真正的表格实体；PNG 仍单独生成，供报告/预览使用。
    tbl_x = max(maxx, (label_maxx + 3.0) if label_maxx > -1e17 else maxx) + 5.0
    _draw_report_table(msp, tbl_x, maxy, table_rows, table_stat_rows,
                       "%s平台 %s炮孔数据报告" % (meta["platform"], meta["date"]))
    print("    报告表已绘制（矢量，%d 行 + 品位统计）" % len(table_rows))
    try:
        doc.saveas(str(path))
    except PermissionError:
        alt = path.with_name(path.stem + "_new" + path.suffix)
        doc.saveas(str(alt))
        print("    %s 被占用（CAD 里开着？），已另存为 %s" % (path.name, alt.name))
    print("    方格 %d 个；炮孔 %d 个" % (n_grid, len(holes_all)))


def _bounds(holes):
    xs = [h.x for h in holes]
    ys = [h.y for h in holes]
    return min(xs), min(ys), max(xs), max(ys)


def _nearest_on_boundary(poly: Polygon, tx: float, ty: float):
    best = None
    bd = 1e18
    rings = []
    geoms = list(poly.geoms) if poly.geom_type == "MultiPolygon" else [poly]
    for g in geoms:
        rings.append(g.exterior)
        rings.extend(list(g.interiors))
    for ring in rings:
        for i in range(len(ring.coords) - 1):
            a = ring.coords[i]
            b = ring.coords[i + 1]
            seg = LineString([a, b])
            p = seg.interpolate(seg.project(Point(tx, ty)))
            d = (p.x - tx) ** 2 + (p.y - ty) ** 2
            if d < bd:
                bd, best = d, (p.x, p.y)
    return best if best else (tx, ty)


# ---------------------------------------------------------------- 3ds
def write_3ds(blocks, meta, path: Path,
              composite_blocks=None, merge_gap: float = 4.5,
              merge_candidates=None) -> None:
    """照 3DMine 选择集格式：每个矿块一条字符串，表头末字段为品位类型名。"""
    lines = ["%s, 3DMine String File" % path, "file_version=3DMine_2009"]
    sid = 0
    for b in blocks:
        if b.polygon is None:
            continue
        outline = b.polygon
        cands = merge_candidates if merge_candidates is not None else composite_blocks
        if cands:
            mo, n = merge_outline(b.polygon, cands, merge_gap)
            if mo is not None:
                outline = mo
        sid += 1
        lines.append("%d,7,0,1.00,1.00,1.00,0,0.5,0,Continuous,%s" % (sid, b.label))
        lines.append("0,0,0,0,0,0,0,0,")
        polys = list(outline.geoms) if outline.geom_type == "MultiPolygon" else [outline]
        for p in polys:
            for x, y in p.exterior.coords:
                lines.append("1,%.6f,%.6f,%.6f," % (y, x, 0.0))   # 3ds 顺序 N,E,Z
            lines.append("0,0.000,0.000,0.000,0,,1.00,0.000,0.00,1.00,1.00")
    path.write_text("\n".join(lines), encoding="gbk")
