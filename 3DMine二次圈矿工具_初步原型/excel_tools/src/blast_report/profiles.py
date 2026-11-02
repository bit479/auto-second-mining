"""按矿段取品位分级。

**为什么要分矿段**

金斗山（北部山头 3940/3960）的档位是 ``0.5-1 / 1-1.5 / 1.5-3 / ≥3``，
中心矿段（3550~3640 平台）是 ``0.5-0.8 / 0.8-1 / ≥1``。
以前这套区间写死在 :mod:`schema` 的 ``GRADE_BANDS`` 里，换矿段以后报告汇总仍按金斗山落档：
中心矿段的总计品位 0.60 / 0.90 全被并到 ``0.500-1.000``，档位行数与人工成果对不上，
看起来像"少了一档"，其实是档位边界没跟着矿段走。

**现在**

* 分级放在 ``config/grade_profiles.json``（改配置即可加矿段/调边界，不用改代码）；
  代码里另留一份同样的内置兜底，配置文件丢了、坏了也能跑，只是会告警。
* 汇总时按「当前矿段」选分级，优先级：**手动指定 > 路径关键字 > 源报告档位 > 默认**。
* 边界规则统一为**下限含、上限不含**（``0.500`` 归 ``0.500-0.800``，``0.800`` 归 ``0.800-1.000``）：
  档位由同一串分界值切出来，相邻档共用边界值，既不会重复计数也不会漏。
* 低于该矿段工业品位下限（第一档下限）的品位单列 ``<0.500`` 一档排在最后，
  **不并进最低档**，并在汇总日志里告警 —— 宁可显眼，不要悄悄算错。
"""

from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

__all__ = [
    "BOUNDARY_LOWER_INCLUSIVE", "GradeBand", "GradeProfile", "GradeRegistry",
    "ProfileError", "load_registry", "default_registry", "get_profile",
    "resolve_profile", "parse_range", "canonical_label", "band_of",
    "CONFIG_RELATIVE_PATH", "DEFAULT_PROFILE_KEY",
]

BOUNDARY_LOWER_INCLUSIVE = "lower_inclusive"

CONFIG_RELATIVE_PATH = ("config", "grade_profiles.json")
DEFAULT_PROFILE_KEY = "jindoushan"

# 内置兜底：与 config/grade_profiles.json 保持一致（配置文件不可用时用它）
BUILTIN_PROFILES: tuple[dict, ...] = (
    {
        "key": "jindoushan",
        "name": "金斗山（北部山头 3940/3960）",
        "edges": [0.0, 0.5, 1.0, 1.5, 3.0, 999.0],
        "keywords": ["金斗山", "北部山头", "南部山头", "bs-", "ns-"],
        "note": "0.000-0.500 为废石档，一并参与汇总（历史成果就是这么出的，保持兼容）。",
    },
    {
        "key": "center",
        "name": "中心矿段（3550~3640 平台）",
        "edges": [0.5, 0.8, 1.0, 999.0],
        "keywords": ["中心矿段", "zx-"],
        "note": "工业品位下限 0.5，只有 0.500-0.800 / 0.800-1.000 / 1.000-999.000 三档；"
                "0.5 以下为废石、不进矿块档。",
    },
)

_RANGE_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s*[-~－—～至]\s*(-?\d+(?:\.\d+)?)")
_OPEN_RE = re.compile(r"^\s*([<>≥≤]?=?)\s*(-?\d+(?:\.\d+)?)")


class ProfileError(ValueError):
    """分级配置不合法。"""


# --------------------------------------------------------------------------
# 数值 / 档位文本
# --------------------------------------------------------------------------

