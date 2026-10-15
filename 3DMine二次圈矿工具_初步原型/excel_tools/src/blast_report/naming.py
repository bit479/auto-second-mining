"""从路径推断报告标题与默认输出文件名。

命名约定（与人工成果一致）::

    <矿名><平台号>平台<日期>炮孔数据报告
    例：北部山头3940平台1011炮孔数据报告

* 平台标签从输入/输出路径里形如 ``北部山头3940平台`` 或 ``3940平台`` 的目录段取；
* 日期代号取输出目录名 / 输出文件名 / 输入目录名末尾的 3~4 位数字
  （如 ``...\\Desktop\\3940平台\\1011\\工作表1.xls`` → ``1011``）；
* 路径里没有矿名时补上默认前缀（``北部山头``）。
"""

from __future__ import annotations

import os
import re
from typing import Iterable, Sequence

from .schema import DEFAULT_MINE_PREFIX

__all__ = ["guess_platform_label", "guess_day_code", "guess_title", "default_output_path"]

# 平台标签：可选中文矿名前缀 + 3~4 位平台号 + "平台"
_PLATFORM_RE = re.compile(r"[\u4e00-\u9fff]{0,8}\d{3,4}\s*平台")
_TRAILING_DAY_RE = re.compile(r"[-_ ]*(\d{3,4})\s*$")
_ANY_DAY_RE = re.compile(r"(?<!\d)(\d{3,4})(?!\d)")


def _segments(paths: Iterable[str]) -> list[str]:
    """把若干路径拆成"由深到浅"的目录/文件名段。"""
    out: list[str] = []
    for path in paths:
        if not path:
            continue
        normalized = str(path).replace("\\", "/")
        parts = [p for p in normalized.split("/") if p and p not in (".", "..")]
        # 越靠后的段越具体，优先匹配
        out.extend(reversed(parts))
    return out


def guess_platform_label(paths: Sequence[str]) -> str:
    """猜平台标签，如 ``北部山头3940平台`` / ``3940平台``；找不到返回空串。"""
    for segment in _segments(paths):
        match = _PLATFORM_RE.search(segment)
        if match:
            return re.sub(r"\s+", "", match.group(0))
    return ""


def guess_day_code(paths: Sequence[str], output: str | None = None,
                   platform: str = "") -> str:
    """猜日期代号（3~4 位数字），如 ``1011``。"""
    platform_digits = re.search(r"(\d{3,4})", platform or "")
    platform_number = platform_digits.group(1) if platform_digits else ""

    near: list[str] = []
    if output:
        near.append(os.path.dirname(os.path.abspath(output)))
        near.append(os.path.splitext(os.path.basename(output))[0])
    for path in list(paths)[:2]:
        if path:
            near.append(os.path.dirname(os.path.abspath(str(path))))
            near.append(os.path.splitext(os.path.basename(str(path)))[0])

    for candidate in near:
        base = os.path.basename(candidate) or candidate
        match = _TRAILING_DAY_RE.search(base)
        if match and match.group(1) != platform_number and not match.group(1).startswith("20"):
            return match.group(1)

    for candidate in near:
        for match in _ANY_DAY_RE.finditer(candidate):
            value = match.group(1)
            if value != platform_number and not value.startswith("20"):
                return value
    return ""


def guess_title(inputs: Sequence[str] | None = None,
                output: str | None = None,
                mine_prefix: str | None = None,
                suffix: str = "炮孔数据报告") -> str:
    """推断报告大标题；推不出来返回空串（调用方回落到输出文件名）。"""
    paths = [str(p) for p in (inputs or []) if p] + ([output] if output else [])
    platform = guess_platform_label(paths)
    if not platform:
        return ""

    prefix = mine_prefix or DEFAULT_MINE_PREFIX
    head = "" if platform.startswith(prefix) else prefix
    day = guess_day_code([str(p) for p in (inputs or []) if p], output, platform)
    return "%s%s%s%s" % (head, platform, day, suffix)


def default_output_path(inputs: Sequence[str], title: str = "") -> str:
    """没指定输出路径时的默认落点：第一个输入文件所在目录 + ``<标题>.xlsx``。"""
    paths = [str(p) for p in inputs if p]
    if not paths:
        raise ValueError("没有输入文件，无法推断默认输出路径")
    directory = os.path.dirname(os.path.abspath(paths[0]))
    stem = title or os.path.splitext(os.path.basename(paths[0]))[0]
    return os.path.join(directory, stem + ".xlsx")
