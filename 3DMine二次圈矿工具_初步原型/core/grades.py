# -*- coding: utf-8 -*-
"""品位分级（按矿段）—— 二次圈矿链路里档位的**唯一来源**。

**为什么要有这个模块**

档位以前散在十来个文件里写死：`oreblocks.LEVELS`、`autoblock._group_by_level`
的四元组、`strip.py` 的三处 `("L4", 3.0, 9e9, ...)`、`deliver` 的层名/色号表、
`run_batch` 的柱状图颜色与文字…… 全部是金斗山那一套
（`0.5-1 / 1-1.5 / 1.5-3 / ≥3`）。换到中心矿段（`0.5-0.8 / 0.8-1 / ≥1`，只有三档）
就全错了：0.85 会被当成 0.5-1 档、块分层与图上图层也跟着错。

现在档位只从 `excel_tools/config/grade_profiles.json` 读（与"炮孔报告汇总"
共用同一份配置，改一处两条链路都跟着变），本模块负责：

* 把配置翻译成"档位列表"（**id 按品位从低到高编号 L1、L2…**，最高档 id 最大）；
* `level_of(grade)`：品位 → (档位 id, 档位名)，低于工业品位下限返回 (None, None)（废孔）；
* `use_for(paths)`：按路径认矿段（`中心矿段` / `zx-` 之类关键字），认不出用默认；
* 层名、短标签、颜色这些展示用的东西一并在本模块给出，别再各处手写。

**兼容**：默认矿段仍是金斗山，档位四元组与旧的 `LEVELS` 完全一致，
所以北部山头的老成果逐格不变（`_probe/test_grades.py` 里有断言）。
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "excel_tools" / "config" / "grade_profiles.json"

# 配置读不到时的兜底（与 config/grade_profiles.json 保持一致）
BUILTIN = {
    "default": "jindoushan",
    "profiles": [
        {"key": "jindoushan", "name": "金斗山（北部山头 3940/3960）",
         "edges": [0.0, 0.5, 1.0, 1.5, 3.0, 999.0], "ore_cutoff": 0.5,
         "keywords": ["金斗山", "北部山头", "南部山头", "bs-", "ns-"]},
        {"key": "center", "name": "中心矿段（3550~3640 平台）",
         "edges": [0.5, 0.8, 1.0, 999.0], "ore_cutoff": 0.5,
         "keywords": ["中心矿段", "zx-"]},
    ],
}

# 颜色按"从低到高"的位置给：青 / 蓝 / 红 / 黄（人工图的习惯）
ACI_BY_INDEX = (4, 5, 1, 2, 7)
RGB_BY_INDEX = ((0, 255, 255), (0, 0, 255), (255, 0, 0), (255, 255, 0), (255, 255, 255))
HEX_BY_INDEX = ("#a9d6d0", "#b4a7d6", "#ffd966", "#f4b183", "#cccccc")

WASTE_ID = "L0"                 # 平均品位低于下限的"整块废石"（人工圈进来的）


@dataclass(frozen=True)
class Band:
    """一个档位：``low <= 品位 < high``（最高档 high 为 None，表示无上限）。"""

    id: str
    low: float
    high: float | None
    label: str
    index: int = 0              # 从低到高的序号（0 = 最低档）

    def contains(self, grade: float) -> bool:
        return grade >= self.low and (self.high is None or grade < self.high)

    @property
    def short(self) -> str:
        """图上/图例用的短标签：``0.5-1`` / ``≥3``（与人工图的写法一致）。"""
        top = self.high if self.high is not None else None
        if top is None:
            return "≥%g" % self.low
        return "%g-%g" % (self.low, top)

    @property
    def aci(self) -> int:
        return ACI_BY_INDEX[min(self.index, len(ACI_BY_INDEX) - 1)]

    @property
    def rgb(self) -> tuple[int, int, int]:
        return RGB_BY_INDEX[min(self.index, len(RGB_BY_INDEX) - 1)]

    @property
    def color(self) -> str:
        return HEX_BY_INDEX[min(self.index, len(HEX_BY_INDEX) - 1)]


@dataclass(frozen=True)
class Profile:
    key: str
    name: str
    bands: tuple[Band, ...]          # 从低到高（只含工业品位以上的档，废石档不算档位）
    ore_cutoff: float = 0.5          # 工业品位下限：低于它的孔是废孔
    keywords: tuple[str, ...] = ()
    note: str = ""

    # ---- 档位 ----

    @property
    def bands_desc(self) -> tuple[Band, ...]:
        """从高到低（体号按这个顺序编：高档在前）。"""
        return tuple(reversed(self.bands))

    @property
    def labels(self) -> tuple[str, ...]:
        return tuple(b.label for b in self.bands)

    @property
    def cutoff(self) -> float:
        """工业品位下限（配置里的 ``ore_cutoff``）。"""
        return self.ore_cutoff

    @property
    def waste_label(self) -> str:
        """整块平均品位都低于下限时用的档位名（报告里要能看见，不能悄悄丢）。"""
        return "<%.3f" % self.cutoff

    def level_of(self, grade: Any) -> tuple[str | None, str | None]:
        value = _to_float(grade)
        if value is None or value < self.ore_cutoff:
            return None, None
        for band in self.bands:
            if band.contains(value):
                return band.id, band.label
        return None, None

    def band_of_id(self, lid: str) -> Band | None:
        for band in self.bands:
            if band.id == lid:
                return band
        return None

    def label_of(self, lid: str) -> str:
        band = self.band_of_id(lid)
        if band is not None:
            return band.label
        return self.waste_label if lid == WASTE_ID else ""

    def band_of_label(self, label: Any) -> Band | None:
        want = _canon(label)
        for band in self.bands:
            if _canon(band.label) == want:
                return band
        return None

    # ---- 兼容旧写法的四元组 ----

    def levels_desc(self) -> list[tuple[str, float, float, str]]:
        """``[(id, 下限, 上限, 档位名), ...]`` 从高到低；最高档上限为 ``inf``。"""
        out = []
        for b in self.bands_desc:
            out.append((b.id, b.low, math.inf if b.high is None else b.high, b.label))
        return out

    def ids_desc(self) -> list[str]:
        return [b.id for b in self.bands_desc]

    def order_map(self, with_waste: bool = False) -> dict[str, int]:
        """``{档位 id: 排序号}``（高档在前）；``with_waste`` 时 ``L0`` 排最后。"""
        out = {lid: i for i, lid in enumerate(self.ids_desc())}
        if with_waste:
            out[WASTE_ID] = len(out)
        return out

    def describe(self) -> str:
        return "%s：%s" % (self.name, " / ".join(self.labels))


def _to_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if not (isinstance(value, float) and math.isnan(value)) else None
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _canon(label: Any) -> str:
    """档位名归一（``0.5-1`` 与 ``0.500-1.000`` 视作同一档，``>=3`` 与 ``≥3.000`` 同理）。"""
    s = str(label or "").strip().replace(" ", "").replace("～", "-").replace("~", "-")
    if "-" in s and not s.startswith("-"):
        a, _, b = s.partition("-")
        try:
            return "%.3f-%.3f" % (float(a), float(b))
        except ValueError:
            return s
    for sign in ("≥", ">=", ">"):
        if s.startswith(sign):
            try:
                return "≥%.3f" % float(s[len(sign):])
            except ValueError:
                return s
    for sign in ("<=", "<"):
        if s.startswith(sign):
            try:
                return "<%.3f" % float(s[len(sign):])
            except ValueError:
                return s
    return s


# --------------------------------------------------------------------------
# 载入配置 / 当前矿段
# --------------------------------------------------------------------------

@dataclass
class Registry:
    profiles: dict[str, Profile] = field(default_factory=dict)
    default_key: str = "jindoushan"
    source: str = "内置"
    warnings: list[str] = field(default_factory=list)

    def get(self, key: str | None) -> Profile:
        if key and key in self.profiles:
            return self.profiles[key]
        return self.default

    @property
    def default(self) -> Profile:
        return self.profiles.get(self.default_key) or next(iter(self.profiles.values()))

    def choices(self) -> list[tuple[str, str]]:
        return [(p.key, p.name) for p in self.profiles.values()]


def _build(raw: dict, source: str) -> Registry:
    profiles: dict[str, Profile] = {}
    for item in raw.get("profiles") or ():
        key = str(item.get("key") or "").strip()
        edges = [_to_float(x) for x in (item.get("edges") or ())]
        if not key or len(edges) < 2 or any(e is None for e in edges):
            raise ValueError("分级配置里有不合法的矿段：%r" % (item,))
        if any(b <= a for a, b in zip(edges, edges[1:])):
            raise ValueError("%s 的 edges 必须严格递增" % key)

        raw_bands = []
        for i in range(len(edges) - 1):
            last = i == len(edges) - 2
            raw_bands.append((edges[i], None if last else edges[i + 1],
                              "%.3f-%.3f" % (edges[i], edges[i + 1])))

        # 工业品位下限：配置里给了就用它（金斗山 0.5 —— 0.000-0.500 是废石档，
        # 只给报告汇总用，圈矿里不算一个档），没给就取最低档下限
        ore_cutoff = _to_float(item.get("ore_cutoff"))
        if ore_cutoff is None:
            ore_cutoff = raw_bands[0][0]

        bands = []
        for low, high, label in raw_bands:
            if low < ore_cutoff - 1e-9:
                continue                      # 低于工业品位下限的档不进圈矿档位
            bands.append(Band(id="L%d" % (len(bands) + 1), low=low, high=high,
                              label=label, index=len(bands)))
        if not bands:
            raise ValueError("%s 的 ore_cutoff 把所有档都滤掉了" % key)

        profiles[key] = Profile(
            key=key,
            name=str(item.get("name") or key),
            bands=tuple(bands),
            ore_cutoff=ore_cutoff,
            keywords=tuple(str(k).strip() for k in (item.get("keywords") or ()) if str(k).strip()),
            note=str(item.get("note") or ""),
        )
    if not profiles:
        raise ValueError("分级配置里没有 profiles")
    default_key = str(raw.get("default") or next(iter(profiles)))
    if default_key not in profiles:
        default_key = next(iter(profiles))
    return Registry(profiles=profiles, default_key=default_key, source=source)


_CACHE: Registry | None = None
_ACTIVE: Profile | None = None
_ACTIVE_REASON: str = ""


def registry(reload: bool = False) -> Registry:
    global _CACHE
    if _CACHE is not None and not reload:
        return _CACHE
    try:
        raw = json.loads(CONFIG.read_text(encoding="utf-8-sig"))
        _CACHE = _build(raw, source=str(CONFIG))
    except FileNotFoundError:
        _CACHE = _build(BUILTIN, source="内置")
        _CACHE.warnings.append("没找到分级配置 %s，已用内置分级" % CONFIG)
    except Exception as exc:  # noqa: BLE001 - 配置写坏了不能把工具带崩
        _CACHE = _build(BUILTIN, source="内置")
        _CACHE.warnings.append("分级配置 %s 不可用（%s），已用内置分级" % (CONFIG, exc))
    return _CACHE


def set_profile(profile: Profile | None, reason: str = "") -> Profile:
    global _ACTIVE, _ACTIVE_REASON
    _ACTIVE = profile or registry().default
    _ACTIVE_REASON = reason
    return _ACTIVE


def active() -> Profile:
    return _ACTIVE or registry().default


def active_reason() -> str:
    return _ACTIVE_REASON


def use_for(paths: Iterable[Any] = (), explicit: str | None = None) -> tuple[Profile, str]:
    """定下这次跑圈矿用哪套分级，返回 ``(分级, 依据)``。

    优先级：显式指定（界面/命令行/参数）→ 路径里的矿段关键字 → 默认矿段。
    """
    reg = registry()
    key = str(explicit or "").strip()
    if key and key.lower() not in ("auto", "自动"):
        profile = reg.get(key)
        set_profile(profile, "手动指定")
        return profile, "手动指定"

    text = "\n".join(str(p) for p in paths if p).lower()
    if text:
        scored = [(sum(len(kw) for kw in p.keywords if kw.lower() in text), p)
                  for p in reg.profiles.values()]
        best = max((s for s, _ in scored), default=0)
        winners = [p for s, p in scored if s == best and s > 0]
        if len(winners) == 1:
            hit = [kw for kw in winners[0].keywords if kw.lower() in text]
            reason = "按路径识别（含「%s」）" % "、".join(hit)
            set_profile(winners[0], reason)
            return winners[0], reason

    set_profile(reg.default, "默认（路径里没认到矿段）")
    return reg.default, "默认（路径里没认到矿段）"


# --------------------------------------------------------------------------
# 便捷函数（模块级，永远跟着"当前矿段"走，不要在别处缓存成常量）
# --------------------------------------------------------------------------

def level_of(grade: Any) -> tuple[str | None, str | None]:
    return active().level_of(grade)


def label_of(lid: str) -> str:
    return active().label_of(lid)


def band_of_label(label: Any) -> Band | None:
    return active().band_of_label(label)


def levels_desc() -> list[tuple[str, float, float, str]]:
    return active().levels_desc()


def ids_desc() -> list[str]:
    return active().ids_desc()


def order_map(with_waste: bool = False) -> dict[str, int]:
    return active().order_map(with_waste)


def cutoff() -> float:
    return active().cutoff


def bands() -> tuple[Band, ...]:
    return active().bands


def bands_desc() -> tuple[Band, ...]:
    return active().bands_desc


def waste_label() -> str:
    return active().waste_label


def choices() -> list[tuple[str, str]]:
    """``[(key, 矿段名), ...]``，给界面下拉框用。"""
    return registry().choices()