def parse_range(text: Any) -> tuple[float, float]:
    """解析品位档文本，返回 ``(下限, 上限)``。

    支持 ``"0.500-0.800"`` / ``"0.5~0.8"`` / ``"≥1.000"`` / ``"3 以上"`` / ``"<0.500"``。
    认不出来返回 ``(-inf, -inf)``，排序时排在最末。
    """
    s = str(text or "").strip()
    s = s.translate({i: i - 0xFEE0 for i in range(0xFF01, 0xFF5F)})   # 全角→半角
    s = s.replace("，", ",").replace(" ", "")

    m = _RANGE_RE.search(s)
    if m:
        low, high = float(m.group(1)), float(m.group(2))
        return (min(low, high), max(low, high))

    m = _OPEN_RE.search(s)
    if m:
        sign, value = m.group(1), float(m.group(2))
        if s[:1] in ("<", "≤"):
            return (-math.inf, value)
        return (value, math.inf)
    return (-math.inf, -math.inf)


def canonical_label(text: Any) -> str:
    """把各种写法的档位归一成 ``0.500-0.800`` / ``≥1.000`` / ``<0.500``，用于比对。"""
    low, high = parse_range(text)
    if low == -math.inf and high == -math.inf:
        return str(text or "").strip()
    if low == -math.inf:
        return "<%.3f" % high
    if high == math.inf:
        return "≥%.3f" % low
    return "%.3f-%.3f" % (low, high)


def _to_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if not (isinstance(value, float) and math.isnan(value)) else None
    try:
        return float(str(value).strip().replace(",", ""))
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------
# 分级模型
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class GradeBand:
    """一个品位档：``low <= 品位 < high``，最后一档的 ``high`` 为 ``None``（无上限）。"""

    low: float
    high: float | None
    label: str
    index: int = 0

    def contains(self, value: float) -> bool:
        return value >= self.low and (self.high is None or value < self.high)


@dataclass(frozen=True)
class GradeProfile:
    """一套品位分级（= 一个矿段）。"""

    key: str
    name: str
    bands: tuple[GradeBand, ...]
    keywords: tuple[str, ...] = ()
    note: str = ""
    boundary: str = BOUNDARY_LOWER_INCLUSIVE

    # ---- 档位 ----

    @property
    def labels(self) -> tuple[str, ...]:
        return tuple(b.label for b in self.bands)

    @property
    def cutoff(self) -> float:
        """工业品位下限（第一档下限）。低于它的品位不属于任何档位。"""
        return self.bands[0].low

    def underflow_label(self) -> str:
        return "<%.3f" % self.cutoff

    def band_of(self, grade: Any) -> str:
        """把品位落到本矿段的档位名称；低于下限返回 ``<0.500``（金斗山为 0，故贴最低档）。"""
        value = _to_float(grade)
        if value is None:
            return ""
        if value < self.cutoff:
            # 金斗山最低档从 0 起，负值/0 贴最低档（沿用旧行为）；中心矿段下限 0.5，单列一档
            return self.bands[0].label if self.cutoff <= 0 else self.underflow_label()
        for band in self.bands:
            if band.high is None or value < band.high:
                return band.label
        return self.bands[-1].label

    def band(self, grade: Any) -> GradeBand | None:
        value = _to_float(grade)
        if value is None:
            return None
        for band in self.bands:
            if band.contains(value):
                return band
        return None

    def owns_label(self, text: Any) -> bool:
        """源报告里的这个档位名，是不是本矿段的写法。"""
        return canonical_label(text) in {canonical_label(x) for x in self.labels}

    # ---- 识别 ----

    def match_score(self, text: str) -> int:
        """路径命中的关键字越多越像本矿段（按下标长度加权）。"""
        lowered = (text or "").lower()
        return sum(len(kw) for kw in self.keywords if kw and kw.lower() in lowered)

    def describe(self) -> str:
        return "%s：%s" % (self.name, " / ".join(self.labels))


@dataclass
class GradeRegistry:
    """所有矿段的分级 + 默认矿段。"""

    profiles: dict[str, GradeProfile] = field(default_factory=dict)
    default_key: str = DEFAULT_PROFILE_KEY
    source: str = "内置"
    warnings: list[str] = field(default_factory=list)

    # ---- 取 ----

    def keys(self) -> list[str]:
        return list(self.profiles.keys())

    def get(self, key: str | None) -> GradeProfile:
        if key and key in self.profiles:
            return self.profiles[key]
        if key:
            raise ProfileError("没有名为 %r 的矿段分级（可选：%s）"
                               % (key, " / ".join(self.keys())))
        return self.default

    @property
    def default(self) -> GradeProfile:
        return self.profiles.get(self.default_key) or next(iter(self.profiles.values()))

    def choices(self) -> list[tuple[str, str]]:
        """``[(key, 显示名), ...]``，给界面下拉框用。"""
        return [(p.key, p.name) for p in self.profiles.values()]


