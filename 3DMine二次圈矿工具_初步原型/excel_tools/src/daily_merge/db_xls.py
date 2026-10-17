"""炮孔数据库（Excel）的并入 —— ``.xls`` 与 ``.xlsx`` 都支持。

读单日的三张表（``定位表 / 测斜表 / pit_blast``），把总表里还没有的孔
（按工程号判重）追加到总表对应表的末尾。

**格式按文件内容判断，不看扩展名**：北部山头那套是 ``.xls``（BIFF），
南部山头那套是 ``.xlsx``，扩展名反过来也照样处理。

* BIFF 总表用 ``xlutils``：先把原始结构整体复制成可写的 xlwt 簿，
  字体、数字格式、列宽、其余工作表都原样保留，新增行沿用最后一行的样式；
* xlsx 总表用 ``openpyxl``：直接在原簿上追加行，同样沿用最后一行的样式。
"""

from __future__ import annotations

import copy as _copy
import os
from typing import Any

import xlrd
from xlutils.filter import XLRDReader, XLWTWriter, process

from ..excel_core.filetype import FMT_XLS, FMT_XLSX, sniff
from .schema import (DB_KEY_COLUMNS, DB_TABLES, DB_TEXT_COLUMNS, KINDS,
                     normalize_key)

__all__ = ["read_sheets", "read_xls_sheets", "merge_xls"]

_CELL_TEXT = 1
_CELL_NUMBER = 2
_CELL_DATE = 3
_CELL_BOOL = 4


# --------------------------------------------------------------------------
# 读取
# --------------------------------------------------------------------------

def _cell_value(sheet, row: int, col: int) -> Any:
    """把 xlrd 单元格转成 Python 值（空 -> None）。"""
    cell = sheet.cell(row, col)
    if cell.ctype == _CELL_TEXT:
        text = cell.value
        return text if text != "" else None
    if cell.ctype in (_CELL_NUMBER, _CELL_DATE):
        return cell.value
    if cell.ctype == _CELL_BOOL:
        return bool(cell.value)
    return None


def _read_xls(path: str, *, with_formatting: bool = False) -> dict[str, dict]:
    book = xlrd.open_workbook(path, formatting_info=with_formatting)
    out: dict[str, dict] = {}
    for table in DB_TABLES:
        if table not in book.sheet_names():
            continue
        sheet = book.sheet_by_name(table)
        header = [str(v).strip() for v in sheet.row_values(0)]
        index_of = {name: i for i, name in enumerate(header) if name}
        rows, raw = [], []
        last_content = 0
        for r in range(1, sheet.nrows):
            values = [_cell_value(sheet, r, c) for c in range(sheet.ncols)]
            raw.append(values)
            if any(v is not None and str(v).strip() != "" for v in values):
                last_content = r
            rows.append({name: (values[i] if i < len(values) else None)
                         for name, i in index_of.items()})
        out[table] = {
            "sheet": sheet,
            "header": header,
            "index_of": index_of,
            "rows": rows,
            "raw": raw,
            "last_content_row": last_content,
            "nrows": sheet.nrows,
            "format": FMT_XLS,
        }
    book.release_resources()
    return out


def _read_xlsx(path: str) -> dict[str, dict]:
    from openpyxl import load_workbook

    wb = load_workbook(path, data_only=True)
    try:
        out: dict[str, dict] = {}
        for table in DB_TABLES:
            if table not in wb.sheetnames:
                continue
            ws = wb[table]
            max_row, max_col = ws.max_row or 1, ws.max_column or 1
            header_row = [ws.cell(1, c).value for c in range(1, max_col + 1)]
            header = ["" if v is None else str(v).strip() for v in header_row]
            index_of = {name: i for i, name in enumerate(header) if name}
            rows, raw = [], []
            last_content = 0
            for r in range(2, max_row + 1):
                values = [ws.cell(r, c).value for c in range(1, max_col + 1)]
                raw.append(values)
                if any(v is not None and str(v).strip() != "" for v in values):
                    last_content = r - 1          # 表头占 0，与 xlrd 口径一致
                rows.append({name: (values[i] if i < len(values) else None)
                             for name, i in index_of.items()})
            out[table] = {
                "sheet": None,
                "header": header,
                "index_of": index_of,
                "rows": rows,
                "raw": raw,
                "last_content_row": last_content,
                "nrows": max_row,
                "format": FMT_XLSX,
            }
        return out
    finally:
        wb.close()


