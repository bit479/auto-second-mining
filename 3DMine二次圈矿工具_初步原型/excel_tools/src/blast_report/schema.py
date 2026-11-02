"""炮孔数据报告的字段与品位档定义。

品位档**按矿段**取（金斗山 / 中心矿段各一套），配置见 ``config/grade_profiles.json``，
解析与识别逻辑在 :mod:`profiles`；本模块只做转出与兼容。
"""

from __future__ import annotations

from typing import Any

from .profiles import (BUILTIN_PROFILES, DEFAULT_PROFILE_KEY, GradeProfile,
                       build_registry, get_profile, parse_range)

__all__ = [
    "COL_TYPE", "COL_BODY", "COL_VOLUME", "COL_WEIGHT", "COL_GRADE", "COL_METAL",
    "OUTPUT_COLUMNS", "COLUMN_SYNONYMS", "NUMERIC_COLUMNS",
    "SUMMARY_TOKENS", "parse_grade_range", "grade_sort_key",
    "MODE_TOTAL", "MODE_DETAIL", "MODES", "MODE_LABELS",
    "GRADE_BANDS", "TOTAL_TOKENS", "band_of_grade", "grade_profile",
    "grade_bands", "DEFAULT_MINE_PREFIX", "DEFAULT_PROFILE_KEY",
]

# --------------------------------------------------------------------------
# 品位档解析（实现在 profiles.py，这里转出以保持旧引用可用）
# --------------------------------------------------------------------------
parse_grade_range = parse_range


def grade_sort_key(text: Any) -> tuple:
    """品位档排序键：档次由高到低，同档按下限降序（``<0.500`` 这类兜底档排最后）。"""
    low, high = parse_grade_range(text)
    return (-low, -high)


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
# 品位档区间（按矿段，见 config/grade_profiles.json）
# --------------------------------------------------------------------------
# 判定规则：下限含、上限不含（0.500 归 0.500-0.800，0.800 归 0.800-1.000）；
# 相邻档共用边界值，既不重复计数也不留缝。矿段不同 → 分界值不同：
#
#   金斗山    0.000 / 0.500 / 1.000 / 1.500 / 3.000 / 999   （含 0.000-0.500 废石档）
#   中心矿段  0.500 / 0.800 / 1.000 / 999                   （0.5 以下为废石，不进档）
#
# GRADE_BANDS 只是**内置默认矿段**（金斗山）的档位快照，留着兼容旧引用；
# 实际落档一律走 band_of_grade(值, 矿段分级)，别直接读它。
_BUILTIN_REGISTRY = build_registry({"default": DEFAULT_PROFILE_KEY,
                                    "profiles": list(BUILTIN_PROFILES)}, source="内置")
GRADE_BANDS = tuple((b.low, b.high, b.label) for b in _BUILTIN_REGISTRY.default.bands)

# 默认矿名前缀：路径里找不到形如「北部山头3940平台」的段时补上
DEFAULT_MINE_PREFIX = "北部山头"


def grade_profile(key: str | None = None, config: str | None = None) -> GradeProfile:
    """取某个矿段的分级（``None`` = 配置里的默认矿段）。"""
    return get_profile(key, config)


def grade_bands(profile: GradeProfile | None = None) -> tuple[tuple[float, float | None, str], ...]:
    """某套分级的 ``(下限, 上限, 档位名)`` 列表；不传就用默认矿段。"""
    target = profile or get_profile(None)
    return tuple((b.low, b.high, b.label) for b in target.bands)


def band_of_grade(grade: Any, profile: GradeProfile | None = None) -> str:
    """把一个品位值落到**指定矿段**的档位。

    * 不给 ``profile`` 时用配置里的默认矿段（内置默认是金斗山，与旧行为一致）；
    * 低于该矿段工业品位下限（第一档下限）时，金斗山贴最低档（旧行为），
      中心矿段这类下限 > 0 的矿段返回 ``<0.500`` 单列一档，避免把废石并进矿。
    """
    from ..excel_core.model import to_number

    value = to_number(grade)
    if value is None:
        return ""
    return (profile or get_profile(None)).band_of(value)

