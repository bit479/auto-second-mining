"""单元格级对比核心。

compare_workbooks(wb_a, wb_b) -> {
    "sheets": [ {name, status, rows_a, cols_a, rows_b, cols_b,
                 changed, only_a, only_b,
                 cells: [ {r, c, addr, type, val_a, val_b}, ... ] }, ... ],
    "totals": {changed, only_a, only_b, equal, compared}
}

type 取值:
    "changed"  -> 两文件都有值但不同
    "only_a"   -> 仅文件A有值，B为空
    "only_b"   -> 仅文件B有值，A为空
(相等且非空的单元格不进入 cells 列表，只计入 equal 统计)
"""
from __future__ import annotations

import openpyxl.utils

_TYPE_LABEL = {
    "changed": "修改",
    "only_a": "仅A存在",
    "only_b": "仅B存在",
}


def type_label(t: str) -> str:
    return _TYPE_LABEL.get(t, t)


def normalize_value(v):
    """把单元格值归一化用于比较：空白/None -> None；字符串去首尾空格；其余原样。"""
    if v is None:
        return None
    if isinstance(v, str):
        s = v.strip()
        return s if s != "" else None
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


def _as_number(v):
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.replace(",", "").replace("%", ""))
        except (ValueError, TypeError):
            return None
    return None


def values_equal(a, b) -> bool:
    """比较两值是否相等：数字按数值容差；其余按字符串。"""
    na, nb = normalize_value(a), normalize_value(b)
    if na is None and nb is None:
        return True
    if na is None or nb is None:
        return False
    fa, fb = _as_number(na), _as_number(nb)
    if fa is not None and fb is not None:
        return abs(fa - fb) < 1e-9
    return str(na) == str(nb)


def _cell_get(rows, r, c):
    if r < len(rows):
        row = rows[r]
        if c < len(row):
            return row[c]
    return None


def _addr(r, c) -> str:
    return f"{openpyxl.utils.get_column_letter(c + 1)}{r + 1}"


def compare_workbooks(wb_a, wb_b):
    sheet_names = []
    seen = set()
    for n in list(wb_a.keys()) + list(wb_b.keys()):
        if n not in seen:
            seen.add(n)
            sheet_names.append(n)

    totals = {"changed": 0, "only_a": 0, "only_b": 0, "equal": 0, "compared": 0}
    sheet_results = []

    for name in sheet_names:
        rows_a = wb_a.get(name)
        rows_b = wb_b.get(name)
        cells = []

        if rows_a is None:
            # 仅存在于 B
            maxr = len(rows_b)
            maxc = max((len(r) for r in rows_b), default=0)
            for r in range(maxr):
                for c in range(maxc):
                    vb = _cell_get(rows_b, r, c)
                    if normalize_value(vb) is not None:
                        cells.append(
                            {"r": r, "c": c, "addr": _addr(r, c),
                             "type": "only_b", "val_a": None, "val_b": vb}
                        )
                        totals["only_b"] += 1
            sheet_results.append({
                "name": name, "status": "only_in_b",
                "rows_a": 0, "cols_a": 0, "rows_b": maxr, "cols_b": maxc,
                "changed": 0, "only_a": 0, "only_b": len(cells), "cells": cells,
            })
            continue

        if rows_b is None:
            maxr = len(rows_a)
            maxc = max((len(r) for r in rows_a), default=0)
            for r in range(maxr):
                for c in range(maxc):
                    va = _cell_get(rows_a, r, c)
                    if normalize_value(va) is not None:
                        cells.append(
                            {"r": r, "c": c, "addr": _addr(r, c),
                             "type": "only_a", "val_a": va, "val_b": None}
                        )
                        totals["only_a"] += 1
            sheet_results.append({
                "name": name, "status": "only_in_a",
                "rows_a": maxr, "cols_a": maxc, "rows_b": 0, "cols_b": 0,
                "changed": 0, "only_a": len(cells), "only_b": 0, "cells": cells,
            })
            continue

        # 两文件都有该 sheet
        maxr = max(len(rows_a), len(rows_b))
        maxc = max(
            max((len(r) for r in rows_a), default=0),
            max((len(r) for r in rows_b), default=0),
        )
        n_changed = n_only_a = n_only_b = n_equal = 0
        for r in range(maxr):
            for c in range(maxc):
                va = _cell_get(rows_a, r, c)
                vb = _cell_get(rows_b, r, c)
                na, nb = normalize_value(va), normalize_value(vb)
                if na is None and nb is None:
                    continue
                if na is None:
                    cells.append({"r": r, "c": c, "addr": _addr(r, c),
                                  "type": "only_b", "val_a": None, "val_b": vb})
                    n_only_b += 1
                    totals["only_b"] += 1
                elif nb is None:
                    cells.append({"r": r, "c": c, "addr": _addr(r, c),
                                  "type": "only_a", "val_a": va, "val_b": None})
                    n_only_a += 1
                    totals["only_a"] += 1
                elif not values_equal(va, vb):
                    cells.append({"r": r, "c": c, "addr": _addr(r, c),
                                  "type": "changed", "val_a": va, "val_b": vb})
                    n_changed += 1
                    totals["changed"] += 1
                else:
                    n_equal += 1
                    totals["equal"] += 1
                totals["compared"] += 1

        sheet_results.append({
            "name": name, "status": "both",
            "rows_a": len(rows_a), "cols_a": _max_cols(rows_a),
            "rows_b": len(rows_b), "cols_b": _max_cols(rows_b),
            "changed": n_changed, "only_a": n_only_a, "only_b": n_only_b,
            "cells": cells,
        })

    return {"sheets": sheet_results, "totals": totals}


def _max_cols(rows):
    return max((len(r) for r in rows), default=0)


def diff_count(result) -> int:
    t = result["totals"]
    return t["changed"] + t["only_a"] + t["only_b"]
