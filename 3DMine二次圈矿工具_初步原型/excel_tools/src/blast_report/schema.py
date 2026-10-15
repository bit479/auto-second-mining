"""炮孔数据报告的字段与品位档定义。"""

from __future__ import annotations

import math
import re
from typing import Any

__all__ = [
    "COL_TYPE", "COL_BODY", "COL_VOLUME", "COL_WEIGHT", "COL_GRADE", "COL_METAL",
    "OUTPUT_COLUMNS", "COLUMN_SYNONYMS", "NUMERIC_COLUMNS",
    "SUMMARY_TOKENS", "parse_grade_range", "grade_sort_key",
    "MODE_TOTAL", "MODE_DETAIL", "MODES", "MODE_LABELS",
    "GRADE_BANDS", "TOTAL_TOKENS", "band_of_grade", "DEFAULT_MINE_PREFIX",
]

# 业务标准列名
COL_TYPE = "类型"
COL_BODY = "体号"
COL_VOLUME = "体积"
COL_WEIGHT = "重量"
COL_GRADE = "平均品位(Au)"
COL_METAL = "金属量"

# 输出表头（3DMine 报告版式）
OUTPUT_COLUMNS = [COL_TYPE, COL_BODY, COL_VOLUME, COL_WEIGHT, COL_GRADE, "金属量（百克）"]

# 同义词归一：键为可能出现的写法，值为标准列名
COLUMN_SYNONYMS = {
    COL_TYPE: COL_TYPE,
    "类别": COL_TYPE,
    "品位档": COL_TYPE,
    "品位区间": COL_TYPE,
    "品位分级": COL_TYPE,
    "分级": COL_TYPE,
    "等级": COL_TYPE,
    "区间": COL_TYPE,
    "类型区间": COL_TYPE,

    COL_BODY: COL_BODY,
    "矿块号": COL_BODY,
    "块号": COL_BODY,
    "矿体号": COL_BODY,
    "体编号": COL_BODY,
    "编号": COL_BODY,

    COL_VOLUME: COL_VOLUME,
    "体积m3": COL_VOLUME,
    "体积(m3)": COL_VOLUME,
    "体积（m3）": COL_VOLUME,
    "体积m³": COL_VOLUME,

    COL_WEIGHT: COL_WEIGHT,
    "重量t": COL_WEIGHT,
    "重量(t)": COL_WEIGHT,
    "重量（t）": COL_WEIGHT,
    "矿石量": COL_WEIGHT,
    "矿石量(t)": COL_WEIGHT,

    COL_GRADE: COL_GRADE,
    "平均品位": COL_GRADE,
    "平均品位（Au）": COL_GRADE,
    "平均品位au": COL_GRADE,
    "平均品位(g/t)": COL_GRADE,
    "品位": COL_GRADE,
    "Au品位": COL_GRADE,

    COL_METAL: COL_METAL,
    "金属量（百克）": COL_METAL,
    "金属量(百克)": COL_METAL,
    "金属量（kg）": COL_METAL,
    "金属量(kg)": COL_METAL,
    "金属量kg": COL_METAL,
}

NUMERIC_COLUMNS = [COL_VOLUME, COL_WEIGHT, COL_GRADE, COL_METAL]

# 需要剔除的汇总行文本
SUMMARY_TOKENS = ("小计", "合计", "总计", "共计")

# 金属量单位换算：报告中重量单位为 t，品位为 g/t，金属量记为"百克"
# 金属量(百克) = 重量(t) × 品位(g/t) ÷ 100
METAL_SCALE = 100.0

_RANGE_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s*[-~－—～至]\s*(-?\d+(?:\.\d+)?)")
_SINGLE_RE = re.compile(r"^\s*[<>≥≤]?=?\s*(-?\d+(?:\.\d+)?)")


def parse_grade_range(text: Any) -> tuple[float, float]:
    """解析品位档字符串，返回 (下限, 上限)。

    支持："0.500-1.000"、"1.5~3"、"≥3.000"、"3.000 以上"、"3 以上"。
    无法解析时返回 ``(-inf, -inf)``，排序时排在最末。
    """
    s = str(text or "").strip()
    s = s.translate({i: i - 0xFEE0 for i in range(0xFF01, 0xFF5F)})
    s = s.replace("，", ",").replace(" ", "")

    m = _RANGE_RE.search(s)
    if m:
        low, high = float(m.group(1)), float(m.group(2))
        return (min(low, high), max(low, high))

    m = _SINGLE_RE.search(s)
    if m:
        value = float(m.group(1))
        if s.startswith(("<", "≤")):
            return (-math.inf, value)
        return (value, math.inf)
    return (-math.inf, -math.inf)


def grade_sort_key(text: Any) -> tuple:
    """品位档排序键：档次由高到低，同档按下限降序。"""
    low, high = parse_grade_range(text)
    return (-low, -high)


# --------------------------------------------------------------------------
# 汇总方式
# --------------------------------------------------------------------------
# total  —— 每份源文件的「总计」行整体当成一个矿块（1011 起的新口径）
# detail —— 把每行明细拆出来按品位档归组（0915/0922/1008 的旧口径）
MODE_TOTAL = "total"
MODE_DETAIL = "detail"
MODES = (MODE_TOTAL, MODE_DETAIL)
MODE_LABELS = {
    MODE_TOTAL: "按每个文件的「总计」行汇总",
    MODE_DETAIL: "按明细行汇总",
}
DEFAULT_MODE = MODE_TOTAL

# 报告的"总结行"标志（第一处即汇总块结束位置）
TOTAL_TOKENS = ("总计", "合计", "共计")

# --------------------------------------------------------------------------
# 品位档区间（3DMine 报告口径）
# --------------------------------------------------------------------------
# 判定规则：下限含、上限不含。即 0.500 归入 "0.500-1.000"。
# 最后一个区间上限为 None（表示无上限）。
GRADE_BANDS = (
    (0.0, 0.5, "0.000-0.500"),
    (0.5, 1.0, "0.500-1.000"),
    (1.0, 1.5, "1.000-1.500"),
    (1.5, 3.0, "1.500-3.000"),
    (3.0, None, "3.000-999.000"),
)

# 默认矿名前缀：路径里找不到形如「北部山头3940平台」的段时补上
DEFAULT_MINE_PREFIX = "北部山头"


def band_of_grade(grade: Any) -> str:
    """把一个品位值落到标准档位字符串。落在区间外时贴到最近的一档。"""
    from ..excel_core.model import to_number

    value = to_number(grade)
    if value is None:
        return ""
    for low, high, name in GRADE_BANDS:
        if high is None:
            if value >= low:
                return name
            continue
        if low <= value < high:
            return name
    return GRADE_BANDS[0][2]          # 小于 0.000 的一律贴到最低档

