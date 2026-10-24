# -*- coding: utf-8 -*-
"""从「炮孔坐标 TXT + 粘贴的品位表」一键生成 3DMine 炮孔数据库。

输入：
  * 坐标 TXT：``BS-3940-0915-P1,,470068.592,4349643.299,3941.101``
    每行 = 工程号, 空列, 开孔坐标E, 开孔坐标N, 开孔坐标R；
  * 品位表：可以直接粘贴 Excel 的两列/四列，也可以是 Markdown 表格；
    程序按「BS-... 工程号后面第一个数字」取品位。

输出：
  * ``1、<平台>平台 炮孔数据库<日期>.xls``（定位表 / 测斜表 / pit_blast）
  * ``2、<平台>平台炮孔数据库<日期>.mdb``（3DMine 兼容，含 config/style/constraint 元数据）

台阶高度默认 10 m：孔底高程 = 平台高程 - 台阶高度，最大孔深 = 开孔坐标R - 孔底高程。

**孔深按整数写库**：定位表的「最大孔深」、测斜表的「深度」、pit_blast 的「至」
三处都是同一个孔深，一律**四舍五入取整**（9.5→10、8.5→9，不是 Python 内置 round 的
"银行家舍入"）；坐标 E/N/R 仍保留 3 位小数。
"""
from __future__ import annotations

import argparse
import gc
import os
import re
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_MDB = ROOT / "assets" / "3dmine_template.mdb"

try:
    from bak_housekeeping import backup_file
except ImportError:                       # 作为 core 包导入时
    from .bak_housekeeping import backup_file


@dataclass
class Hole:
    hid: str
    e: float
    n: float
    r: float
    depth: float = 0.0


@dataclass
class ParsedGrades:
    grades: dict[str, float] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)
    extra: list[str] = field(default_factory=list)
    duplicates: list[str] = field(default_factory=list)
    decimals: int = 2
    n_rows: int = 0


def _clean(s: str) -> str:
    return (s.replace("&#x20;", " ").replace("&nbsp;", " ")
             .replace("\u00a0", " ").replace("\u3000", " ").strip())


