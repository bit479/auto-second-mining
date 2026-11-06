# -*- coding: utf-8 -*-
"""字段映射配置（T03.1）。

把「工作表列头 → 标准字段」的映射**配置化**，支持不同 Excel 使用不同表头。

原则：
* **精确匹配**，不做「相似名称」的模糊匹配 —— 含义不明确的字段不能强行映射；
* 无法识别的列头 → 返回未匹配清单，由调用方输出明确提示（`unmapped_column`），
  并允许后续人工配置（`register_schema` / `load_schema`）；
* 默认 schema 只覆盖当前确认过的表头写法，新增写法用注册/覆盖方式扩展，不改默认。
"""
from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# 默认 schema（仅当前确认过的表头写法；不含任何模糊匹配）
# ---------------------------------------------------------------------------
DEFAULT_SCHEMAS: dict[str, dict[str, list[str]]] = {
    # 定位表
    "loc": {
        "hid":        ["工程号", "孔号", "孔名", "hole", "holeid", "hid", "id"],
        "x":          ["开孔坐标e", "坐标e", "东坐标", "孔口x", "x", "e"],
        "y":          ["开孔坐标n", "坐标n", "北坐标", "孔口y", "y", "n"],
        "z":          ["开孔坐标r", "坐标r", "孔口r", "孔口高程", "高程", "z", "r"],
        "depth":      ["最大孔深", "孔深", "深度", "设计孔深", "终孔深", "depth"],
        "trajectory": ["轨迹类型", "轨迹", "孔型", "孔迹", "trajectory"],
    },
    # pit_blast
    "blast": {
        "hid":   ["工程号", "孔号", "孔名", "hole", "holeid", "hid", "id"],
        "frm":   ["从", "起始", "from"],
        "to":    ["至", "终止", "终孔", "to"],
        "grade": ["au", "品位", "金品位", "品位au", "金", "grade"],
    },
    # 测斜表
    "survey": {
        "hid":     ["工程号", "孔号", "孔名", "hole", "holeid", "hid", "id"],
        "depth":   ["深度", "孔深", "最大孔深", "depth"],
        "azimuth": ["方位角", "方位", "azimuth"],
        "dip":     ["倾角", "倾角(度)", "倾角（度）", "dip"],
    },
}

# 工作表名 → 类别（定位表/pit_blast/测斜表）的对应（精确匹配）
SHEET_KINDS: dict[str, tuple[str, ...]] = {
    "loc":    ("定位表",),
    "blast":  ("pit_blast", "品位表", "化验"),
    "survey": ("测斜表",),
}

# 内存注册表：register_schema 覆盖/扩展
_REGISTRY: dict[str, dict] = {k: dict(v) for k, v in DEFAULT_SCHEMAS.items()}


def _norm(s) -> str:
    """列头归一：去空格、去全角、转小写。"""
    t = str(s or "")
    for a, b in ((" ", ""), ("\u3000", ""), ("（", "("), ("）", ")")):
        t = t.replace(a, b)
    return t.lower()


def get_schema(kind: str, schema: dict | None = None) -> dict:
    """返回某个类别的字段→同义词映射。``schema`` 可整体覆盖默认。"""
    if schema and kind in schema:
        return dict(schema[kind])
    return {k: list(v) for k, v in _REGISTRY.get(kind, {}).items()}


def register_schema(kind: str, mapping: dict) -> None:
    """扩展/覆盖某类别的字段映射（仅内存，不落盘）。``mapping`` = {字段: [同义词...]}。"""
    if kind not in _REGISTRY:
        _REGISTRY[kind] = {}
    for field, syns in mapping.items():
        _REGISTRY[kind][field] = [str(s) for s in syns]


def resolve_mapping(header_row: list, kind: str, schema: dict | None = None) -> tuple[dict, list]:
    """把一行表头解析成映射，返回 (``{字段: 列索引}``, 未识别列头列表)。

    - 同义词命中才映射（精确、归一化后比对）；
    - 一个字段命中多列时取第一列；一列命中多字段时取第一个字段；
    - 未识别的**非空**列头进第二返回值，交由调用方提示，绝不静默丢弃。
    """
    field_syns = get_schema(kind, schema)
    # 归一化同义词表：norm(syn) -> field
    lookup: dict[str, str] = {}
    for field, syns in field_syns.items():
        for s in syns:
            lookup.setdefault(_norm(s), field)

    mapping: dict[str, int] = {}
    used_fields: set = set()
    unmatched: list[str] = []
    for c, cell in enumerate(header_row):
        key = _norm(cell)
        if not key:
            continue
        field = lookup.get(key)
        if field is None or field in used_fields:
            if str(cell).strip():
                unmatched.append(str(cell).strip())
            continue
        mapping[field] = c
        used_fields.add(field)
    return mapping, unmatched


def load_schema(name: str) -> dict | None:
    """按名取一个预定义 schema（当前仅 'default' 映射到内置；扩展名可在此登记）。"""
    if name in ("default", None, ""):
        return None          # None = 用内置默认
    return None              # 预留：后续可支持外部 schema 文件