def read_sheets(path: str, *, with_formatting: bool = False) -> dict[str, dict]:
    """读出 ``DB_TABLES`` 涉及的表，自动适配 xls / xlsx。

    返回 ``{表名: {"header", "index_of", "rows", "raw", "last_content_row", "nrows", "format"}}``
    """
    if sniff(path) == FMT_XLSX:
        return _read_xlsx(path)
    return _read_xls(path, with_formatting=with_formatting)


# 老名字，保持调用方不变（pipeline / tests 都在用）
read_xls_sheets = read_sheets


# --------------------------------------------------------------------------
# 判重与追加计划
# --------------------------------------------------------------------------

def _plan_tables(src: dict[str, dict], dst: dict[str, dict],
                 skip_duplicates: bool) -> tuple[dict[str, list[list]], dict[str, dict]]:
    """算出每张表要追加的行（按 DB_TABLES 列序的 list）以及统计信息。"""
    additions: dict[str, list[list]] = {}
    stats: dict[str, dict] = {}
    for table, columns in DB_TABLES.items():
        src_sheet, dst_sheet = src.get(table), dst.get(table)
        if src_sheet is None or dst_sheet is None:
            stats[table] = {"status": "skip", "reason": "单日或总表缺少该表",
                            "existing": 0, "source": 0, "added": 0,
                            "skipped": 0, "duplicates": []}
            continue

        keys = DB_KEY_COLUMNS[table]
        existing = {tuple(normalize_key(r.get(c)) for c in keys) for r in dst_sheet["rows"]}

        added_rows, duplicates = [], []
        seen_in_batch: set[tuple] = set()
        for row in src_sheet["rows"]:
            sig = tuple(normalize_key(row.get(c)) for c in keys)
            if skip_duplicates and (sig in existing or sig in seen_in_batch):
                duplicates.append(str(row.get(keys[0])))
                continue
            seen_in_batch.add(sig)
            added_rows.append([row.get(c) for c in columns])

        additions[table] = added_rows
        stats[table] = {
            "status": "ok",
            "reason": "",
            "existing": len(dst_sheet["rows"]),
            "source": len(src_sheet["rows"]),
            "added": len(added_rows),
            "skipped": len(duplicates),
            "duplicates": duplicates,
        }
    return additions, stats


