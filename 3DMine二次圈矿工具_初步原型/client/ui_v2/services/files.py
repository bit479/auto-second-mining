# -*- coding: utf-8 -*-
"""文件相关的纯函数工具（识别平台/日期、找综合图、数 .3ds 闭合线、扫批量目录）。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from . import config, paths

_PLATFORM_RE = re.compile(r"(\d{3,4})\s*平台")
_DATE_RE = re.compile(r"(\d{4})(?=\.\w+$|[^0-9]|$)")


def parse_platform_date(name: str) -> tuple[str, str]:
    """从文件名/文件夹名里取 (平台, 日期)。与原工具的正则完全一致。"""
    s = str(name)
    m = _PLATFORM_RE.search(s)
    platform = m.group(1) if m else ""
    rest = s[m.end():] if m else s
    d = _DATE_RE.search(rest)
    date = d.group(1) if d else ""
    if not platform:
        m2 = re.search(r"(?<!\d)(\d{4})(?!\d)", s)
        if m2 and not date:
            date = m2.group(1)
    return platform, date


def is_coord_txt(path) -> bool:
    try:
        md = config.core_module("make_database")
        return md.looks_like_coord_txt(path)
    except Exception:
        return False


def count_3ds_lines(paths_in: list[str]) -> int:
    """.3ds 里有多少条闭合线（1 条=多半整条矿界；多条=一块一条）。"""
    try:
        strip = config.core_module("strip")
        n = 0
        for p in paths_in:
            try:
                n += len(strip.read_3ds_polylines(Path(p)))
            except Exception:
                continue
        return n
    except Exception:
        return 0


def find_composite(xls: Path) -> Path | None:
    """在数据库同目录/上级目录里找"综合图" DWG。"""
    folder = Path(xls).parent
    cands = (sorted(folder.glob("*综合*.dwg"))
             + sorted(folder.parent.glob("*综合*.dwg")))
    for c in cands:
        if c.exists() and not c.name.startswith("~"):
            return c
    return None


def default_out_dir(xls: Path, platform: str, date: str) -> Path:
    return Path(xls).parent / ("二次圈矿成果_%s_%s" % (platform or "?", date or "?"))


def output_paths(out_dir: Path, platform: str, date: str) -> dict[str, Path]:
    tag = "%s平台 %s" % (platform, date)
    return {
        "tag": tag,
        "xlsx": out_dir / ("%s炮孔数据报告.xlsx" % tag),
        "xls": out_dir / ("%s炮孔数据报告.xls" % tag),
        "png": out_dir / ("%s炮孔数据报告.png" % tag),
        "dxf": out_dir / ("%s二次圈矿矿块图.dxf" % tag),
        "dwg": out_dir / ("%s二次圈矿矿块图_2010.dwg" % tag),
        "tds": out_dir / ("%s矿块边界线.3ds" % tag),
    }


def size_text(p: Path) -> str:
    try:
        n = Path(p).stat().st_size
    except OSError:
        return ""
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return ("%.0f %s" % (n, unit)) if unit == "B" else ("%.1f %s" % (n, unit))
        n /= 1024.0
    return ""


def mtime_text(p: Path) -> str:
    import datetime

    try:
        return datetime.datetime.fromtimestamp(Path(p).stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    except OSError:
        return ""


# ---------------------------------------------------------------- 批量目录


@dataclass
class DayTask:
    folder: Path
    platform: str
    date: str
    xls: Path | None
    composite: Path | None
    status: str = "待执行"
    message: str = ""
    started: str = ""
    ended: str = ""

    @property
    def name(self) -> str:
        return "%s-%s" % (self.platform or "?", self.date or "?")


def scan_day_folders(parent: Path) -> list[DayTask]:
    """扫一个父目录：每个子目录算"一天"，找它的数据库与综合图。"""
    out: list[DayTask] = []
    if not parent.is_dir():
        return out
    for d in sorted(p for p in parent.iterdir() if p.is_dir()):
        if d.name.startswith(("_", ".", "bak", "二次圈矿成果")):
            continue
        dbs = sorted(list(d.glob("1、*.xls")) + list(d.glob("1、*.xlsx")))
        if not dbs:
            continue
        xls = dbs[0]
        plat, date = parse_platform_date(d.name)
        p2, d2 = parse_platform_date(xls.name)
        plat, date = plat or p2, date or d2
        out.append(DayTask(folder=d, platform=plat, date=date, xls=xls,
                           composite=find_composite(xls)))
    return out


def probe_path(name: str) -> Path:
    return paths.probe_dir() / name
