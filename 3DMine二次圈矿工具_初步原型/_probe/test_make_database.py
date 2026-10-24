# -*- coding: utf-8 -*-
"""自检：TXT 坐标 + 粘贴品位表 -> .xls / .mdb。

**自带数据**，不依赖外部目录（原来的 0915 原始数据已经挪走）。

重点验证 2026-10 这次的口径改动：孔深相关的三列
—— 定位表「最大孔深」、测斜表「深度」、pit_blast「至」——
一律**四舍五入取整**，而且必须是"真·四舍五入"，
不是 Python 内置 ``round()`` 的银行家舍入（``round(8.5) == 8``，这里是 9）。

用法::

    python _probe/test_make_database.py
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORE = ROOT / "core"
sys.path.insert(0, str(CORE))

from make_database import (build, looks_like_coord_txt, parse_grades,  # noqa: E402
                           parse_tag_from_txt, parse_txt, round_int)

PLATFORM = "3940"
BENCH = 10.0            # 孔底高程 = 3940 - 10 = 3930
DATE = "0101"

# (工程号, E, N, R)  R - 3930 = 设计孔深
HOLES = [
    ("BS-3940-0101-P1", 470000.592, 4349000.129, 3938.500),   # 8.5 -> 9（银行家会是 8）
    ("BS-3940-0101-P2", 470001.101, 4349001.101, 3939.500),   # 9.5 -> 10
    ("BS-3940-0101-P3", 470002.222, 4349002.202, 3939.400),   # 9.4 -> 9
    ("BS-3940-0101-P4", 470003.333, 4349003.303, 3939.600),   # 9.6 -> 10
    ("BS-3940-0101-P5", 470004.444, 4349004.404, 3940.000),   # 10.0 -> 10
]
EXPECT_DEPTH = [9, 10, 9, 10, 10]

checks = []


def check(ok, msg):
    print(("  ✓ " if ok else "  ✗ ") + msg)
    checks.append((bool(ok), msg))


def make_txt(path: Path) -> None:
    lines = ["%s,,%.3f,%.3f,%.3f" % h for h in HOLES]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_grades() -> str:
    head = "| 工程号 | Au |\n| --- | --- |\n"
    rows = ["| %s | %.2f |" % (h[0], 1.10 + i * 0.37) for i, h in enumerate(HOLES)]
    return head + "\n".join(rows) + "\n"


def main():
    checks.clear()
    print("=" * 70)
    print("[1] 四舍五入（ROUND_HALF_UP，不是银行家舍入）")
    cases = [(8.5, 9), (9.5, 10), (7.5, 8), (9.4, 9), (9.6, 10),
             (9.499, 9), (10.0, 10), (0.5, 1)]
    for value, expect in cases:
        got = round_int(value)
        check(got == expect, "round_int(%s) = %d（期望 %d）" % (value, got, expect))

    td = Path(tempfile.mkdtemp(prefix="mkdb_test_"))
    try:
        txt = td / ("BS-%s-%s-P1-P%d.txt" % (PLATFORM, DATE, len(HOLES)))
        make_txt(txt)
        res = build(txt, make_grades(), out_dir=td, platform=PLATFORM,
                    date=DATE, bench_height=BENCH)
        check(res["holes"] == len(HOLES), "读到 %d 孔" % len(HOLES))
        check(res["xls"].exists() and res["mdb"].exists(), "生成 .xls + .mdb")

        print("\n[2] xls：三列孔深都是整数")
        import xlrd
        wb = xlrd.open_workbook(str(res["xls"]))
        check(wb.sheet_names() == ["定位表", "测斜表", "pit_blast"], "三张表名正确")

        s = wb.sheet_by_name("定位表")
        check([s.cell_value(0, c) for c in range(6)] ==
              ["工程号", "开孔坐标E", "开孔坐标N", "开孔坐标R", "轨迹类型", "最大孔深"],
              "定位表表头正确")
        got = [s.cell_value(r, 5) for r in range(1, s.nrows)]
        check([int(v) for v in got] == EXPECT_DEPTH,
              "最大孔深 = %s（期望 %s）" % (got, EXPECT_DEPTH))
        check(all(float(v).is_integer() for v in got), "最大孔深没有小数")
        check(abs(s.cell_value(1, 1) - 470000.592) < 1e-9
              and abs(s.cell_value(1, 3) - 3938.5) < 1e-9,
              "坐标 E / 开孔坐标R 仍是原值（没被取整）")

        s = wb.sheet_by_name("测斜表")
        got = [s.cell_value(r, 1) for r in range(1, s.nrows)]
        check([int(v) for v in got] == EXPECT_DEPTH,
              "测斜表 深度 = %s（期望 %s）" % (got, EXPECT_DEPTH))
        check(all(float(v).is_integer() for v in got), "深度没有小数")

        s = wb.sheet_by_name("pit_blast")
        got = [s.cell_value(r, 2) for r in range(1, s.nrows)]
        check([int(v) for v in got] == EXPECT_DEPTH,
              "pit_blast 至 = %s（期望 %s）" % (got, EXPECT_DEPTH))
        check(all(float(s.cell_value(r, 1)) == 0.0 for r in range(1, s.nrows)),
              "pit_blast 从 全部为 0")
        check(abs(s.cell_value(1, 3) - 1.10) < 1e-9, "品位原样保留（1.10）")

        print("\n[3] mdb：三列孔深同样是整数")
        import pyodbc
        check(open(res["mdb"], "rb").read(20).startswith(b"\x00\x01\x00\x00Standard Jet DB"),
              "mdb 是真正的 Standard Jet DB")
        cn = pyodbc.connect("DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
                            "DBQ=%s;" % res["mdb"])
        try:
            cur = cn.cursor()
            counts = {}
            for t in ("config_table_3dmine", "constraint_table_3dmine", "pit_blast",
                      "style_table_3dmine", "定位表", "测斜表"):
                cur.execute("SELECT COUNT(*) FROM [%s]" % t)
                counts[t] = cur.fetchone()[0]
            check(counts["定位表"] == counts["测斜表"] == counts["pit_blast"] == len(HOLES),
                  "三张业务表各 %d 行" % len(HOLES))
            check(counts["config_table_3dmine"] > 0 and counts["style_table_3dmine"] > 0,
                  "3DMine 元数据表在")

            for table, column in (("定位表", "最大孔深"), ("测斜表", "深度"),
                                  ("pit_blast", "至")):
                cur.execute("SELECT [%s] FROM [%s] ORDER BY [工程号]" % (column, table))
                values = [row[0] for row in cur.fetchall()]
                check([int(v) for v in values] == EXPECT_DEPTH,
                      "%s.%s = %s" % (table, column, values))
                check(all(float(v).is_integer() for v in values),
                      "%s.%s 没有小数" % (table, column))
        finally:
            cn.close()

        print("\n[4] 边界：取整后为 0 的孔要拦住")
        bad = [
            ("BS-3940-0101-P1", 470000.0, 4349000.0, 3930.400),   # 0.4 -> 0
        ]
        bad_txt = td / "bad" / "BS-3940-0101-P1-P1.txt"
        bad_txt.parent.mkdir(parents=True, exist_ok=True)
        bad_txt.write_text("%s,,%.3f,%.3f,%.3f\n" % bad[0], encoding="utf-8")
        try:
            build(bad_txt, "| 工程号 | Au |\n| BS-3940-0101-P1 | 1.0 |\n",
                  out_dir=bad_txt.parent, platform=PLATFORM, date=DATE,
                  bench_height=BENCH)
        except ValueError as exc:
            check("四舍五入后的孔深为 0" in str(exc), "报错并说明原因：%s" % exc)
        else:
            check(False, "孔深取整为 0 却没有报错")

        print("\n[5] 品位表缺行仍能指出")
        holes = []
        from make_database import parse_txt
        holes = parse_txt(txt)
        short = "\n".join(make_grades().splitlines()[:-1]) + "\n"
        g = parse_grades(short, holes)
        check(g.missing == ["BS-3940-0101-P5"], "少一行时指出缺 P5：%s" % g.missing)

        print("\n[6] 换前缀：中心矿段 zx- / 文件名里没有 BS-")
        zx_dir = td / "zx"
        zx_dir.mkdir()
        zx_txt = zx_dir / "3570取样1023.txt"
        zx_txt.write_text(
            "\n".join("zx-3570-1023-p%d,,467945.599,4350279.965,3569.073" % (i + 1)
                      for i in range(3)) + "\n", encoding="utf-8")
        check(looks_like_coord_txt(zx_txt), "按内容认得出是坐标 TXT（不靠文件名）")
        tag = parse_tag_from_txt(zx_txt)
        check(tag == ("3570", "1023"), "平台/日期从工程号里认出：%s" % (tag,))

        rep = zx_dir / "BS-3940-1008_报告.txt"
        rep.write_text("炮孔数据报告\n类型,体号,体积\n", encoding="utf-8")
        check(not looks_like_coord_txt(rep), "报告类 txt 不会被当成坐标文件")

        zx_holes = parse_txt(zx_txt)
        zx_grades = parse_grades(
            "| 工程号 | Au |\n| --- | --- |\n| zx-3570-1023-p1 | 1.23 |\n"
            "| zx-3570-1023-p2 | 1.56 |\n| zx-3570-1023-p3 | 1.78 |\n", zx_holes)
        check(not zx_grades.missing and len(zx_grades.grades) == 3,
              "小写 zx- 工程号的品位能对上（%d/3）" % len(zx_grades.grades))
    finally:
        shutil.rmtree(td, ignore_errors=True)

    failed = [m for ok, m in checks if not ok]
    print("\n%d/%d 通过" % (len(checks) - len(failed), len(checks)))
    print("结论：" + ("全部通过 ✓" if not failed else "失败：%s" % failed))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
