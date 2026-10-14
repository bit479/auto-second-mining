"""炮孔数据库 .xls 的并入。

读单日 xls 的三张表，把总表里还没有的孔（按工程号判重）追加到总表对应表的末尾。

写回用 ``xlutils``：先把总表原始 BIFF 结构整体复制成可写的 xlwt 簿，
因此字体、数字格式、列宽、其余工作表都被原样保留；新增行直接沿用
"该列最后一个数据单元格"的样式，视觉上与既有数据完全一致。
"""

from __future__ import annotations

import os
from typing import Any

import xlrd
from xlutils.filter import XLRDReader, XLWTWriter, process

from .schema import (DB_KEY_COLUMNS, DB_TABLES, DB_TEXT_COLUMNS, KINDS,
                     normalize_key)

__all__ = ["read_xls_sheets", "merge_xls"]

_CELL_TEXT = 1
_CELL_NUMBER = 2
_CELL_DATE = 3
_CELL_BOOL = 4


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


def read_xls_sheets(path: str, *, with_formatting: bool = False) -> dict[str, dict]:
    """读出 xls 里 ``DB_TABLES`` 涉及的表。

    返回 ``{表名: {"header": [...], "rows": [{列: 值}], "raw": [[...]], "last_content_row": int}}``
    """
    book = xlrd.open_workbook(path, formatting_info=with_formatting)
    out: dict[str, dict] = {}
    for table in DB_TABLES:
        if table not in book.sheet_names():
            continue
        sheet = book.sheet_by_name(table)
        header = [str(v).strip() for v in sheet.row_values(0)]
        index_of = {name: i for i, name in enumerate(header)}
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
        }
    return out


def _plan_tables(src: dict[str, dict], dst: dict[str, dict],
                 skip_duplicates: bool) -> tuple[dict[str, list[list]], dict[str, dict]]:
    """算出每张表要追加的行（raw 值的 list）以及统计信息。"""
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


def _write_additions(dst_path: str, dst: dict[str, dict],
                     additions: dict[str, list[list]]) -> None:
    """在原文件基础上追加行并另存（覆盖 dst_path）。"""
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
                column = DB_TABLES[table][c]
                if value is None:
                    value = ""
                elif column in DB_TEXT_COLUMNS or isinstance(value, str):
                    value = str(value)
                else:
                    try:
                        value = float(value)
                    except (TypeError, ValueError):
                        value = str(value)
                if style is not None:
                    wt_sheet.write(r, c, value, style)
                else:
                    wt_sheet.write(r, c, value)

    wt_book.save(dst_path)


def merge_xls(src_path: str, dst_path: str, *,
              skip_duplicates: bool = True,
              dry_run: bool = False) -> dict:
    """把 ``src_path`` 的炮孔数据并入 ``dst_path``（总表）。"""
    src = read_xls_sheets(src_path)
    dst = read_xls_sheets(dst_path)

    additions, stats = _plan_tables(src, dst, skip_duplicates)
    total_added = sum(s["added"] for s in stats.values())

    if not dry_run and total_added:
        _write_additions(dst_path, dst, additions)

    return {
        "kind": KINDS[0],
        "src": os.path.abspath(src_path),
        "dst": os.path.abspath(dst_path),
        "written": bool(total_added) and not dry_run,
        "added": total_added,
        "tables": stats,
        "sheets": list(dst.keys()),
    }
