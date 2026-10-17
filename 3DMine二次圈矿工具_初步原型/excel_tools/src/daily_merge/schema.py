"""单日数据并入总表 —— 文件命名约定与表结构定义。

这里的每一项都来自北部山头 3940 / 3960 / 3970 平台 2026 的真实数据：
* 炮孔数据库（xls 与 mdb）都含 ``定位表 / 测斜表 / pit_blast`` 三张表，列名完全一致；
* 炮孔数据报告是从上到下依次堆叠的"日报告块"，每块 = 标题行 + 表头行 + 明细 + 小计 + 合计；
* 二次圈矿矿块图（dwg）是**复制**进 ``6、…二次圈矿矿块图`` 文件夹的，不做合并。

目录编号习惯（总目录与单日目录同名，只是单日目录多一层）：

===========================  ==============================
总目录                        单日目录
===========================  ==============================
``1、…炮孔数据库-2026.xls``     ``1、…炮孔数据库1008.xls``
``2、…炮孔数据库-2026.mdb``     ``2、…炮孔数据库1008.mdb``
``3、…炮孔数据报告-2026综合.xlsx``  ``…炮孔数据报告.xlsx``
（无）                         ``5、…二次圈矿矿块图1008.dwg``
``6、…二次圈矿矿块图\\``           （复制到总目录的 6、文件夹，去掉 ``5、`` 前缀）
===========================  ==============================
"""

from __future__ import annotations

import re
from typing import Any

__all__ = [
    "KIND_XLS", "KIND_MDB", "KIND_REPORT", "KIND_DWG", "KINDS",
    "MERGE_KINDS", "COPY_KINDS",
    "KIND_LABELS",
    "DB_TABLES", "DB_KEY_COLUMNS", "DB_TEXT_COLUMNS",
    "REPORT_TOTAL_TOKEN", "REPORT_TOTAL_TOKENS", "REPORT_SUBTOTAL_TOKENS",
    "REPORT_TYPE_COLUMN", "REPORT_TITLE_WORDS", "REPORT_TITLE_PREFIXES",
    "is_report_title",
    "DAY_PATTERNS", "MASTER_PATTERNS", "MAP_FOLDER_PATTERNS", "SKIP_PREFIXES",
    "strip_number_prefix", "map_target_name",
    "normalize_key", "key_of_row", "guess_day_code", "day_code_from_holes",
]

KIND_XLS = "xls"
KIND_MDB = "mdb"
KIND_REPORT = "report"
KIND_DWG = "dwg"
KINDS = (KIND_XLS, KIND_MDB, KIND_REPORT, KIND_DWG)

# 前三类是"并入"（往总表里加数据），最后一类是"复制"（把矿块图搬进 6、文件夹）
MERGE_KINDS = (KIND_XLS, KIND_MDB, KIND_REPORT)
COPY_KINDS = (KIND_DWG,)

KIND_LABELS = {
    KIND_XLS: "炮孔数据库 (.xls/.xlsx)",
    KIND_MDB: "炮孔数据库 (.mdb)",
    KIND_REPORT: "炮孔数据报告 (.xlsx/.xls)",
    KIND_DWG: "二次圈矿矿块图 (.dwg)",
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
REPORT_TOTAL_TOKEN = "合计"      # 汇总块的结束行（新版报告用"合计"）
REPORT_TOTAL_TOKENS = ("合计", "总计")   # 老版报告用"总计"，两种都当块尾
REPORT_SUBTOTAL_TOKENS = ("小计",)
REPORT_TYPE_COLUMN = "类型"      # 表头首列的标志文本

# 日报告块标题的特征：北部山头写「…炮孔数据报告…」，
# 南部山头写「…炮孔数据库报告…」「…矿块报告…」，都用这两条判。
REPORT_TITLE_WORDS = ("报告",)
REPORT_TITLE_PREFIXES = ("炮孔", "矿块")


def is_report_title(text: Any) -> bool:
    """判断某行首列文本是不是一个日报告块的标题。"""
    value = str(text or "").strip()
    if not value:
        return False
    return (any(w in value for w in REPORT_TITLE_WORDS)
            and any(p in value for p in REPORT_TITLE_PREFIXES))

# --------------------------------------------------------------------------
# 文件探测：目录 -> 四类文件
# --------------------------------------------------------------------------
# 单日目录里的文件名形如「1、3940平台 炮孔数据库1008.xls」，
# 报告名形如「3940平台 1008炮孔数据报告.xlsx」（南部山头还有「…炮孔数据库报告…」「…矿块报告…」两种叫法），
# 矿块图形如「5、北部山头3970平台二次圈矿矿块图1011.dwg」（也有写成「5、 」带空格的）。
DAY_PATTERNS = {
    KIND_XLS: ["1、*.xls", "1、*.xlsx"],
    KIND_MDB: ["2、*.mdb"],
    KIND_REPORT: ["*炮孔数据报告*.xlsx", "*炮孔数据报告*.xls",
                  "*炮孔数据库报告*.xlsx", "*炮孔数据库报告*.xls",
                  "*矿块报告*.xlsx", "*矿块报告*.xls"],
    KIND_DWG: ["5、*二次圈矿矿块图*.dwg", "*二次圈矿矿块图*.dwg"],
}

# 总目录里的文件名形如「1、北部山头3940平台 炮孔数据库-2026.xls」。
MASTER_PATTERNS = {
    KIND_XLS: ["1、*.xls", "1、*.xlsx"],
    KIND_MDB: ["2、*.mdb"],
    KIND_REPORT: ["3、*.xlsx", "3、*.xls"],
}

# 总目录里的矿块图**文件夹**：「6、北部山头3940平台二次圈矿矿块图」
MAP_FOLDER_PATTERNS = ["6、*", "6、 *", "*二次圈矿矿块图"]

# Excel / Access 的临时文件前缀，一律跳过
SKIP_PREFIXES = ("~$",)

# 文件名开头的编号前缀：「1、」「5、 」「6、」……
_NUMBER_PREFIX_RE = re.compile(r"^\s*\d+\s*、\s*")

# 工程号形如 BS-3940-1008-P12 / NS-3970-0708-P1 / BL1
_HOLE_DAY_RE = re.compile(r"[A-Z]{2,3}-\d+-(\d{3,4})-", re.IGNORECASE)
_DIR_DAY_RE = re.compile(r"[-_ ](\d{3,4})\s*$")


def strip_number_prefix(name: str) -> str:
    """去掉文件名开头的「N、」前缀（含紧跟的空格）。

    ``5、北部山头3970平台二次圈矿矿块图1011.dwg`` -> ``北部山头3970平台二次圈矿矿块图1011.dwg``
    ``5、 北部山头3940平台二次圈矿矿块图1008.dwg`` -> ``北部山头3940平台二次圈矿矿块图1008.dwg``
    """
    import os

    base = os.path.basename(str(name or "").strip())
    return _NUMBER_PREFIX_RE.sub("", base) or base


def map_target_name(name: str) -> str:
    """矿块图复制到 6、文件夹时用的新文件名（就是去掉编号前缀）。"""
    return strip_number_prefix(name)



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
