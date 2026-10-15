"""通用表格变换。

这些函数与具体业务无关，是"Excel 数据处理能力"里可复用的部分：
纵向拼接、跨表列名对齐、去重、按表达式排序、加权平均等。
"""

from __future__ import annotations

from typing import Any, Callable, Iterable, Sequence

from .model import DataTable, to_number

__all__ = [
    "concat",
    "align_columns",
    "dedupe",
    "sort_by_expression",
    "weighted_average",
    "sum_column",
]


def align_columns(tables: Sequence[DataTable],
                  order: Sequence[str] | None = None,
                  fill: Any = None) -> list[DataTable]:
    """把多张表的列对齐到同一套列集合，缺列补 ``fill``。

    列集合 = 所有表列的并集，顺序可显式指定；``order`` 中额外的列也会被保留。
    """
    seen: list[str] = list(order) if order else []
    for t in tables:
        for c in t.columns:
            if c not in seen:
                seen.append(c)
    out = []
    for t in tables:
        rows = [{c: row.get(c, fill) for c in seen} for row in t.rows]
        out.append(DataTable(columns=list(seen), rows=rows, name=t.name, source=t.source))
    return out


def concat(tables: Sequence[DataTable],
           order: Sequence[str] | None = None,
           name: str = "") -> DataTable:
    """纵向拼接多张表（先对齐列，再合并行）。"""
    aligned = align_columns(list(tables), order)
    rows = [r for t in aligned for r in t.rows]
    columns = aligned[0].columns if aligned else list(order or [])
    sources = [t.source for t in aligned if t.source]
    return DataTable(columns=columns, rows=rows, name=name,
                     source=";".join(dict.fromkeys(sources)))


def dedupe(table: DataTable, keys: Sequence[str] | None = None, keep: str = "first") -> DataTable:
    """按指定列去重，默认保留首次出现的行。"""
    keys = list(keys or table.columns)
    seen, rows = set(), []
    source = table.rows if keep == "first" else list(reversed(table.rows))
    for row in source:
        sig = tuple(_norm_key(row.get(k)) for k in keys)
        if sig in seen:
            continue
        seen.add(sig)
        rows.append(row)
    if keep != "first":
        rows.reverse()
    return DataTable(columns=list(table.columns), rows=rows, name=table.name, source=table.source)


def _norm_key(v: Any) -> Any:
    n = to_number(v)
    return round(n, 6) if n is not None else v


def sort_by_expression(table: DataTable, key: Callable[[dict[str, Any]], Any],
                       reverse: bool = False) -> DataTable:
    """按任意表达式排序（DataTable.sort 的语义化别名，便于链式书写）。"""
    return table.sort(key=key, reverse=reverse)


def sum_column(rows: Iterable[dict[str, Any]], column: str) -> float:
    """对某列求和，忽略空值。"""
    return sum(v for v in (to_number(r.get(column)) for r in rows) if v is not None)


def weighted_average(rows: Iterable[dict[str, Any]], value_column: str,
                     weight_column: str) -> float | None:
    """加权平均：sum(value * weight) / sum(weight)。"""
    num = den = 0.0
    for r in rows:
        v, w = to_number(r.get(value_column)), to_number(r.get(weight_column))
        if v is None or w is None:
            continue
        num += v * w
        den += w
    return num / den if den else None
