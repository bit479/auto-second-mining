# -*- coding: utf-8 -*-
"""TXT 坐标文件解析服务（纯 Python，不含 Qt，可在后台线程里跑）。

为什么要单独一层
----------------
现有核心 ``core/make_database.parse_txt()`` 只认一种形态：**UTF-8 + 逗号 + 5 列
``工程号,,E,N,R``**，其它情况会报错或读成乱码（GBK 会被 ``errors="replace"`` 吞掉）。
本模块负责"容错读进来、把问题说清楚"，并在需要时生成一份**规范化副本**给核心脚本用，
原文件一个字节都不改，核心算法与数据库结构保持原样。

真实样本（已核对）：``excel_tools/_out/.../NS-3970-0718-P1-P90.txt``
    NS-3970-0718-P1,,470163.884,4349418.489,3971.508
即 CRLF、逗号、第 2 列为空、无表头。

元数据识别优先级（按需求）：
    1. 文件内部明确标注（``平台：3940`` / ``日期：1008`` / ``台阶高度：10``）
       以及炮孔编号内嵌的 ``BS-3940-0915-P1``（这是文件里的显式信息）
    2. 文件名里的 ``3940平台 1008`` / ``BS-3940-0915`` / ``3570取样1023``
    3. 都没有 → 保留页面原值，等人工补
**绝不从 Z 高程推断平台，也绝不自动填当天日期。**
"""

from __future__ import annotations

import hashlib
import re
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import paths

# ---------------------------------------------------------------- 常量

TXT_SUFFIXES = (".txt", ".dat", ".csv")
MAX_PREVIEW_ROWS = 200
BIG_FILE_ROWS = 20000

ENC_CANDIDATES = ("utf-8-sig", "utf-8", "gbk", "gb18030")

# 工程号形态：<前缀 2~4 字母>-<平台 3~4 位>-<日期 3~4 位>-<孔号>
HID_RE = re.compile(r"^([A-Za-z]{2,4})-(\d{3,4})-(\d{3,4})\s*[-–]")

ID_KEYS = ("工程号", "孔号", "炮孔", "编号", "名称", "孔名", "hole", "holeid", "id", "name")
E_KEYS = ("东坐标", "x坐标", "east", "东", "e", "x")
N_KEYS = ("北坐标", "y坐标", "north", "北", "n", "y")
R_KEYS = ("高程", "标高", "z坐标", "rl", "z", "r")

_SRC_LABEL = {
    "content": "文件内标注",
    "hole_id": "炮孔编号",
    "filename": "文件名",
    "page": "页面已有",
    "none": "未识别",
}


# ---------------------------------------------------------------- 数据模型

@dataclass
class Issue:
    """一条解析问题。level: error 阻断生成 / warn 需注意 / info 仅记录。"""

    level: str
    message: str
    line_no: int = 0
    raw: str = ""

    @property
    def text(self) -> str:
        head = "第 %d 行" % self.line_no if self.line_no else ""
        if head:
            return "%s：%s" % (head, self.message)
        return self.message


@dataclass
class HoleRow:
    hid: str
    e: float
    n: float
    r: float
    line_no: int = 0
    raw_cells: list[str] = field(default_factory=list)
    extras: list[str] = field(default_factory=list)


@dataclass
class MetaValue:
    value: str = ""
    source: str = "none"      # content / hole_id / filename / page / none
    note: str = ""

    @property
    def source_label(self) -> str:
        return _SRC_LABEL.get(self.source, self.source)

    def __bool__(self) -> bool:
        return bool(self.value)


