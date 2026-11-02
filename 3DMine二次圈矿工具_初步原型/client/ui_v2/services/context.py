# -*- coding: utf-8 -*-
"""跨页面共享的应用上下文（当前输入、平台、矿段、后台任务）。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal

from . import config, files
from .runner import runner


class AppContext(QObject):
    changed = Signal()             # 当前选择变化（顶栏刷新）
    task_added = Signal()          # 有任务开始/结束（工作台刷新）

    def __init__(self) -> None:
        super().__init__()
        self.xls: str = ""
        self.comp: str = ""
        self.platform: str = ""
        self.date: str = ""
        self.out_dir: str = ""
        self.section: str = "auto"
        self.mode: str = "auto"            # auto / manual / exact
        self.outlines: list[str] = []
        self.dwg_convert: bool = True
        self.merge_composite: bool = True
        self.runner = runner()
        self.state = config.STATE

    # ---------------- 选择 ----------------

    def set_xls(self, path, auto_fill: bool = True) -> None:
        p = Path(path)
        self.xls = str(p)
        if auto_fill:
            plat, date = files.parse_platform_date(p.name)
            self.platform = plat or self.platform
            self.date = date or self.date
            self.out_dir = str(files.default_out_dir(p, self.platform, self.date))
            comp = files.find_composite(p)
            if comp is not None:
                self.comp = str(comp)
            # 炮区文件夹里的 .3ds 自动取用（与原工具一致）
            threes = sorted(p.parent.glob("*.3ds"))
            if threes:
                pick = next((c for c in threes if "分品位" in c.name), threes[0])
                self.outlines = [str(pick)]
                n = files.count_3ds_lines(self.outlines)
                self.mode = "manual" if n > 1 else "exact"
        self.changed.emit()

    def set_section(self, key: str) -> None:
        self.section = key or "auto"
        self.changed.emit()

    def section_label(self) -> str:
        if self.section == "auto":
            key, why = config.resolve_section(
                [self.xls, self.comp, self.out_dir], "auto")
            return "自动识别 → %s" % _profile_name(key)
        return _profile_name(self.section)

    def current_profile(self):
        if self.section == "auto":
            key, _ = config.resolve_section([self.xls, self.comp, self.out_dir], "auto")
            return config.grade_profile(key)
        return config.grade_profile(self.section)

    # ---------------- 任务记录 ----------------

    def record(self, name: str, status: str, detail: str = "", out_dir: str = "") -> None:
        self.state.add_task(name, status, detail, out_dir)
        self.task_added.emit()


def _profile_name(key: str) -> str:
    for p in config.grade_profiles():
        if p.key == key:
            return p.name
    return key


CTX: AppContext | None = None


def context() -> AppContext:
    global CTX
    if CTX is None:
        CTX = AppContext()
    return CTX
