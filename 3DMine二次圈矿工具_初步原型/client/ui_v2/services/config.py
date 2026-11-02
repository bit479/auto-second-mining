# -*- coding: utf-8 -*-
"""配置与业务数据的读取门面（不重写任何业务规则，只做展示与保存）。"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import paths

# ---------------------------------------------------------------- core 导入


def _ensure_core() -> None:
    c = str(paths.core_dir())
    if c not in sys.path:
        sys.path.insert(0, c)


def core_module(name: str):
    _ensure_core()
    import importlib

    return importlib.import_module(name)


# ---------------------------------------------------------------- 品位分级


@dataclass
class Band:
    id: str
    label: str
    short: str
    low: float
    high: float | None
    color: str

    @property
    def range_text(self) -> str:
        if self.high is None:
            return "≥%.3f" % self.low
        return "%.3f ~ %.3f" % (self.low, self.high)


@dataclass
class GradeProfile:
    key: str
    name: str
    bands: list[Band] = field(default_factory=list)      # 从低到高
    cutoff: float = 0.5

    @property
    def labels(self) -> list[str]:
        return [b.label for b in self.bands]


def grade_profiles() -> list[GradeProfile]:
    """品位分级（唯一来源：grade_profiles.json，经 core.grades 解析）。"""
    try:
        grades = core_module("grades")
        reg = grades.registry(True)
        out = []
        for p in reg.profiles.values():
            out.append(GradeProfile(
                key=p.key,
                name=p.name,
                cutoff=p.cutoff,
                bands=[Band(id=b.id, label=b.label, short=b.short, low=b.low,
                            high=b.high, color=b.color) for b in p.bands],
            ))
        return out
    except Exception:
        return [GradeProfile(key="jindoushan", name="金斗山（北部山头 3940/3960）",
                             cutoff=0.5,
                             bands=[Band("L1", "0.500-1.000", "0.5-1", 0.5, 1.0, "#a9d6d0"),
                                    Band("L2", "1.000-1.500", "1-1.5", 1.0, 1.5, "#b4a7d6"),
                                    Band("L3", "1.500-3.000", "1.5-3", 1.5, 3.0, "#ffd966"),
                                    Band("L4", "3.000-999.000", "≥3", 3.0, None, "#f4b183")])]


def grade_profile(key: str | None) -> GradeProfile:
    profs = grade_profiles()
    for p in profs:
        if p.key == key:
            return p
    return profs[0]


def grade_choices() -> list[tuple[str, str]]:
    """``[("auto", "自动（按路径识别）"), (key, name), ...]``"""
    return [("auto", "自动（按路径识别）")] + [(p.key, p.name) for p in grade_profiles()]


# ---------------------------------------------------------------- 圈矿参数

PARAM_SPECS = [
    # (键, 中文名, 单位, 是否整数, 说明)
    ("extrude_m", "外推距离", "m", False, "矿界从矿孔向外推的距离"),
    ("zone_link_m", "连接半径", "m", False, "≤这个距离才算同一条矿化带"),
    ("min_fragment_m2", "最小块段面积", "m²", False, "比它小的同档碎片并入邻块"),
    ("merge_gap_m", "接综合图距离", "m", False, "与综合图历史块的最大合并间距"),
    ("seam_join_m", "贴合综合图", "m", False, "≤该间距处矿界改走历史块边界；0=关闭"),
    ("isolated_min_holes", "孤立组最少孔数", "孔", True, "孤立小组达到这个孔数才单独成块"),
    ("ring_alpha_k", "外轮廓兜底 k", "", False, ">0 时把矿孔外轮廓+外推并进矿界"),
    ("block_simplify_m", "块轮廓抽稀", "m", False, "去 Voronoi 锯齿，面积变化≤2%"),
    ("block_smooth_m", "块轮廓圆滑", "m", False, "buffer 外扩/内收，避免断颈"),
    ("density_ore", "矿石容重", "t/m³", False, "重量 = 体积 × 容重"),
    ("density_waste", "废石容重", "t/m³", False, "块内低于工业品位的部分用这个"),
]

PARAM_KEYS = [s[0] for s in PARAM_SPECS]

_CN2KEY = {s[1]: s[0] for s in PARAM_SPECS}


def params_module():
    return core_module("params")


def load_params() -> dict:
    try:
        return params_module().load()
    except Exception:
        return {}


def params_for(platform: str = "", date: str = "") -> dict:
    """按"全局 → 平台 → 炮区"三层解析后的生效参数（与原逻辑完全一致）。"""
    p = params_module()
    try:
        if platform and date:
            return p.for_blast(date, platform=platform)
        if platform:
            return p.for_platform(platform)
        return p.load()
    except Exception:
        return {}


def param_sources(platform: str = "", date: str = "") -> dict[str, str]:
    """每个参数最终来自哪一层：全局默认 / 平台 xxx / 炮区 xxx-xxx。"""
    cfg = load_params()
    out: dict[str, str] = {}
    plat_layer = (cfg.get("platforms") or {}).get(platform) or {}
    blast_layer = (cfg.get("blasts") or {}).get("%s-%s" % (platform, date)) or {} if (platform and date) else {}
    for key in PARAM_KEYS:
        if key in blast_layer:
            out[key] = "炮区 %s-%s" % (platform, date)
        elif key in plat_layer:
            out[key] = "平台 %s" % platform
        elif key in cfg:
            out[key] = "全局默认"
        else:
            out[key] = "内置默认"
    return out


def save_params(values: dict, scope: str = "platform", platform: str = "",
                date: str = "") -> Path:
    """写回 圈矿参数.json。“不允许因为 UI 初始化而被清空” —— 这里只做 update。"""
    p = params_module()
    cfg = p.load()
    if scope == "blast":
        if not (platform and date):
            raise ValueError("存为炮区需要平台号和日期")
        key = "%s-%s" % (platform, date)
        cfg.setdefault("blasts", {}).setdefault(key, {}).update(values)
    elif scope == "platform":
        if not platform:
            raise ValueError("存为平台需要平台号")
        cfg.setdefault("platforms", {}).setdefault(platform, {}).update(values)
    else:
        cfg.update(values)
    return Path(p.save(cfg))


# ---------------------------------------------------------------- 品位分级里"识别到哪个矿段"


def resolve_section(paths_in: list[str], explicit: str = "auto") -> tuple[str, str]:
    """返回 (矿段 key, 依据)；与圈矿子进程用的是同一套规则。"""
    if explicit and explicit != "auto":
        return explicit, "手动指定"
    try:
        grades = core_module("grades")
        prof, why = grades.use_for([str(p) for p in paths_in], explicit=explicit)
        return prof.key, why
    except Exception:
        return "jindoushan", "默认"


# ---------------------------------------------------------------- 最近的记录（UI 状态）


class StateStore:
    """轻量持久化：最近任务、最近成果、上次目录。失败不影响使用。"""

    def __init__(self) -> None:
        self.path = paths.state_file()
        self.data: dict[str, Any] = {}
        try:
            if self.path.exists():
                self.data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            self.data = {}

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=1), encoding="utf-8")
        except Exception:
            pass

    # ---- 通用 ----

    def get(self, key: str, default=None):
        return self.data.get(key, default)

    def set(self, key: str, value) -> None:
        self.data[key] = value
        self.save()

    # ---- 任务与成果 ----

    def add_task(self, name: str, status: str, detail: str = "", out_dir: str = "") -> None:
        items = self.data.setdefault("tasks", [])
        items.insert(0, {
            "name": name, "status": status, "detail": detail,
            "out_dir": out_dir, "time": time.strftime("%Y-%m-%d %H:%M"),
        })
        del items[30:]
        self.save()

    def add_output(self, path: str, kind: str = "") -> None:
        items = self.data.setdefault("outputs", [])
        items.insert(0, {"path": str(path), "kind": kind, "time": time.strftime("%Y-%m-%d %H:%M")})
        del items[30:]
        self.save()

    def tasks(self) -> list[dict]:
        return list(self.data.get("tasks") or [])

    def outputs(self) -> list[dict]:
        return [x for x in (self.data.get("outputs") or []) if Path(x["path"]).exists()]


STATE = StateStore()