@dataclass
class TxtImportTask:
    source_path: str = ""
    state: str = "parsing"          # parsing / ready / failed
    error: str = ""                 # 文件级失败原因
    encoding: str = ""
    delimiter: str = ""
    has_header: bool = False
    header: list[str] = field(default_factory=list)
    layout_note: str = ""
    rows: list[HoleRow] = field(default_factory=list)
    total_rows: int = 0
    invalid_rows: int = 0
    duplicate_rows: int = 0
    empty_lines: int = 0
    skipped_lines: int = 0
    issues: list[Issue] = field(default_factory=list)
    meta: dict[str, MetaValue] = field(default_factory=dict)
    meta_notes: list[str] = field(default_factory=list)
    core_ready: bool = True
    effective_path: str = ""
    normalized: bool = False
    normalize_note: str = ""
    size_bytes: int = 0
    mtime: float = 0.0
    started_at: float = 0.0
    elapsed_ms: int = 0

    # ---- 派生信息 ----

    @property
    def source_name(self) -> str:
        return Path(self.source_path).name if self.source_path else ""

    @property
    def valid_rows(self) -> int:
        return len(self.rows)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "warn"]

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)

    @property
    def blocked(self) -> bool:
        """有 error 级问题时禁止进入正式生成流程。"""
        return self.state != "ready" or self.has_errors

    @property
    def platform(self) -> str:
        return self.meta.get("platform", MetaValue()).value

    @property
    def date(self) -> str:
        return self.meta.get("date", MetaValue()).value

    @property
    def bench(self) -> str:
        return self.meta.get("bench", MetaValue()).value

    def size_text(self) -> str:
        n = float(self.size_bytes)
        for unit in ("B", "KB", "MB", "GB"):
            if n < 1024 or unit == "GB":
                return ("%.0f %s" if unit == "B" else "%.1f %s") % (n, unit)
            n /= 1024.0
        return "%.1f MB" % n

    def summary_line(self) -> str:
        if self.state == "failed":
            return "解析失败：%s" % (self.error or "未知原因")
        return "共 %d 孔 · 有效 %d · 异常 %d" % (
            self.total_rows, self.valid_rows, self.invalid_rows + self.duplicate_rows)

    def identity(self) -> tuple:
        """用于判断"同一个文件重复拖入"。"""
        return (str(Path(self.source_path)).lower(), self.size_bytes, int(self.mtime))


# ---------------------------------------------------------------- 解码

def decode_bytes(raw: bytes) -> tuple[str, str]:
    """按 UTF-8(BOM) → UTF-8 → GBK → GB18030 的顺序解码，返回 (文本, 编码名)。"""
    for enc in ENC_CANDIDATES:
        try:
            text = raw.decode(enc)
        except UnicodeDecodeError:
            continue
        if _looks_garbled(text):
            continue
        if enc == "utf-8-sig":
            return text, "UTF-8 BOM" if raw[:3] == b"\xef\xbb\xbf" else "UTF-8"
        return text, enc.upper()
    return raw.decode("gbk", "replace"), "GBK（含无法识别字符）"


