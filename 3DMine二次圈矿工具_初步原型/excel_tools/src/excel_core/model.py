"""统一数据表模型。

无论来源是 xlsx / xls / csv，读入后一律转成 :class:`DataTable`，
后续所有处理（清洗、分组、聚合、排序、写出）都只面向 DataTable，
上层业务不再关心文件格式。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Iterator, Sequence

__all__ = ["DataTable", "to_number", "to_text", "is_blank"]

_EMPTY_TOKENS = {"", "-", "--", "—", "－", "/", "N/A", "NA", "NULL", "null", "None"}

# 全角字符 -> 半角
_FULLWIDTH = {i: i - 0xFEE0 for i in range(0xFF01, 0xFF5F)}
_FULLWIDTH[0x3000] = 0x0020  # 全角空格


def is_blank(value: Any) -> bool:
    """判断单元格是否为空（含常见占位符）。"""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() in _EMPTY_TOKENS
    return False


def to_text(value: Any) -> str:
    """把任意单元格值规范成干净的字符串。"""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = str(value).strip()
    text = text.translate(_FULLWIDTH)
    return re.sub(r"\s+", " ", text).strip()


def to_number(value: Any) -> float | None:
    """把任意单元格值规范成 float，失败返回 None。

    能处理：千分位逗号、全角数字、百分号、单位后缀（m3 / t / g/t 等）、
    括号负数、中文负号。
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = to_text(value)
    if not text:
        return None

    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1]

    # 去掉单位/货币/空格等非数字字符（保留数字、小数点、负号、科学计数法）
    text = text.replace(",", "").replace("，", "").replace("%", "")
    text = re.sub(r"[^\d\.\-+eE]", "", text)
    if text in ("", "-", "+", ".", "-.", "+."):
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    if text.lstrip("+").startswith("-"):
        negative = True
    return -number if negative else number


