"""自动探测"单日数据 -> 总表"的六个文件。

只要给一个单日目录（形如 ``...\\7、单日数据\\北部山头3940平台-1008``），
就能自动找到同级的 7 份/单日 3 份文件；总目录则向上回溯定位。
"""

from __future__ import annotations

import glob
import os
from dataclasses import dataclass, field

from .schema import (DAY_PATTERNS, KIND_LABELS, KIND_MDB, KIND_REPORT,
                     KIND_XLS, KINDS, MASTER_PATTERNS, SKIP_PREFIXES,
                     guess_day_code)

__all__ = ["DailyMergePlan", "pick_in_dir", "find_day_files", "find_master_files",
           "locate_master_dir", "resolve_plan", "DailyMergeOptions"]


def pick_in_dir(directory: str, patterns: list[str]) -> str | None:
    """在目录里按模式列表依次匹配，返回第一个命中的文件（自然排序后的第一个）。"""
    if not directory or not os.path.isdir(directory):
        return None
    for pattern in patterns:
        hits = [
            p for p in sorted(glob.glob(os.path.join(directory, pattern)))
            if os.path.isfile(p) and not os.path.basename(p).startswith(SKIP_PREFIXES)
        ]
        if hits:
            return hits[0]
    return None


def find_day_files(day_dir: str) -> dict[str, str | None]:
    """在单日目录里找出 xls / mdb / 报告 三类文件。"""
    return {kind: pick_in_dir(day_dir, DAY_PATTERNS[kind]) for kind in KINDS}


def find_master_files(master_dir: str) -> dict[str, str | None]:
    """在总目录里找出 xls / mdb / 综合报告 三类总表。"""
    return {kind: pick_in_dir(master_dir, MASTER_PATTERNS[kind]) for kind in KINDS}


def locate_master_dir(day_dir: str, depth: int = 3) -> str | None:
    """从单日目录向上回溯，找到含三份总表的目录。

    典型层级：``...\\北部山头3940平台2026\\7、单日数据\\北部山头3940平台-1008``，
    总目录在第 2 级父目录上。
    """
    current = os.path.abspath(os.path.normpath(day_dir))
    if os.path.isfile(current):
        current = os.path.dirname(current)
    for _ in range(depth + 1):
        parent = os.path.dirname(current)
        if not parent or parent == current:
            break
        current = parent
        found = find_master_files(current)
        if found[KIND_XLS] or found[KIND_MDB] or found[KIND_REPORT]:
            return current
    return None


@dataclass
class DailyMergeOptions:
    """并入参数。三个 src/dst 都可以留空，留空即自动探测。"""

    day_dir: str | None = None
    master_dir: str | None = None
    src: dict[str, str] = field(default_factory=dict)
    dst: dict[str, str] = field(default_factory=dict)
    day_code: str | None = None
    skip_duplicates: bool = True      # 工程号已存在于总表则跳过
    with_report_appendix: bool = False  # 报告：是否连同附录一起搬进总表
    backup: bool = True               # 写入前把总表备份成 *_并入<日>.bak
    dry_run: bool = False             # 只算不写
    require_all: bool = False         # 三类缺一即报错（默认缺哪类跳过哪类）


@dataclass
class DailyMergePlan:
    """解析后的并入计划。"""

    day_code: str
    day_dir: str | None
    master_dir: str | None
    src: dict[str, str | None]
    dst: dict[str, str | None]
    missing: list[str] = field(default_factory=list)     # 人类可读的缺口说明
    warnings: list[str] = field(default_factory=list)

    @property
    def pairs(self) -> list[tuple[str, str, str]]:
        """返回可执行的 (kind, 单日文件, 总表文件) 列表。"""
        out = []
        for kind in KINDS:
            s, d = self.src.get(kind), self.dst.get(kind)
            if s and d:
                out.append((kind, s, d))
        return out

    @property
    def executable(self) -> bool:
        return bool(self.pairs)

    def describe(self) -> list[str]:
        lines = ["日期代号：%s" % (self.day_code or "(未识别)")]
        lines.append("单日目录：%s" % (self.day_dir or "(未指定)"))
        lines.append("总表目录：%s" % (self.master_dir or "(未指定)"))
        for kind in KINDS:
            s, d = self.src.get(kind), self.dst.get(kind)
            lines.append("  %-18s 单日：%s" % (KIND_LABELS[kind], os.path.basename(s) if s else "— 缺失 —"))
            lines.append("  %-18s 总表：%s" % ("", os.path.basename(d) if d else "— 缺失 —"))
        return lines


