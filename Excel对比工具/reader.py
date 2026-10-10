"""读取 Excel / CSV 为统一的可比较结构。

对外唯一入口: read_workbook(path) -> {sheet_name: [[cell_value, ...], ...]}
- 每个 sheet 是一组「行」，每行是一组「单元格值」(list)
- 读公式值 (data_only=True)，即拿到计算后的结果而非公式文本
- 行可能长短不齐，比较时按最大列数补齐
"""
from __future__ import annotations

import csv
import os

import openpyxl


def read_workbook(path: str):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xlsm"):
        return _read_xlsx(path)
    if ext == ".csv":
        return _read_csv(path)
    if ext == ".xls":
        return _read_xls(path)
    raise ValueError(f"不支持的文件类型: {ext or '(无扩展名)'}，仅支持 .xlsx/.xlsm/.xls/.csv")


def _read_xlsx(path: str):
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    result = {}
    for ws in wb.worksheets:
        rows = [list(r) for r in ws.iter_rows(values_only=True)]
        result[ws.title] = rows
    wb.close()
    return result


def _read_csv(path: str):
    # utf-8-sig 兼容带 BOM 的文件；退化为 gbk 以防中文 csv
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            with open(path, "r", encoding=enc, newline="") as f:
                rows = [list(r) for r in csv.reader(f)]
            return {"Sheet1": rows}
        except UnicodeDecodeError:
            continue
    raise ValueError(f"无法解码 CSV 文件: {path}")


def _read_xls(path: str):
    try:
        import xlrd
    except ImportError:
        raise RuntimeError(
            "读取旧版 .xls 需要 xlrd 库。请先执行: pip install xlrd\n"
            "或把文件另存为 .xlsx 后再对比。"
        )
    book = xlrd.open_workbook(path)
    result = {}
    for sh in book.sheets():
        rows = [
            [sh.cell_value(r, c) for c in range(sh.ncols)] for r in range(sh.nrows)
        ]
        result[sh.name] = rows
    return result
