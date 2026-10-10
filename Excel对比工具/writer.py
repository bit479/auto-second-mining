"""把对比结果写成 Excel 报告。

报告包含 3 类 sheet:
1) 汇总        —— 文件路径、各工作表统计、差异总计
2) 差异清单    —— 逐条列出所有差异(工作表/坐标/类型/A值/B值)，类型列颜色标注
3) 对比_<表名> —— 原表网格，差异单元格高亮(修改=黄/仅A=绿/仅B=红)

高亮配色(浅色，便于阅读):
    changed -> FFF2CC (琥珀黄)
    only_a  -> C6EFCE (绿)
    only_b  -> FFC7CE (红)
"""
from __future__ import annotations

import datetime as _dt

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from compare import type_label

_FILL = {
    "changed": PatternFill("solid", fgColor="FFF2CC"),
    "only_a": PatternFill("solid", fgColor="C6EFCE"),
    "only_b": PatternFill("solid", fgColor="FFC7CE"),
}
_TYPE_FILL = _FILL  # 差异清单的类型列用同样配色

_TITLE_FONT = Font(bold=True, size=14)
_H_FONT = Font(bold=True, color="FFFFFF")
_H_FILL = PatternFill("solid", fgColor="4472C4")
_THIN = Side(style="thin", color="BFBFBF")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)
_WRAP = Alignment(vertical="top", wrap_text=True)


def write_report(result, path_a: str, path_b: str, out_path: str,
                source_a=None, source_b=None):
    """source_a / source_b: 可选 {name: [[...]]}，用于生成「两文件并集」的高亮可视化网格；
    不传则跳过可视化。可视化网格取两文件并集维度，单元格显示 B 的值(无则 A 的值)。"""
    wb = Workbook()
    _write_summary(wb, result, path_a, path_b)
    _write_diff_list(wb, result)
    if source_a is not None or source_b is not None:
        _write_visuals(wb, result, source_a or {}, source_b or {})
    wb.save(out_path)
    return out_path


def _write_summary(wb, result, path_a, path_b):
    ws = wb.active
    ws.title = "汇总"
    ws["A1"] = "Excel 差异对比报告"
    ws["A1"].font = _TITLE_FONT
    ws["A2"] = f"文件A: {path_a}"
    ws["A3"] = f"文件B: {path_b}"
    ws["A4"] = f"生成时间: {_dt.datetime.now():%Y-%m-%d %H:%M:%S}"
    ws["A4"].font = Font(italic=True, color="808080")

    headers = ["工作表", "状态", "A行数", "A列数", "B行数", "B列数",
               "修改", "仅A", "仅B", "差异合计"]
    hrow = 6
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=hrow, column=c, value=h)
        cell.font = _H_FONT
        cell.fill = _H_FILL
        cell.border = _BORDER
        cell.alignment = Alignment(horizontal="center")

    r = hrow + 1
    totals = result["totals"]
    for s in result["sheets"]:
        status = {"both": "两文件都有", "only_in_a": "仅A有", "only_in_b": "仅B有"}.get(
            s["status"], s["status"]
        )
        diff_n = s["changed"] + s["only_a"] + s["only_b"]
        vals = [s["name"], status, s["rows_a"], s["cols_a"], s["rows_b"],
                s["cols_b"], s["changed"], s["only_a"], s["only_b"], diff_n]
        for c, v in enumerate(vals, start=1):
            cell = ws.cell(row=r, column=c, value=v)
            cell.border = _BORDER
        r += 1

    # 总计行
    total_diff = totals["changed"] + totals["only_a"] + totals["only_b"]
    tvals = ["合计", "", "", "", "", "", totals["changed"], totals["only_a"],
             totals["only_b"], total_diff]
    for c, v in enumerate(tvals, start=1):
        cell = ws.cell(row=r, column=c, value=v)
        cell.font = Font(bold=True)
        cell.border = _BORDER
        cell.fill = PatternFill("solid", fgColor="D9E1F2")

    note_row = r + 2
    ws.cell(row=note_row, column=1,
            value=f"说明: 共比较 {totals['compared']} 个非空单元格，"
                  f"其中相等 {totals['equal']} 个；差异 {total_diff} 个"
                  f"（修改 {totals['changed']}、仅A {totals['only_a']}、仅B {totals['only_b']}）。")
    ws.cell(row=note_row, column=1).font = Font(italic=True, color="808080")

    widths = [22, 12, 9, 9, 9, 9, 9, 8, 8, 11]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A7"