def resolve_plan(options: DailyMergeOptions) -> DailyMergePlan:
    """把选项补齐成一个完整计划（自动探测 + 显式覆盖 + 校验）。"""
    warnings: list[str] = []
    missing: list[str] = []

    day_dir = options.day_dir
    master_dir = options.master_dir

    if day_dir and not os.path.isdir(day_dir):
        raise FileNotFoundError("单日目录不存在：%s" % day_dir)

    src: dict[str, str | None] = {k: None for k in KINDS}
    dst: dict[str, str | None] = {k: None for k in KINDS}

    auto_src = find_day_files(day_dir) if day_dir else {k: None for k in KINDS}
    for kind in KINDS:
        src[kind] = options.src.get(kind) or auto_src.get(kind)

    if not master_dir:
        # 优先用单日文件所在目录回溯，其次用单日目录回溯
        anchor = day_dir or next((p for p in src.values() if p), None)
        if anchor:
            master_dir = locate_master_dir(anchor)
        if master_dir:
            warnings.append("总表目录未指定，已自动定位：%s" % master_dir)

    auto_dst = find_master_files(master_dir) if master_dir else {k: None for k in KINDS}
    for kind in KINDS:
        dst[kind] = options.dst.get(kind) or auto_dst.get(kind)

    day_code = options.day_code or (guess_day_code(day_dir) if day_dir else "") or ""

    for kind in KINDS:
        if src[kind] and not os.path.isfile(src[kind]):
            raise FileNotFoundError("单日文件不存在：%s" % src[kind])
        if dst[kind] and not os.path.isfile(dst[kind]):
            raise FileNotFoundError("总表文件不存在：%s" % dst[kind])
        if not src[kind] and not dst[kind]:
            missing.append("%s：单日与总表都未找到" % KIND_LABELS[kind])
        elif not src[kind]:
            missing.append("%s：未找到单日文件" % KIND_LABELS[kind])
        elif not dst[kind]:
            missing.append("%s：未找到总表文件" % KIND_LABELS[kind])

    if not day_code:
        day_code = _day_code_from_src(src) or ""
        if day_code:
            warnings.append("日期代号从工程号推断：%s" % day_code)

    if options.require_all and missing:
        raise FileNotFoundError("缺少必要文件：\n  " + "\n  ".join(missing))

    return DailyMergePlan(
        day_code=day_code,
        day_dir=day_dir,
        master_dir=master_dir,
        src=src,
        dst=dst,
        missing=missing,
        warnings=warnings,
    )


def _day_code_from_src(src: dict[str, str | None]) -> str:
    """从单日 xls/mdb 的首个工程号推断日期代号。"""
    from .schema import day_code_from_holes

    for kind, reader in ((KIND_XLS, _holes_from_xls), (KIND_MDB, _holes_from_mdb)):
        path = src.get(kind)
        if not path:
            continue
        try:
            holes = reader(path)
        except Exception:  # noqa: BLE001 - 推断失败不影响主流程
            continue
        code = day_code_from_holes(holes)
        if code:
            return code
    return ""


def _holes_from_xls(path: str) -> list[str]:
    import xlrd

    book = xlrd.open_workbook(path)
    for name in book.sheet_names():
        sheet = book.sheet_by_name(name)
        if sheet.nrows > 1 and str(sheet.cell_value(0, 0)).strip() == "工程号":
            return [sheet.cell_value(i, 0) for i in range(1, sheet.nrows)]
    return []


def _holes_from_mdb(path: str) -> list[str]:
    from .db_mdb import connect

    conn = connect(path, write=False)
    try:
        cur = conn.cursor()
        cur.execute("SELECT 工程号 FROM [定位表]")
        return [r[0] for r in cur.fetchall()]
    finally:
        conn.close()