def _coerce(value: Any, column: str) -> Any:
    """按列类型整理要写入的值。"""
    if value is None:
        return ""
    if column in DB_TEXT_COLUMNS or isinstance(value, str):
        return str(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return str(value)


# --------------------------------------------------------------------------
# 写回
# --------------------------------------------------------------------------

def _write_additions_xls(dst_path: str, dst: dict[str, dict],
                         additions: dict[str, list[list]]) -> None:
    """BIFF 总表：在原文件基础上追加行并覆盖保存。"""
    book = xlrd.open_workbook(dst_path, formatting_info=True)
    writer = XLWTWriter()
    process(XLRDReader(book, os.path.basename(dst_path)), writer)
    wt_book = writer.output[0][1]

    for table, rows in additions.items():
        if not rows:
            continue
        info = dst[table]
        sheet = book.sheet_by_name(table)
        wt_sheet = wt_book.get_sheet(table)
        start = info["last_content_row"] + 1          # 0-based 的第一空行
        style_row = max(info["last_content_row"], 0)  # 沿用最后一行的样式

        for offset, values in enumerate(rows):
            r = start + offset
            for c, value in enumerate(values):
                if c >= sheet.ncols:
                    continue
                xf_index = sheet.cell(style_row, c).xf_index
                style = writer.style_list[xf_index] if xf_index < len(writer.style_list) else None
                value = _coerce(value, DB_TABLES[table][c])
                if style is not None:
                    wt_sheet.write(r, c, value, style)
                else:
                    wt_sheet.write(r, c, value)

    wt_book.save(dst_path)


def _copy_style(src_cell, dst_cell) -> None:
    dst_cell.font = _copy.copy(src_cell.font)
    dst_cell.border = _copy.copy(src_cell.border)
    dst_cell.fill = _copy.copy(src_cell.fill)
    dst_cell.alignment = _copy.copy(src_cell.alignment)
    dst_cell.protection = _copy.copy(src_cell.protection)
    dst_cell.number_format = src_cell.number_format


def _write_additions_xlsx(dst_path: str, dst: dict[str, dict],
                          additions: dict[str, list[list]]) -> int:
    """xlsx 总表：用 openpyxl 直接追加行（其余工作表、样式原样保留）。

    返回总表里**公式单元格**的个数 —— openpyxl 保存会把公式的缓存值清掉，
    调用方据此给出提示（Excel 打开时会自动重算，所以缓存值只影响"不开 Excel 直接读"的场景）。
    """
    from openpyxl import load_workbook

    wb = load_workbook(dst_path, data_only=False)
    try:
        for table, rows in additions.items():
            if not rows:
                continue
            ws = wb[table]
            info = dst[table]
            start0 = info["last_content_row"] + 1        # 0-based 第一空行
            style_row = max(info["last_content_row"], 0) + 1   # openpyxl 1-based

            for offset, values in enumerate(rows):
                excel_row = start0 + offset + 1
                for c, value in enumerate(values, start=1):
                    cell = ws.cell(excel_row, c)
                    src_cell = ws.cell(style_row, c)
                    if src_cell.has_style:
                        _copy_style(src_cell, cell)
                    value = _coerce(value, DB_TABLES[table][c - 1])
                    cell.value = None if value == "" else value

        formula_cells = sum(
            1
            for sheet in wb.worksheets
            for row in sheet.iter_rows()
            for cell in row
            if isinstance(cell.value, str) and cell.value.startswith("=")
        )
        if formula_cells:
            # 让 Excel 打开时重算，弥补被清掉的缓存值
            try:
                wb.calculation.fullCalcOnLoad = True
            except Exception:  # noqa: BLE001 - 老版本 openpyxl 没有该属性
                pass

        wb.save(dst_path)
        return formula_cells
    finally:
        wb.close()


# --------------------------------------------------------------------------
# 对外入口
# --------------------------------------------------------------------------

def merge_xls(src_path: str, dst_path: str, *,
              skip_duplicates: bool = True,
              dry_run: bool = False) -> dict:
    """把 ``src_path`` 的炮孔数据并入 ``dst_path``（总表），两种格式都支持。"""
    src = read_sheets(src_path)
    dst = read_sheets(dst_path)

    additions, stats = _plan_tables(src, dst, skip_duplicates)
    total_added = sum(s["added"] for s in stats.values())

    notices: list[str] = []
    if not dry_run and total_added:
        if sniff(dst_path) == FMT_XLSX:
            formula_cells = _write_additions_xlsx(dst_path, dst, additions)
            if formula_cells:
                notices.append(
                    "总表是 xlsx，里面有 %d 个公式单元格（如「每日坐标」的 =D1-3960）。"
                    "Excel 保存格式时这些公式的**缓存值**会被清空，打开文件时会自动重算；"
                    "若有别的工具直接读缓存值（不开 Excel），请先用 Excel 打开保存一次。"
                    % formula_cells)
        else:
            _write_additions_xls(dst_path, dst, additions)

    missing = [t for t, s in stats.items() if s["status"] == "skip"]
    return {
        "kind": KINDS[0],
        "src": os.path.abspath(src_path),
        "dst": os.path.abspath(dst_path),
        "written": bool(total_added) and not dry_run,
        "added": total_added,
        "tables": stats,
        "sheets": list(dst.keys()),
        "format": {"src": sniff(src_path), "dst": sniff(dst_path)},
        "missing_tables": missing,
        "notices": notices,
    }