def _write_diff_list(wb, result):
    ws = wb.create_sheet("差异清单")
    headers = ["工作表", "坐标", "类型", "A文件值", "B文件值"]
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=c, value=h)
        cell.font = _H_FONT
        cell.fill = _H_FILL
        cell.border = _BORDER
        cell.alignment = Alignment(horizontal="center")

    r = 2
    for s in result["sheets"]:
        for cell_info in s["cells"]:
            ws.cell(row=r, column=1, value=s["name"]).border = _BORDER
            ws.cell(row=r, column=2, value=cell_info["addr"]).border = _BORDER
            tcell = ws.cell(row=r, column=3, value=type_label(cell_info["type"]))
            tcell.border = _BORDER
            tcell.fill = _TYPE_FILL[cell_info["type"]]
            tcell.alignment = Alignment(horizontal="center")
            ws.cell(row=r, column=4, value=_to_text(cell_info["val_a"])).border = _BORDER
            ws.cell(row=r, column=5, value=_to_text(cell_info["val_b"])).border = _BORDER
            for cc in (4, 5):
                ws.cell(row=r, column=cc).alignment = _WRAP
            r += 1

    if r == 2:
        ws.cell(row=2, column=1, value="（无差异）")
    widths = [22, 10, 12, 40, 40]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"


def _write_visuals(wb, result, source_a, source_b):
    for s in result["sheets"]:
        name = s["name"]
        safe = name[:28] if len(name) <= 31 else name[:28] + "…"
        title = f"对比_{safe}"
        # openpyxl 不允许 sheet 名重复
        if title in wb.sheetnames:
            title = f"对比_{safe}_{s['name']}"[:31]
        ws = wb.create_sheet(title)
        rows_a = source_a.get(name, [])
        rows_b = source_b.get(name, [])
        # 收集差异坐标便于快速查表
        mark = {(ci["r"], ci["c"]): ci["type"] for ci in s["cells"]}
        maxr = max(len(rows_a), len(rows_b), 1)
        maxc = max(_maxc(rows_a), _maxc(rows_b), 1)
        for r in range(maxr):
            for c in range(maxc):
                va = _cell_get(rows_a, r, c)
                vb = _cell_get(rows_b, r, c)
                # 显示 B 的值(无则 A 的值)；相等单元格两者内容一致
                disp = vb if _nonempty(vb) else va
                if not _nonempty(disp) and not _nonempty(va) and not _nonempty(vb):
                    continue
                cell = ws.cell(row=r + 1, column=c + 1, value=_to_text(disp))
                cell.border = _BORDER
                t = mark.get((r, c))
                if t:
                    cell.fill = _FILL[t]
        # 列宽自适应(简单截断)
        for c in range(maxc):
            ws.column_dimensions[get_column_letter(c + 1)].width = 16
        ws.freeze_panes = "A1"


def _cell_get(rows, r, c):
    if r < len(rows):
        row = rows[r]
        if c < len(row):
            return row[c]
    return None


def _nonempty(v):
    if v is None:
        return False
    if isinstance(v, str) and v.strip() == "":
        return False
    return True


def _maxc(rows):
    return max((len(r) for r in rows), default=0)


def _to_text(v):
    if v is None:
        return ""
    if isinstance(v, float):
        # 避免 1.0 显示成 1.0 时与整数混淆，保持原值即可
        return v
    return v