def _looks_garbled(text: str) -> bool:
    """粗判：控制字符太多、或出现典型 GBK 被当 UTF-8 的替换字符。"""
    if "\ufffd" in text:
        return True
    sample = text[:4000]
    if not sample:
        return False
    bad = sum(1 for ch in sample if ord(ch) < 9 or 13 < ord(ch) < 32)
    return bad > max(3, len(sample) // 200)


# ---------------------------------------------------------------- 拆列

def split_cells(line: str) -> list[str]:
    """按制表符 → 逗号 → 分号 → 空白的顺序拆列（自动去掉首尾空白与不换行空格）。"""
    s = line.replace("\u00a0", " ").replace("\u3000", " ").strip().strip("\ufeff")
    if not s:
        return []
    if "\t" in s:
        return [c.strip() for c in s.split("\t")]
    if "," in s:
        return [c.strip() for c in s.split(",")]
    if "，" in s:
        return [c.strip() for c in s.split("，")]
    if s.count(";") >= 3:
        return [c.strip() for c in s.split(";")]
    return [c for c in re.split(r"\s+", s) if c]


def _to_float(cell: str) -> float | None:
    t = cell.strip().replace(" ", "")
    if not t:
        return None
    try:
        return float(t)
    except ValueError:
        return None


def _is_number(cell: str) -> bool:
    return _to_float(cell) is not None


def _is_comment(line: str) -> bool:
    s = line.lstrip()
    return s.startswith("#") or s.startswith("//") or s.startswith(";;")


# 「平台：3940」「台阶高度 10」「备注:xxx」这类元数据行，不是炮孔数据
_META_LINE_RE = re.compile(
    r"^\s*(?:平台|平台号|平台高程|炮区|炮区号|炮区日期|日期|台阶|台阶高度|坐标系统|"
    r"工程号|孔号|爆破|矿段|备注|说明|单位|meta)\s*[:：=]")


def _is_meta_line(line: str) -> bool:
    return bool(_META_LINE_RE.match(line))


# ---------------------------------------------------------------- 表头

def _detect_header(cells: list[str]) -> dict[str, int] | None:
    """如果这一行是表头，返回 字段→列号 映射；否则 None。"""
    low = [c.strip().lower() for c in cells]
    if not any(k in c for c in low for k in ID_KEYS):
        # 没有"工程号"字样时：整行都不是数字，也当表头（如 id,E,N,R）
        if any(_is_number(c) for c in cells):
            return None
        if len([c for c in cells if c]) < 3:
            return None
    mapping: dict[str, int] = {}

    def pick(keys) -> int | None:
        for i, cell in enumerate(low):                 # 完全相同
            if cell in keys:
                return i
        for i, cell in enumerate(low):                 # 前缀（忽略单字母，避免 "e" 命中 "name"）
            if any(len(k) > 1 and cell.startswith(k) for k in keys):
                return i
        for i, cell in enumerate(low):                 # 包含（同样忽略单字母）
            if any(len(k) > 1 and k in cell for k in keys):
                return i
        return None

    i = pick(ID_KEYS)
    if i is not None:
        mapping["id"] = i
    for name, keys in (("e", E_KEYS), ("n", N_KEYS), ("r", R_KEYS)):
        j = pick(keys)
        if j is not None and j not in mapping.values():
            mapping[name] = j
    if "id" not in mapping:
        mapping["id"] = 0
    return mapping


# ---------------------------------------------------------------- 元数据

def normalize_date(raw: str) -> tuple[str, str]:
    """把各种日期写法规范成炮区编号（MMDD）。返回 (值, 说明)。

    项目里的"日期"是炮区日期编号（0915 / 1008 / 0718），不是完整日历日期；
    带年份的写法会折算成 MMDD 并在说明里写清原始值，**绝不填当天日期**。
    """
    s = (raw or "").strip()
    if not s:
        return "", ""
    m = re.fullmatch(r"(\d{4})[-/.年](\d{1,2})[-/.月](\d{1,2})日?", s)
    if m:
        mo, day = int(m.group(2)), int(m.group(3))
        if 1 <= mo <= 12 and 1 <= day <= 31:
            return "%02d%02d" % (mo, day), "原写法 %s → %02d%02d" % (s, mo, day)
        return "", ""
    m = re.fullmatch(r"(\d{1,2})[-/月](\d{1,2})日?", s)
    if m:
        mo, day = int(m.group(1)), int(m.group(2))
        if 1 <= mo <= 12 and 1 <= day <= 31:
            return "%02d%02d" % (mo, day), "原写法 %s → %02d%02d" % (s, mo, day)
    if re.fullmatch(r"\d{3,4}", s):
        return s, ""
    return "", ""


def _platform_from_text(line: str) -> str:
    m = re.search(r"平台(?:号|编号|高程)?\s*[:：=]\s*(\d{3,4})", line)
    if m:
        return m.group(1)
    m = re.search(r"(?<!\d)(\d{3,4})\s*平台", line)
    return m.group(1) if m else ""


def _date_from_text(line: str) -> str:
    m = re.search(r"(?:炮区)?日期(?:编号|号)?\s*[:：=]\s*([0-9]{3,4}|[0-9]{4}[-/.][0-9]{1,2}[-/.][0-9]{1,2})",
                  line)
    if m:
        return m.group(1)
    m = re.search(r"炮区(?:编号|号)?\s*[:：=]\s*(\d{3,4})", line)
    if m:
        return m.group(1)
    m = re.search(r"(?<!\d)(\d{3,4})\s*(?:炮区|炮次)", line)
    return m.group(1) if m else ""


def _bench_from_text(line: str) -> str:
    m = re.search(r"台阶(?:高度)?\s*[:：=]?\s*(\d{1,2}(?:\.\d+)?)\s*(?:m|米)?", line)
    return m.group(1) if m else ""


def _from_filename(stem: str) -> tuple[str, str, str]:
    """文件名 → (平台, 日期, 依据说明)；识别不出返回空串。"""
    m = re.search(r"([A-Za-z]{2,4})-(\d{3,4})-(\d{3,4})", stem)
    if m:
        return m.group(2), m.group(3), "文件名 %s" % stem
    m = re.search(r"(?<!\d)(\d{3,4})\s*平台[^0-9]{0,6}(\d{3,4})?", stem)
    if m:
        return m.group(1), (m.group(2) or ""), "文件名 %s" % stem
    m = re.search(r"(?<!\d)(\d{3,4})\s*取样\s*(\d{3,4})", stem)
    if m:
        return m.group(1), m.group(2), "文件名 %s" % stem
    return "", "", ""


def _hole_id_tag(hids: list[str]) -> tuple[str, str]:
    """从炮孔编号里取平台/日期（多数票），例如 BS-3940-0915-P1 → 3940 / 0915。"""
    votes: dict[tuple[str, str], int] = {}
    for hid in hids:
        m = HID_RE.match(hid)
        if not m:
            continue
        key = (m.group(2), m.group(3))
        votes[key] = votes.get(key, 0) + 1
    if not votes:
        return "", ""
    return max(votes.items(), key=lambda kv: kv[1])[0]


# ---------------------------------------------------------------- 主解析

def is_txt_candidate(path) -> bool:
    return Path(str(path)).suffix.lower() in TXT_SUFFIXES


def parse_txt_file(path, should_cancel=None) -> TxtImportTask:
    """解析坐标 TXT。纯函数，可在后台线程调用；``should_cancel()`` 返回真时抛 ParseCancelled。"""
    p = Path(str(path))
    task = TxtImportTask(source_path=str(p), started_at=time.time(),
                         effective_path=str(p))
    try:
        stat = p.stat()
        task.size_bytes = int(stat.st_size)
        task.mtime = float(stat.st_mtime)
    except OSError as exc:
        return _fail(task, "无法读取文件（%s）" % exc)

    if p.suffix.lower() not in TXT_SUFFIXES:
        return _fail(task, "不是 TXT 坐标文件（.txt / .dat）")
    if task.size_bytes == 0:
        return _fail(task, "文件是空的（0 字节）")

    try:
        raw = p.read_bytes()
    except OSError as exc:
        return _fail(task, "无法读取文件内容（%s）" % exc)

    text, encoding = decode_bytes(raw)
    task.encoding = encoding
    if "\ufffd" in text:
        task.issues.append(Issue("warn", "文件里存在无法解码的字符，相关行可能被判为异常"))

    lines = text.splitlines()
    task.empty_lines = sum(1 for ln in lines if not ln.strip())

    # ---- 1) 逐行拆列 + 表头
    header_map: dict[str, int] | None = None
    header_seen = False
    data_rows: list[tuple[int, list[str], str]] = []
    for lineno, line in enumerate(lines, 1):
        if should_cancel is not None and lineno % 2000 == 0 and should_cancel():
            raise ParseCancelled()
        if not line.strip():
            continue
        if _is_comment(line):
            task.skipped_lines += 1
            continue
        if _is_meta_line(line):
            task.skipped_lines += 1
            continue
        cells = split_cells(line)
        if not cells:
            continue
        if not header_seen:
            header_seen = True
            maybe = _detect_header(cells)
            if maybe is not None:
                header_map = maybe
                task.has_header = True
                task.header = [c for c in cells]
                continue
        data_rows.append((lineno, cells, line))

    if not data_rows:
        return _fail(task, "文件里没有读到任何数据行（可能只有表头或全是注释）")

    # ---- 2) 逐行取炮孔
    id_idx = header_map.get("id", 0) if header_map else 0
    e_idx = header_map.get("e") if header_map else None
    n_idx = header_map.get("n") if header_map else None
    r_idx = header_map.get("r") if header_map else None

    seen: dict[str, int] = {}
    for lineno, cells, raw_line in data_rows:
        task.total_rows += 1
        hid = cells[id_idx].strip() if id_idx < len(cells) else ""
        if not hid:
            task.invalid_rows += 1
            _add(task, "error", "工程号为空", lineno, raw_line)
            continue

        if e_idx is not None and r_idx is not None:
            try:
                e, n, r = float(cells[e_idx]), float(cells[n_idx]), float(cells[r_idx])
            except (ValueError, TypeError, IndexError):
                task.invalid_rows += 1
                _add(task, "error", "坐标不是数字", lineno, raw_line)
                continue
            extras = [c for i, c in enumerate(cells)
                      if i not in (id_idx, e_idx, n_idx, r_idx) and c]
        else:
            numbers = [(i, _to_float(c)) for i, c in enumerate(cells) if i != id_idx]
            numbers = [(i, v) for i, v in numbers if v is not None]
            if len(numbers) < 3:
                task.invalid_rows += 1
                _add(task, "error", "坐标不足 3 个（E/N/R）", lineno, raw_line)
                continue
            e, n, r = numbers[0][1], numbers[1][1], numbers[2][1]
            extras = [c for i, c in enumerate(cells)
                      if i != id_idx and i not in [k for k, _ in numbers[:3]] and c]

        key = hid.upper()
        if key in seen:
            task.duplicate_rows += 1
            _add(task, "error", "工程号重复：%s（首次出现在第 %d 行）" % (hid, seen[key]),
                 lineno, raw_line)
            continue
        seen[key] = lineno
        task.rows.append(HoleRow(hid=hid, e=e, n=n, r=r, line_no=lineno,
                                 raw_cells=cells, extras=extras))

    task.layout_note = _layout_note(task, data_rows[0][1] if data_rows else [],
                                    data_rows[0][2] if data_rows else "")

    if task.total_rows > BIG_FILE_ROWS:
        task.issues.append(Issue("info", "文件较大（%d 行），已全部解析；预览只显示前 %d 行"
                                 % (task.total_rows, MAX_PREVIEW_ROWS)))
    if not task.rows:
        return _fail(task, "没有一条有效炮孔记录（共 %d 行，全部异常）" % task.total_rows)

    # ---- 3) 元数据
    _extract_meta(task, lines, task.header if task.has_header else [])

    # ---- 4) 与核心脚本的兼容性
    _check_core_compat(task)
    task.state = "ready"
    task.elapsed_ms = int((time.time() - task.started_at) * 1000)
    return task


class ParseCancelled(Exception):
    """用户取消了本次解析。"""


def _add(task: TxtImportTask, level: str, message: str, lineno: int, raw: str) -> None:
    # 每级最多留 20 条明细，其余只计数（大文件不至于刷爆问题列表）
    same_level = [i for i in task.issues if i.level == level]
    if len(same_level) >= 20:
        if len(same_level) == 20:
            task.issues.append(Issue(level, "同类问题较多，仅显示前 20 条明细"))
        return
    task.issues.append(Issue(level, message, lineno, raw[:180]))


def _fail(task: TxtImportTask, message: str) -> TxtImportTask:
    task.state = "failed"
    task.error = message
    task.issues.append(Issue("error", message))
    task.elapsed_ms = int((time.time() - task.started_at) * 1000)
    return task


def _layout_note(task: TxtImportTask, first_cells: list[str], first_line: str = "") -> str:
    if "\t" in first_line:
        delim = "制表符"
    elif "," in first_line:
        delim = "逗号"
    elif ";" in first_line and first_line.count(";") >= 3:
        delim = "分号"
    else:
        delim = "空格"
    if len(first_cells) >= 5 and not first_cells[1]:
        delim = "逗号（工程号,,E,N,R）"
    parts = [task.encoding, delim]
    if task.has_header:
        parts.append("含表头")
    if len(first_cells) > 5:
        parts.append("%d 列（多出的列保留原样）" % len(first_cells))
    return " · ".join(parts)


# ---------------------------------------------------------------- 元数据识别

def _extract_meta(task: TxtImportTask, lines: list[str], header: list[str]) -> None:
    meta = {"platform": MetaValue(), "date": MetaValue(), "bench": MetaValue()}

    # ---- 1) 文件内明确标注（只看前 60 行与注释行，避免误读坐标）
    scan = [ln for ln in lines[:60] if ln.strip()]
    scan += [ln for ln in lines if _is_comment(ln)][:40]
    for line in scan:
        if not meta["platform"]:
            val = _platform_from_text(line)
            if val:
                meta["platform"] = MetaValue(val, "content", "文件内标注")
        if not meta["date"]:
            raw = _date_from_text(line)
            if raw:
                val, note = normalize_date(raw)
                if val:
                    meta["date"] = MetaValue(val, "content", note or "文件内标注")
        if not meta["bench"]:
            val = _bench_from_text(line)
            if val:
                meta["bench"] = MetaValue(val, "content", "文件内标注")

    # ---- 2) 炮孔编号内嵌
    if not meta["platform"] or not meta["date"]:
        plat, date = _hole_id_tag([r.hid for r in task.rows[:30]])
        if plat and not meta["platform"]:
            meta["platform"] = MetaValue(plat, "hole_id", "取自炮孔编号")
        if date and not meta["date"]:
            meta["date"] = MetaValue(date, "hole_id", "取自炮孔编号")

    # ---- 3) 文件名
    fplat, fdate, why = _from_filename(Path(task.source_path).stem)
    if fplat:
        if not meta["platform"]:
            meta["platform"] = MetaValue(fplat, "filename", why)
        elif meta["platform"].value != fplat:
            task.meta_notes.append(
                "平台存在冲突：文件内为 %s，文件名为 %s（已采用文件内）"
                % (meta["platform"].value, fplat))
            task.issues.append(Issue("warn", task.meta_notes[-1]))
    if fdate:
        if not meta["date"]:
            meta["date"] = MetaValue(fdate, "filename", why)
        elif meta["date"].value != fdate:
            task.meta_notes.append(
                "日期存在冲突：文件内为 %s，文件名为 %s（已采用文件内）"
                % (meta["date"].value, fdate))
            task.issues.append(Issue("warn", task.meta_notes[-1]))

    # ---- 表头里如果写了平台/日期（例如 "平台:3940" 单独一列），补一次
    if header:
        joined = " ".join(header)
        if not meta["platform"]:
            v = _platform_from_text(joined)
            if v:
                meta["platform"] = MetaValue(v, "content", "取自表头")
        if not meta["date"]:
            v = _date_from_text(joined)
            if v:
                val, note = normalize_date(v)
                if val:
                    meta["date"] = MetaValue(val, "content", note or "取自表头")

    if not meta["platform"]:
        task.issues.append(Issue("warn", "没有识别到平台号，请在页面上手工填写"))
    if not meta["date"]:
        task.issues.append(Issue("warn", "没有识别到日期/炮区号，请在页面上手工填写"))

    task.meta = meta


# ---------------------------------------------------------------- 核心兼容 + 规范化

def _check_core_compat(task: TxtImportTask) -> None:
    """判断核心脚本能否直接吃这个文件；不能则生成规范化副本（原文件不动）。"""
    enc_utf8 = task.encoding.replace(" ", "").upper().startswith("UTF-8")
    comma_layout = True
    for row in task.rows[:50]:
        cells = row.raw_cells
        if len(cells) < 5 or cells[1] != "":
            comma_layout = False
            break
        if _to_float(cells[2]) != row.e or _to_float(cells[3]) != row.n or _to_float(cells[4]) != row.r:
            comma_layout = False
            break
    task.core_ready = bool(enc_utf8 and comma_layout and not task.has_header)
    if task.core_ready:
        task.effective_path = task.source_path
        return

    try:
        out = write_normalized(task)
        task.effective_path = str(out)
        task.normalized = True
        task.normalize_note = ("已生成规范化副本（UTF-8 / 5 列）供生成使用；原文件未改动：%s"
                               % out.name)
        task.issues.append(Issue("info", task.normalize_note))
    except OSError as exc:
        task.issues.append(Issue("error", "生成规范化副本失败：%s" % exc))


def cache_dir() -> Path:
    """规范化副本放系统临时目录：不污染项目目录，退出后由系统回收。"""
    d = Path(tempfile.gettempdir()) / "sm_txt_import"
    try:
        d.mkdir(parents=True, exist_ok=True)
    except OSError:
        d = Path(tempfile.gettempdir())
    return d


def write_normalized(task: TxtImportTask) -> Path:
    """把容错解析结果写成核心脚本认的 5 列 CSV（UTF-8）。坐标沿用原始字符串，不做舍入。"""
    stem = re.sub(r"[^\w\u4e00-\u9fa5-]+", "_", Path(task.source_path).stem)[:40] or "txt"
    digest = hashlib.md5(("%s|%s|%s" % (task.source_path, task.size_bytes, task.mtime))
                         .encode("utf-8")).hexdigest()[:8]
    out = cache_dir() / ("%s_%s.normalized.txt" % (stem, digest))
    lines = []
    for row in task.rows:
        coords = [_cell_text(row.e, row.raw_cells, 2),
                  _cell_text(row.n, row.raw_cells, 3),
                  _cell_text(row.r, row.raw_cells, 4)]
        lines.append("%s,,%s" % (row.hid, ",".join(coords)))
    out.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
    return out


def _cell_text(value: float, cells: list[str], idx: int) -> str:
    """优先沿用原始单元格文本（避免 470163.884 → 470163.8839999）。"""
    if idx < len(cells):
        raw = cells[idx].strip()
        if raw and _to_float(raw) == value:
            return raw
    return repr(value)


def cleanup_cache(keep: str = "", max_age_h: float = 24.0) -> None:
    """只清理超过 max_age_h 的规范化副本；正在用的那份永远保留。"""
    keep_name = Path(keep).name if keep else ""
    cutoff = time.time() - max_age_h * 3600
    try:
        for p in cache_dir().glob("*.normalized.txt"):
            if p.name == keep_name:
                continue
            try:
                if p.stat().st_mtime >= cutoff:
                    continue
                p.unlink()
            except OSError:
                pass
    except OSError:
        pass


def preview_rows(task: TxtImportTask, limit: int = MAX_PREVIEW_ROWS) -> list[HoleRow]:
    return task.rows[:limit]
