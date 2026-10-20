"""自动探测"单日数据 -> 总表"的四类文件。

只要给一个单日目录（形如 ``...\\7、单日数据\\北部山头3940平台-1008``），
就能自动找到同级的 3 份单日文件 + 1 张矿块图；总目录则向上回溯定位。

四类里前三类（xls / mdb / 报告）是"并入"，第四类（矿块图 dwg）是"复制"到
总目录的 ``6、…二次圈矿矿块图`` 文件夹里。
"""

from __future__ import annotations

import glob
import os
import re
from dataclasses import dataclass, field

from .schema import (DAY_PATTERNS, KIND_DWG, KIND_LABELS, KIND_MDB,
                     KIND_REPORT, KIND_XLS, KINDS, MAP_FOLDER_PATTERNS,
                     MASTER_PATTERNS, MERGE_KINDS, SKIP_PREFIXES,
                     guess_day_code, strip_number_prefix)

__all__ = ["DailyMergePlan", "pick_in_dir", "find_day_files", "find_master_files",
           "find_map_folder", "locate_master_dir", "resolve_plan", "DailyMergeOptions"]


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
    """在单日目录里找出 xls / mdb / 报告 / 矿块图 四类文件。"""
    return {kind: pick_in_dir(day_dir, DAY_PATTERNS[kind]) for kind in KINDS}


def find_master_files(master_dir: str) -> dict[str, str | None]:
    """在总目录里找出 xls / mdb / 综合报告 三份总表（矿块图是文件夹，另走 find_map_folder）。"""
    return {kind: pick_in_dir(master_dir, MASTER_PATTERNS[kind]) for kind in MERGE_KINDS}


def find_map_folder(master_dir: str) -> str | None:
    """在总目录里找「6、…二次圈矿矿块图」文件夹。"""
    if not master_dir or not os.path.isdir(master_dir):
        return None
    for pattern in MAP_FOLDER_PATTERNS:
        hits = [
            p for p in sorted(glob.glob(os.path.join(master_dir, pattern)))
            if os.path.isdir(p) and not os.path.basename(p).startswith(SKIP_PREFIXES)
        ]
        if hits:
            return hits[0]
    return None


def derive_map_folder(master_dir: str, src_dwg: str | None, day_code: str = "") -> str | None:
    """总目录里没有 6、文件夹时，按源图名推一个：``6、北部山头3970平台二次圈矿矿块图``。

    只用于兜底（正常数据里这个文件夹一直存在）。
    """
    if not master_dir or not src_dwg:
        return None
    stem = os.path.splitext(strip_number_prefix(src_dwg))[0]
    if day_code and stem.endswith(day_code):
        stem = stem[: -len(day_code)]
    stem = re.sub(r"[-_ ]*\d{1,4}$", "", stem) or stem
    return os.path.join(master_dir, "6、" + stem)


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
    """并入参数。四个 src/dst 都可以留空，留空即自动探测。"""

    day_dir: str | None = None
    master_dir: str | None = None
    src: dict[str, str] = field(default_factory=dict)
    dst: dict[str, str] = field(default_factory=dict)
    day_code: str | None = None
    skip_duplicates: bool = True      # 工程号已存在于总表则跳过
    with_report_appendix: bool = False  # 报告：是否连同附录一起搬进总表
    with_map: bool = True             # 是否顺手把矿块图复制进 6、文件夹
    backup: bool = True               # 写入前把总表备份成 *_并入<日>.bak
    dry_run: bool = False             # 只算不写
    require_closed: bool = True       # 文件被 Excel/Access/CAD 打开时中止（--allow-open 可关）
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
        """返回可执行的 (kind, 单日文件, 目标) 列表。矿块图的目标是文件夹。"""
        out = []
        for kind in KINDS:
            s, d = self.src.get(kind), self.dst.get(kind)
            if s and d:
                out.append((kind, s, d))
        return out

    @property
    def merge_pairs(self) -> list[tuple[str, str, str]]:
        return [p for p in self.pairs if p[0] in MERGE_KINDS]

    @property
    def executable(self) -> bool:
        return bool(self.pairs)

    def describe(self) -> list[str]:
        lines = ["日期代号：%s" % (self.day_code or "(未识别)")]
        lines.append("单日目录：%s" % (self.day_dir or "(未指定)"))
        lines.append("总表目录：%s" % (self.master_dir or "(未指定)"))
        for kind in KINDS:
            s, d = self.src.get(kind), self.dst.get(kind)
            tail = "(文件夹)" if kind == KIND_DWG else ""
            lines.append("  %-18s 单日：%s" % (KIND_LABELS[kind], os.path.basename(s) if s else "— 缺失 —"))
            lines.append("  %-18s 目标：%s%s" % ("", os.path.basename(d) if d else "— 缺失 —", tail))
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
    if not options.with_map:
        src[KIND_DWG] = None

    if not master_dir:
        # 优先用单日文件所在目录回溯，其次用单日目录回溯
        anchor = day_dir or next((p for p in src.values() if p), None)
        if anchor:
            master_dir = locate_master_dir(anchor)
        if master_dir:
            warnings.append("总表目录未指定，已自动定位：%s" % master_dir)

    auto_dst = find_master_files(master_dir) if master_dir else {k: None for k in MERGE_KINDS}
    for kind in MERGE_KINDS:
        dst[kind] = options.dst.get(kind) or auto_dst.get(kind)

    day_code = options.day_code or (guess_day_code(day_dir) if day_dir else "") or ""

    # 矿块图：目标是总目录里的「6、…二次圈矿矿块图」文件夹；找不到就按源图名兜底推一个
    if src[KIND_DWG]:
        dst[KIND_DWG] = options.dst.get(KIND_DWG) or find_map_folder(master_dir)
        if not dst[KIND_DWG]:
            dst[KIND_DWG] = derive_map_folder(master_dir, src[KIND_DWG], day_code)
            if dst[KIND_DWG]:
                warnings.append("总目录里没找到 6、矿块图文件夹，已按源图名推断：%s"
                                % os.path.basename(dst[KIND_DWG]))

    for kind in KINDS:
        if src[kind] and not os.path.isfile(src[kind]):
            raise FileNotFoundError("单日文件不存在：%s" % src[kind])
        if kind == KIND_DWG:
            # 目标是文件夹，不存在也能现建，所以只做提示不算错误
            if src[kind] and not dst[kind]:
                missing.append("%s：没找到（也推不出）6、矿块图文件夹" % KIND_LABELS[kind])
            continue
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