def round_int(value: float) -> int:
    """四舍五入到整数。

    不能用内置 ``round()`` —— 它是"银行家舍入"（``round(8.5) == 8``），
    和 Excel / 3DMine 里的四舍五入对不上。这里用 Decimal 的 ROUND_HALF_UP：
    8.5→9、9.5→10、9.499→9。
    """
    return int(Decimal(str(float(value))).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


# 工程号形态：<前缀 2~4 个字母>-<平台号 3~4 位>-<日期 3~4 位>-<孔号>
# 北部山头 BS-3940-0915-P1 / 南部山头 NS-3970-0708-P1 / 中心矿段 zx-3570-1023-p1
_HID_RE = re.compile(r"^([A-Za-z]{2,4})-(\d{3,4})-(\d{3,4})-")


def looks_like_coord_txt(path) -> bool:
    """判断一个 .txt 是不是"坐标文件"（工程号,,开孔坐标E,开孔坐标N,开孔坐标R）。

    **只看内容形态，不看文件名前缀**：中心矿段的取样文件叫「3570取样1023.txt」，
    里面工程号是 ``zx-3570-1023-p1``，一个 ``BS-`` 都没有。
    """
    try:
        with Path(path).open(encoding="utf-8-sig", errors="replace") as fh:
            for _ in range(8):
                line = fh.readline()
                if not line:
                    break
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                cells = [_clean(x) for x in s.split(",")]
                if len(cells) < 5 or not cells[0]:
                    continue
                try:
                    float(cells[2])
                    float(cells[3])
                    float(cells[4])
                except ValueError:
                    continue
                return True
    except OSError:
        return False
    return False


def parse_txt(path) -> list[Hole]:
    """读坐标 TXT；返回按文件顺序排列的 Hole 列表。"""
    p = Path(path)
    text = p.read_text(encoding="utf-8-sig", errors="replace")
    holes = []
    seen = set()
    for lineno, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        cells = [_clean(x) for x in s.split(",")]
        if len(cells) < 5:
            raise ValueError("TXT 第 %d 行不是 5 列：%s" % (lineno, line))
        hid = cells[0]
        try:
            e, n, r = float(cells[2]), float(cells[3]), float(cells[4])
        except ValueError:
            raise ValueError("TXT 第 %d 行坐标不是数字：%s" % (lineno, line))
        if not hid:
            raise ValueError("TXT 第 %d 行工程号为空" % lineno)
        key = hid.upper()
        if key in seen:
            raise ValueError("TXT 里工程号重复：%s" % hid)
        seen.add(key)
        holes.append(Hole(hid, e, n, r))
    if not holes:
        raise ValueError("TXT 里没有读到炮孔")
    return holes


def _split_line(line: str):
    s = _clean(line)
    if not s:
        return []
    if "|" in s:
        return [_clean(x) for x in s.strip("|").split("|")]
    if "\t" in s:
        return [_clean(x) for x in s.split("\t")]
    return [_clean(x) for x in re.split(r"\s{2,}", s)]


def _is_separator(cells) -> bool:
    if not cells:
        return True
    return all(re.fullmatch(r":?-{3,}:?", c.replace(" ", "")) for c in cells if c) \
        and any(c for c in cells)


def _to_float(s: str):
    t = _clean(s).replace(",", "")
    m = re.match(r"^[-+]?\d+(?:\.\d+)?", t)
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def parse_grades(text: str, holes: list[Hole]) -> ParsedGrades:
    """解析粘贴的品位表；工程号按 TXT 里的大小写为准。"""
    canonical = {h.hid.upper(): h.hid for h in holes}
    out = ParsedGrades()
    found: dict[str, tuple[float, int]] = {}
    raw_decimals = 2
    for line in text.splitlines():
        cells = _split_line(line)
        if not cells or _is_separator(cells):
            continue
        # 先按"这一格是不是 TXT 里真有的工程号"找（不分前缀、不分大小写）；
        # 找不到再按工程号形态认，记成"品位表里多出来的"。
        hid_i = next((i for i, c in enumerate(cells)
                      if _clean(c).upper() in canonical), None)
        if hid_i is None:
            hid_i = next((i for i, c in enumerate(cells)
                          if _HID_RE.match(_clean(c))), None)
        if hid_i is None:
            continue
        raw_hid = cells[hid_i]
        hid = canonical.get(raw_hid.upper())
        if hid is None:
            out.extra.append(raw_hid)
            continue
        grade = None
        grade_raw = ""
        for j in range(hid_i + 1, min(len(cells), hid_i + 3)):
            grade = _to_float(cells[j])
            if grade is not None:
                grade_raw = cells[j]
                break
        if grade is None:
            continue
        m = re.search(r"\.(\d+)", grade_raw)
        if m:
            raw_decimals = max(raw_decimals, len(m.group(1)))
        out.n_rows += 1
        prev = found.get(hid)
        if prev is not None and abs(prev[0] - grade) > 1e-9:
            out.duplicates.append("%s（%.4f / %.4f）" % (hid, prev[0], grade))
            continue
        found[hid] = (grade, len(m.group(1)) if m else 2)
    out.grades = {k: v[0] for k, v in found.items()}
    out.missing = [h.hid for h in holes if h.hid not in out.grades]
    out.decimals = max([v[1] for v in found.values()] + [raw_decimals])
    return out


def parse_tag_from_txt(path) -> tuple[str, str]:
    """从文件名或文件内容里认「平台号 + 日期」。

    认得的写法：
    * ``BS-3940-0915-P1-P47.txt`` / ``NS-3970-0708.txt``（文件名里就有）
    * ``3570取样1023.txt``（文件名里没有，读第一行工程号 ``zx-3570-1023-p1``）
    * 实在认不出，就按文件名里的数字猜（``3570取样1023`` → 3570 / 1023）
    """
    p = Path(path)
    m = re.search(r"([A-Za-z]{2,4})-(\d{3,4})-(\d{3,4})", p.stem)
    if m:
        return m.group(2), m.group(3)

    try:
        with p.open(encoding="utf-8-sig", errors="replace") as fh:
            for _ in range(8):
                line = fh.readline()
                if not line:
                    break
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                m = _HID_RE.match(s)
                if m:                       # 只看第一条数据行
                    return m.group(2), m.group(3)
                break
    except OSError:
        pass

    digits = re.findall(r"\d{3,4}", p.stem)
    if len(digits) >= 2:
        return digits[0], digits[1]
    return "", ""


def default_output_paths(out_dir, platform: str, date: str) -> tuple[Path, Path]:
    out_dir = Path(out_dir)
    xls = out_dir / ("1、%s平台 炮孔数据库%s.xls" % (platform, date))
    mdb = out_dir / ("2、%s平台炮孔数据库%s.mdb" % (platform, date))
    return xls, mdb


def _write_xls(holes, grades: ParsedGrades, path: Path, dec: int):
    import xlwt

    wb = xlwt.Workbook(encoding="utf-8")
    thin = "borders: left thin, right thin, top thin, bottom thin;"
    head = xlwt.easyxf("font: bold on; align: horiz center, vert center;" + thin)
    cell = xlwt.easyxf("align: horiz center, vert center;" + thin)
    num3 = xlwt.easyxf("align: horiz center, vert center;" + thin,
                       num_format_str="0.000")
    num0 = xlwt.easyxf("align: horiz center, vert center;" + thin,
                       num_format_str="0")
    numg = xlwt.easyxf("align: horiz center, vert center;" + thin,
                       num_format_str="0." + "0" * max(2, dec))

    ws = wb.add_sheet("定位表")
    heads = ["工程号", "开孔坐标E", "开孔坐标N", "开孔坐标R", "轨迹类型", "最大孔深"]
    for i, h in enumerate(heads):
        ws.write(0, i, h, head)
    for r, hole in enumerate(holes, 1):
        ws.write(r, 0, hole.hid, cell)
        ws.write(r, 1, hole.e, num3)
        ws.write(r, 2, hole.n, num3)
        ws.write(r, 3, hole.r, num3)
        ws.write(r, 4, "直线", cell)
        ws.write(r, 5, round_int(hole.depth), num0)
    for col, w in enumerate((22, 14, 14, 14, 10, 12)):
        ws.col(col).width = w * 256

    ws = wb.add_sheet("测斜表")
    for i, h in enumerate(["工程号", "深度", "方位角", "倾角"]):
        ws.write(0, i, h, head)
    for r, hole in enumerate(holes, 1):
        ws.write(r, 0, hole.hid, cell)
        ws.write(r, 1, round_int(hole.depth), num0)
        ws.write(r, 2, 0.0, num3)
        ws.write(r, 3, -90.0, num3)
    for col, w in enumerate((22, 12, 12, 12)):
        ws.col(col).width = w * 256

    ws = wb.add_sheet("pit_blast")
    for i, h in enumerate(["工程号", "从", "至", "Au"]):
        ws.write(0, i, h, head)
    for r, hole in enumerate(holes, 1):
        ws.write(r, 0, hole.hid, cell)
        ws.write(r, 1, 0.0, num3)
        ws.write(r, 2, round_int(hole.depth), num0)
        ws.write(r, 3, grades.grades[hole.hid], numg)
    for col, w in enumerate((22, 10, 10, 12)):
        ws.col(col).width = w * 256
    wb.save(str(path))


def _write_mdb(holes, grades: ParsedGrades, path: Path, template: Path):
    import pyodbc

    pyodbc.pooling = False
    shutil.copy2(template, path)
    cn = pyodbc.connect(
        "DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=%s;" % path,
        autocommit=False)
    try:
        cur = cn.cursor()
        for table in ("定位表", "测斜表", "pit_blast"):
            cur.execute("DELETE FROM [%s]" % table)
        cur.executemany(
            "INSERT INTO [定位表] ([工程号],[开孔坐标E],[开孔坐标N],[开孔坐标R],"
            "[轨迹类型],[最大孔深]) VALUES (?,?,?,?,?,?)",
            [(h.hid, h.e, h.n, h.r, "直线", float(round_int(h.depth)))
             for h in holes])
        cur.executemany(
            "INSERT INTO [测斜表] ([工程号],[深度],[方位角],[倾角]) VALUES (?,?,?,?)",
            [(h.hid, float(round_int(h.depth)), 0.0, -90.0) for h in holes])
        cur.executemany(
            "INSERT INTO [pit_blast] ([工程号],[从],[至],[Au]) VALUES (?,?,?,?)",
            [(h.hid, 0.0, float(round_int(h.depth)), grades.grades[h.hid])
             for h in holes])
        cn.commit()
        for table in ("定位表", "测斜表", "pit_blast"):
            cur.execute("SELECT COUNT(*) FROM [%s]" % table)
            n = int(cur.fetchone()[0])
            if n != len(holes):
                raise RuntimeError("%s 行数 %d ≠ %d" % (table, n, len(holes)))
    finally:
        cn.close()
        del cn
        gc.collect()


def _replace_retry(src: Path, dst: Path, timeout: float = 5.0):
    """Access ODBC 关闭后可能还会短暂占用文件；等它释放再替换。"""
    t0 = time.time()
    while True:
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if time.time() - t0 > timeout:
                raise
            time.sleep(0.2)


def build(txt_path, grades_text: str, out_dir=None, platform: str = "",
          date: str = "", bench_height: float = 10.0, force: bool = False,
          template: Path = None) -> dict:
    """解析并生成 .xls + .mdb；返回路径、孔数、警告。"""
    txt_path = Path(txt_path)
    holes = parse_txt(txt_path)
    p, d = parse_tag_from_txt(txt_path)
    platform = platform or p
    date = date or d
    if not platform or not date:
        raise ValueError("认不出平台/日期，请在界面上填写（TXT 文件名应含 BS-3940-0915）")
    out_dir = Path(out_dir) if out_dir else txt_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    xls_path, mdb_path = default_output_paths(out_dir, platform, date)
    template = Path(template) if template else TEMPLATE_MDB
    if not template.is_file():
        raise FileNotFoundError("缺少 3DMine 空库模板：%s" % template)

    try:
        bench = float(bench_height)
    except ValueError:
        raise ValueError("台阶高度不是数字：%s" % bench_height)
    if bench <= 0:
        raise ValueError("台阶高度必须大于 0")
    bottom = float(platform) - bench
    for h in holes:
        h.depth = round(h.r - bottom, 3)
        if h.depth <= 0:
            raise ValueError("%s 计算出的孔深 %.3f ≤ 0，请检查平台高程/台阶高度"
                             % (h.hid, h.depth))

    # 三处孔深都要写成整数，取整后不能变成 0（0.4 m 的孔没有意义）
    zeroed = [(h.hid, h.depth) for h in holes if round_int(h.depth) <= 0]
    if zeroed:
        more = " 等 %d 个" % len(zeroed) if len(zeroed) > 8 else ""
        raise ValueError("这些孔四舍五入后的孔深为 0：%s%s（请检查平台高程/台阶高度）"
                         % ("、".join("%s(%.3f)" % (hid, d) for hid, d in zeroed[:8]), more))

    grades = parse_grades(grades_text, holes)
    if grades.duplicates:
        raise ValueError("同一工程号出现不同品位：%s" % "；".join(grades.duplicates[:8]))
    if grades.missing:
        more = " 等 %d 个" % len(grades.missing) if len(grades.missing) > 12 else ""
        raise ValueError("品位表缺少这些工程号：%s%s"
                         % ("、".join(grades.missing[:12]), more))

    if not force:
        exists = [p.name for p in (xls_path, mdb_path) if p.exists()]
        if exists:
            raise FileExistsError("输出文件已存在：%s（确认覆盖请勾选/加 --force）"
                                  % "、".join(exists))

    for p in (xls_path, mdb_path):
        if p.exists():
            backup_file(str(p), tag="_覆盖前" + time.strftime("%Y%m%d-%H%M%S"))

    fd_x, name_x = tempfile.mkstemp(prefix="mkdb_", suffix=".xls", dir=out_dir)
    os.close(fd_x)
    tmp_xls = Path(name_x)
    fd_m, name_m = tempfile.mkstemp(prefix="mkdb_", suffix=".mdb", dir=out_dir)
    os.close(fd_m)
    tmp_mdb = Path(name_m)
    tmp_mdb.unlink()                       # pyodbc 要求目标不存在时由 copy 创建
    try:
        _write_xls(holes, grades, tmp_xls, grades.decimals)
        _write_mdb(holes, grades, tmp_mdb, template)
        _replace_retry(tmp_xls, xls_path)
        _replace_retry(tmp_mdb, mdb_path)
    finally:
        for p in (tmp_xls, tmp_mdb):
            try:
                if p.exists():
                    p.unlink()
            except OSError:
                pass
    return {"xls": xls_path, "mdb": mdb_path, "holes": len(holes),
            "missing": grades.missing, "extra": sorted(set(grades.extra)),
            "platform": platform, "date": date, "bench_height": bench,
            "grades_decimals": grades.decimals}


def _read_grades_arg(args) -> str:
    if args.grades_file:
        return Path(args.grades_file).read_text(encoding="utf-8-sig", errors="replace")
    if args.grades_stdin or not sys.stdin.isatty():
        return sys.stdin.read()
    raise ValueError("请用 --grades-file 指定品位表，或把品位表从标准输入传进来")


def main() -> int:
    ap = argparse.ArgumentParser(description="TXT + 品位表 -> 3DMine 炮孔数据库")
    ap.add_argument("txt", help="炮孔坐标 TXT（BS-平台-日期-P1-P47.txt）")
    ap.add_argument("--grades-file", help="粘贴的品位表（Markdown/TSV）")
    ap.add_argument("--grades-stdin", action="store_true", help="从标准输入读品位表")
    ap.add_argument("--out-dir", help="输出目录（默认 TXT 同目录）")
    ap.add_argument("--platform", default="", help="平台高程，如 3940")
    ap.add_argument("--date", default="", help="日期/炮区号，如 0915")
    ap.add_argument("--bench-height", type=float, default=10.0, help="台阶高度(m)，默认10")
    ap.add_argument("--template", help="3DMine 空库模板 .mdb")
    ap.add_argument("--force", action="store_true", help="覆盖已存在的 .xls/.mdb（先备份到 bak/）")
    args = ap.parse_args()
    try:
        res = build(args.txt, _read_grades_arg(args), out_dir=args.out_dir,
                    platform=args.platform, date=args.date,
                    bench_height=args.bench_height, force=args.force,
                    template=Path(args.template) if args.template else None)
    except Exception as exc:
        print("[错误] %s" % exc)
        return 2
    print("完成：%d 孔" % res["holes"])
    print("  XLS: %s" % res["xls"])
    print("  MDB: %s" % res["mdb"])
    if res["extra"]:
        print("  [提示] 品位表里多出 %d 个不在 TXT 的工程号，已忽略：%s"
              % (len(res["extra"]), "、".join(res["extra"][:8])))
    print("  台阶高度 %.2f m；品位保留 %d 位小数"
          % (res["bench_height"], res["grades_decimals"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