@dataclass
class DataTable:
    """一张二维表：列名 + 行字典。

    rows 里每行都是 ``{列名: 值}``，取值时缺失列返回 None，
    这样不同来源的列顺序差异不会影响后续处理。
    """

    columns: list[str] = field(default_factory=list)
    rows: list[dict[str, Any]] = field(default_factory=list)
    name: str = ""
    source: str = ""

    def __len__(self) -> int:
        return len(self.rows)

    def __iter__(self) -> Iterator[dict[str, Any]]:
        return iter(self.rows)

    def __bool__(self) -> bool:
        return bool(self.rows)

    # ---------- 构造 ----------

    @classmethod
    def from_matrix(cls, matrix: Sequence[Sequence[Any]], name: str = "", source: str = "") -> "DataTable":
        """由二维序列构造，第一行为表头。"""
        matrix = [list(row) for row in matrix if any(not is_blank(v) for v in row)]
        if not matrix:
            return cls(name=name, source=source)
        header = [to_text(v) for v in matrix[0]]
        rows = []
        for raw in matrix[1:]:
            rows.append({header[i]: raw[i] if i < len(raw) else None for i in range(len(header))})
        return cls(columns=header, rows=rows, name=name, source=source)

    def with_columns(self, columns: Sequence[str]) -> "DataTable":
        """只保留指定列（缺失列补 None）。"""
        keep = list(columns)
        rows = [{c: row.get(c) for c in keep} for row in self.rows]
        return DataTable(columns=keep, rows=rows, name=self.name, source=self.source)

    # ---------- 行级变换 ----------

    def filter(self, predicate: Callable[[dict[str, Any]], bool]) -> "DataTable":
        return DataTable(
            columns=list(self.columns),
            rows=[r for r in self.rows if predicate(r)],
            name=self.name,
            source=self.source,
        )

    def filter_blank(self, *columns: str) -> "DataTable":
        """丢掉指定列全为空的行。"""
        cols = columns or self.columns
        return self.filter(lambda r: any(not is_blank(r.get(c)) for c in cols))

    def sort(self, key: Callable[[dict[str, Any]], Any], reverse: bool = False) -> "DataTable":
        return DataTable(
            columns=list(self.columns),
            rows=sorted(self.rows, key=key, reverse=reverse),
            name=self.name,
            source=self.source,
        )

    def add_column(self, name: str, func: Callable[[dict[str, Any]], Any]) -> "DataTable":
        """新增/覆盖一列。"""
        columns = list(self.columns)
        if name not in columns:
            columns.append(name)
        rows = []
        for row in self.rows:
            new = dict(row)
            new[name] = func(row)
            rows.append(new)
        return DataTable(columns=columns, rows=rows, name=self.name, source=self.source)

    def cast(self, mapping: dict[str, Callable[[Any], Any]]) -> "DataTable":
        """按 {列名: 转换函数} 就地转换列值。"""
        rows = []
        for row in self.rows:
            new = dict(row)
            for col, fn in mapping.items():
                if col in new:
                    new[col] = fn(new[col])
            rows.append(new)
        return DataTable(columns=list(self.columns), rows=rows, name=self.name, source=self.source)

    def rename(self, mapping: dict[str, str]) -> "DataTable":
        """列名重命名，未列出的列保持原名。"""
        columns = [mapping.get(c, c) for c in self.columns]
        rows = [{mapping.get(k, k): v for k, v in row.items()} for row in self.rows]
        return DataTable(columns=columns, rows=rows, name=self.name, source=self.source)

    def map_columns(self, synonyms: dict[str, str]) -> "DataTable":
        """同义词归一：把各种写法映射到标准列名。

        ``synonyms`` 形如 ``{"类型": "类型", "类别": "类型", "品位档": "类型"}``，
        键为可能出现的写法，值为标准列名；匹配前会去除空格并忽略大小写。
        """
        lookup = {_norm(k): v for k, v in synonyms.items()}
        mapping = {}
        for col in self.columns:
            std = lookup.get(_norm(col))
            if std and std != col:
                mapping[col] = std
        return self.rename(mapping) if mapping else self

    def drop_rows_matching(self, column: str, values: Iterable[str]) -> "DataTable":
        """丢弃某列命中给定文本的行（用于剔除"小计/合计/标题"等辅助行）。"""
        bad = {_norm(v) for v in values}
        return self.filter(lambda r: _norm(to_text(r.get(column))) not in bad)

    # ---------- 分组聚合 ----------

    def group_by(self, *columns: str, key: Callable[[dict[str, Any]], Any] | None = None) -> "GroupedTable":
        if key is None:
            cols = list(columns)

            def key(row):  # noqa: F811
                return tuple(row.get(c) for c in cols)

        buckets: dict[Any, list[dict[str, Any]]] = {}
        order: list[Any] = []
        for row in self.rows:
            k = key(row)
            if k not in buckets:
                buckets[k] = []
                order.append(k)
            buckets[k].append(row)
        return GroupedTable(order=order, buckets=buckets, columns=list(self.columns))

    # ---------- 输出 ----------

    def to_matrix(self, columns: Sequence[str] | None = None) -> list[list[Any]]:
        cols = list(columns or self.columns)
        return [list(cols)] + [[row.get(c) for c in cols] for row in self.rows]

    def describe(self) -> str:
        return "%s  列=%d  行=%d  来源=%s" % (self.name or "表", len(self.columns), len(self.rows), self.source or "-")


@dataclass
class GroupedTable:
    """分组结果：保持首次出现的顺序。"""

    order: list[Any]
    buckets: dict[Any, list[dict[str, Any]]]
    columns: list[str]

    def items(self):
        for k in self.order:
            yield k, self.buckets[k]

    def aggregate(self, spec: dict[str, str | Callable[[list[Any]], Any]]) -> "DataTable":
        """按分组聚合出一张新表。

        ``spec`` 的键是输出列名，值是聚合方式：
        ``"sum"`` / ``"count"`` / ``"first"`` / ``"min"`` / ``"max"`` / ``"mean"``
        或任意自定义函数（接收该列的值列表）。
        """
        out_cols = list(spec.keys())
        rows = []
        for key, rows_in_group in self.items():
            out = {}
            for col, how in spec.items():
                values = [r.get(col) for r in rows_in_group]
                out[col] = _apply_agg(how, values)
            out["__group__"] = key
            rows.append(out)
        return DataTable(columns=out_cols + ["__group__"], rows=rows)


def _apply_agg(how, values):
    if callable(how):
        return how(values)
    nums = [v for v in (to_number(x) for x in values) if v is not None]
    if how == "sum":
        return sum(nums) if nums else None
    if how == "count":
        return len(values)
    if how == "mean":
        return sum(nums) / len(nums) if nums else None
    if how == "min":
        return min(nums) if nums else None
    if how == "max":
        return max(nums) if nums else None
    if how == "first":
        return values[0] if values else None
    raise ValueError("不支持的聚合方式: %r" % (how,))


def _norm(text: Any) -> str:
    return re.sub(r"[\s\u3000]+", "", to_text(text)).lower()
