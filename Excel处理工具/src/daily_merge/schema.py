"""单日数据并入总表 —— 文件命名约定与表结构定义。

这里的每一项都来自北部山头 3940 / 3960 平台 2026 的真实数据：
* 炮孔数据库（xls 与 mdb）都含 ``定位表 / 测斜表 / pit_blast`` 三张表，列名完全一致；
* 炮孔数据报告是从上到下依次堆叠的"日报告块"，每块 = 标题行 + 表头行 + 明细 + 小计 + 合计。
"""

from __future__ import annotations

import re
from typing import Any

__all__ = [
    "KIND_XLS", "KIND_MDB", "KIND_REPORT", "KINDS",
    "KIND_LABELS",
    "DB_TABLES", "DB_KEY_COLUMNS", "DB_TEXT_COLUMNS",
    "REPORT_TOTAL_TOKEN", "REPORT_TYPE_COLUMN",
    "DAY_PATTERNS", "MASTER_PATTERNS", "SKIP_PREFIXES",
    "normalize_key", "key_of_row", "guess_day_code", "day_code_from_holes",
]

KIND_XLS = "xls"
KIND_MDB = "mdb"
KIND_REPORT = "report"
KINDS = (KIND_XLS, KIND_MDB, KIND_REPORT)

KIND_LABELS = {
    KIND_XLS: "炮孔数据库 (.xls)",
    KIND_MDB: "炮孔数据库 (.mdb)",
    KIND_REPORT: "炮孔数据报告 (.xlsx)",
}

# --------------------------------------------------------------------------
# 炮孔数据库：表名 -> 列（顺序即列顺序）
# --------------------------------------------------------------------------
DB_TABLES = {
    "定位表": ["工程号", "开孔坐标E", "开孔坐标N", "开孔坐标R", "轨迹类型", "最大孔深"],
    "测斜表": ["工程号", "深度", "方位角", "倾角"],
    "pit_blast": ["工程号", "从", "至", "Au"],
}

# 判重用的键列。pit_blast 在 Access 里有 (工程号, 从) 的唯一索引，必须按两列判重。
DB_KEY_COLUMNS = {
    "定位表": ("工程号",),
    "测斜表": ("工程号",),
    "pit_blast": ("工程号", "从"),
}

# 这些列按文本写入（其余按数值写入）
DB_TEXT_COLUMNS = {"工程号", "轨迹类型"}

# --------------------------------------------------------------------------
# 炮孔数据报告
# --------------------------------------------------------------------------
REPORT_TOTAL_TOKEN = "合计"      # 汇总块的结束行
REPORT_TYPE_COLUMN = "类型"      # 表头首列的标志文本

# --------------------------------------------------------------------------
# 文件探测：目录 -> 三类文件
# --------------------------------------------------------------------------
# 单日目录里的文件名形如「1、3940平台 炮孔数据库1008.xls」，
# 报告名形如「3940平台 1008炮孔数据报告.xlsx」。
DAY_PATTERNS = {
    KIND_XLS: ["1、*.xls", "1、*.xlsx"],
    KIND_MDB: ["2、*.mdb"],
    KIND_REPORT: ["*炮孔数据报告*.xlsx", "*炮孔数据报告*.xls"],
}

# 总目录里的文件名形如「1、北部山头3940平台 炮孔数据库-2026.xls」。
MASTER_PATTERNS = {
    KIND_XLS: ["1、*.xls", "1、*.xlsx"],
    KIND_MDB: ["2、*.mdb"],
    KIND_REPORT: ["3、*.xlsx", "3、*.xls"],
}

# Excel / Access 的临时文件前缀，一律跳过
SKIP_PREFIXES = ("~$",)

_HOLE_DAY_RE = re.compile(r"BS-\d+-(\d{3,4})-", re.IGNORECASE)
_DIR_DAY_RE = re.compile(r"[-_ ](\d{3,4})\s*$")


def _norm_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return re.sub(r"[\s\u3000]+", "", str(value)).upper()


def normalize_key(value: Any) -> Any:
    """把判重用的值规范化：文本去空格转大写，数值保留 6 位小数。"""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        return round(float(value), 6)
    text = _norm_text(value)
    if not text:
        return ""
    try:                      # 形如 "11.0" 的数值文本也按数值比较
        return round(float(text), 6)
    except ValueError:
        return text


def key_of_row(row: dict[str, Any], key_columns: tuple[str, ...]) -> tuple:
    return tuple(normalize_key(row.get(c)) for c in key_columns)


def guess_day_code(day_dir: str) -> str:
    """从单日目录名猜日期代号，如「北部山头3940平台-1008」-> ``1008``。"""
    import os

    name = os.path.basename(os.path.normpath(day_dir))
    match = _DIR_DAY_RE.search(name)
    return match.group(1) if match else ""


def day_code_from_holes(holes: list[str]) -> str:
    """兜底：从工程号（BS-3940-1008-P1）里取日期代号。"""
    for hole in holes:
        match = _HOLE_DAY_RE.search(str(hole))
        if match:
            return match.group(1)
    return ""