# --------------------------------------------------------------------------
# 载入配置
# --------------------------------------------------------------------------

def config_path() -> Path:
    """``excel_tools/config/grade_profiles.json`` 的绝对路径。"""
    # 单文件 exe：配置要落在可写目录（SM_HOME）里，包内那份只当模板
    home = os.environ.get("SM_HOME")
    if home:
        candidate = Path(home).joinpath(*CONFIG_RELATIVE_PATH)
        if candidate.exists():
            return candidate
    here = Path(__file__).resolve()
    base = here.parents[2] if len(here.parents) > 2 else here.parent
    return base.joinpath(*CONFIG_RELATIVE_PATH)


def _build_profile(raw: dict, position: int) -> GradeProfile:
    key = str(raw.get("key") or "").strip()
    if not key:
        raise ProfileError("第 %d 套分级缺少 key" % (position + 1))

    edges_raw = raw.get("edges")
    if not isinstance(edges_raw, (list, tuple)) or len(edges_raw) < 2:
        raise ProfileError("%s：edges 至少要有 2 个分界值" % key)
    edges: list[float] = []
    for item in edges_raw:
        value = _to_float(item)
        if value is None:
            raise ProfileError("%s：edges 里有非数字 %r" % (key, item))
        if edges and value <= edges[-1]:
            raise ProfileError("%s：edges 必须严格递增（%r 不大于 %r）" % (key, value, edges[-1]))
        edges.append(value)

    bands: list[GradeBand] = []
    for i in range(len(edges) - 1):
        low, high_edge = edges[i], edges[i + 1]
        last = i == len(edges) - 2
        bands.append(GradeBand(
            low=low,
            high=None if last else high_edge,       # 最后一档无上限，上限值只用于显示
            label="%.3f-%.3f" % (low, high_edge),
            index=i,
        ))

    keywords = tuple(str(k).strip() for k in (raw.get("keywords") or []) if str(k).strip())
    boundary = str(raw.get("boundary") or BOUNDARY_LOWER_INCLUSIVE)
    if boundary != BOUNDARY_LOWER_INCLUSIVE:
        raise ProfileError("%s：暂只支持 boundary=%s（下限含、上限不含）"
                           % (key, BOUNDARY_LOWER_INCLUSIVE))
    return GradeProfile(
        key=key,
        name=str(raw.get("name") or key),
        bands=tuple(bands),
        keywords=keywords,
        note=str(raw.get("note") or ""),
        boundary=boundary,
    )


def build_registry(raw: dict, source: str = "内置") -> GradeRegistry:
    profiles_raw = raw.get("profiles")
    if not isinstance(profiles_raw, (list, tuple)) or not profiles_raw:
        raise ProfileError("profiles 不能为空")

    profiles: dict[str, GradeProfile] = {}
    for i, item in enumerate(profiles_raw):
        if not isinstance(item, dict):
            raise ProfileError("profiles[%d] 不是对象" % i)
        profile = _build_profile(item, i)
        if profile.key in profiles:
            raise ProfileError("矿段 key 重复：%s" % profile.key)
        profiles[profile.key] = profile

    default_key = str(raw.get("default") or "").strip() or next(iter(profiles))
    if default_key not in profiles:
        raise ProfileError("default=%r 不在 profiles 里" % default_key)
    boundary = str(raw.get("boundary") or BOUNDARY_LOWER_INCLUSIVE)
    if boundary != BOUNDARY_LOWER_INCLUSIVE:
        raise ProfileError("顶层 boundary 只支持 %s" % BOUNDARY_LOWER_INCLUSIVE)
    return GradeRegistry(profiles=profiles, default_key=default_key, source=source)


_REGISTRY_CACHE: dict[str, GradeRegistry] = {}


def load_registry(path: str | os.PathLike | None = None, *, reload: bool = False) -> GradeRegistry:
    """读分级配置；读不到/写坏了就回落到内置那份，并把原因记在 ``warnings`` 里。"""
    target = Path(path) if path else config_path()
    cache_key = str(target)
    if not reload and cache_key in _REGISTRY_CACHE:
        return _REGISTRY_CACHE[cache_key]

    registry: GradeRegistry
    try:
        raw = json.loads(target.read_text(encoding="utf-8-sig"))
        if not isinstance(raw, dict):
            raise ProfileError("顶层不是 JSON 对象")
        registry = build_registry(raw, source=str(target))
    except FileNotFoundError:
        registry = build_registry({"default": DEFAULT_PROFILE_KEY,
                                   "profiles": list(BUILTIN_PROFILES)}, source="内置")
        registry.warnings.append("没找到分级配置 %s，已用内置分级" % target)
    except (OSError, ValueError) as exc:      # ProfileError 也是 ValueError
        registry = build_registry({"default": DEFAULT_PROFILE_KEY,
                                   "profiles": list(BUILTIN_PROFILES)}, source="内置")
        registry.warnings.append("分级配置 %s 不可用（%s），已用内置分级" % (target, exc))

    _REGISTRY_CACHE[cache_key] = registry
    return registry


def default_registry() -> GradeRegistry:
    return load_registry()


def get_profile(key: str | None = None, config: str | None = None) -> GradeProfile:
    """按 key 取分级；``None`` 取默认矿段。"""
    return load_registry(config).get(key)


def band_of(grade: Any, profile: GradeProfile | None = None) -> str:
    return (profile or default_registry().default).band_of(grade)


# --------------------------------------------------------------------------
# 识别当前矿段
# --------------------------------------------------------------------------

def _score_paths(profile: GradeProfile, text: str) -> int:
    return profile.match_score(text)


def _score_labels(profile: GradeProfile, labels: Iterable[str]) -> int:
    own = {canonical_label(x) for x in profile.labels}
    return sum(1 for label in labels if canonical_label(label) in own)


def resolve_profile(explicit: str | None = None,
                    paths: Sequence[str] = (),
                    reports: Sequence[Any] = (),
                    registry: GradeRegistry | None = None) -> tuple[GradeProfile, str]:
    """确定这次汇总用哪套分级，返回 ``(分级, 判断依据)``。

    优先级：手动指定 → 路径关键字 → 源报告里的档位名 → 配置里的默认矿段。
    """
    reg = registry or default_registry()
    key = (explicit or "").strip()
    if key and key.lower() not in ("auto", "自动"):
        return reg.get(key), "手动指定"

    # ① 路径关键字
    text = "\n".join(str(p) for p in paths if p)
    if text:
        scored = [(_score_paths(p, text), p) for p in reg.profiles.values()]
        best = max((s for s, _ in scored), default=0)
        winners = [p for s, p in scored if s == best and s > 0]
        if len(winners) == 1:
            hit = [kw for kw in winners[0].keywords if kw.lower() in text.lower()]
            return winners[0], "按路径识别（含「%s」）" % "、".join(hit)

    # ② 源报告里的档位名
    labels: list[str] = []
    for rep in reports:
        for rec in getattr(rep, "records", ()) or ():
            label = str(getattr(rec, "grade_type", "") or "").strip()
            if label:
                labels.append(label)
    if labels:
        scored = [(_score_labels(p, labels), p) for p in reg.profiles.values()]
        best = max((s for s, _ in scored), default=0)
        winners = [p for s, p in scored if s == best and s > 0]
        if len(winners) == 1:
            return winners[0], "按源报告档位识别（%d/%d 档命中）" % (best, len(winners[0].bands))
        if best == 0:
            unknown = sorted({str(x) for x in labels})
            return reg.default, "默认（源报告档位 %s 不在任何已知分级里）" % "、".join(unknown[:4])

    return reg.default, "默认（路径里没认到矿段）"
