# -*- coding: utf-8 -*-
"""自检：TXT + 粘贴品位表 -> .xls/.mdb（0915，47 孔）。"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORE = ROOT / "core"
sys.path.insert(0, str(CORE))

from make_database import build, parse_grades, parse_txt   # noqa: E402

TXT = Path(r"D:\WK\N CRT\北部山头3940平台2026\7、单日数据\北部山头3940平台-0915"
           r"\BS-3940-0915-P1-P47.txt")
GRADES = ROOT / "_probe" / "0915_grades.md"

checks = []


def check(ok, msg):
    print(("  ✓ " if ok else "  ✗ ") + msg)
    checks.append((bool(ok), msg))


def main():
    if not TXT.exists() or not GRADES.exists():
        print("缺少自检输入：", TXT, GRADES)
        return 2
    td = tempfile.mkdtemp(prefix="mkdb_test_")
    try:
        out = Path(td)
        res = build(TXT, GRADES.read_text(encoding="utf-8"), out_dir=out)
        check(res["holes"] == 47, "TXT 读到 47 孔")
        check(res["xls"].exists() and res["mdb"].exists(), "生成 .xls + .mdb")

        import xlrd
        wb = xlrd.open_workbook(str(res["xls"]))
        check(wb.sheet_names() == ["定位表", "测斜表", "pit_blast"],
              "xls 三张表名正确")
        s = wb.sheet_by_name("定位表")
        check(s.nrows == 48 and [s.cell_value(0, c) for c in range(6)] ==
              ["工程号", "开孔坐标E", "开孔坐标N", "开孔坐标R", "轨迹类型", "最大孔深"],
              "定位表表头/行数正确")
        check(abs(s.cell_value(1, 1) - 470068.592) < 1e-9
              and abs(s.cell_value(1, 3) - 3941.101) < 1e-9
              and abs(s.cell_value(1, 5) - 11.101) < 1e-9,
              "P1 坐标与孔深正确")
        p = wb.sheet_by_name("pit_blast")
        check(abs(p.cell_value(1, 3) - 2.23) < 1e-9, "P1 品位 2.23")
        check(abs(p.cell_value(35, 3) - 3.11) < 1e-9, "P35 品位 3.11")

        import pyodbc
        check(open(res["mdb"], "rb").read(20).startswith(b"\x00\x01\x00\x00Standard Jet DB"),
              "mdb 是真正的 Standard Jet DB")
        cn = pyodbc.connect("DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
                            "DBQ=%s;" % res["mdb"])
        cur = cn.cursor()
        counts = {}
        for t in ("config_table_3dmine", "constraint_table_3dmine", "pit_blast",
                  "style_table_3dmine", "定位表", "测斜表"):
            cur.execute("SELECT COUNT(*) FROM [%s]" % t)
            counts[t] = cur.fetchone()[0]
        cn.close()
        check(counts == {"config_table_3dmine": 18, "constraint_table_3dmine": 0,
                         "pit_blast": 47, "style_table_3dmine": 5,
                         "定位表": 47, "测斜表": 47},
              "mdb 六张表行数正确（含 3DMine 元数据）")

        holes = parse_txt(TXT)
        g = parse_grades(GRADES.read_text(encoding="utf-8"), holes)
        check(not g.missing and not g.duplicates, "47 个工程号品位全匹配")

        bad = "\n".join(GRADES.read_text(encoding="utf-8").splitlines()[:-1])
        g2 = parse_grades(bad, holes)
        check(g2.missing == ["BS-3940-0915-P47"], "少一行时能指出缺 P47")
    finally:
        shutil.rmtree(td, ignore_errors=True)
    failed = [m for ok, m in checks if not ok]
    print("\n%d/%d 通过" % (len(checks) - len(failed), len(checks)))
    print("结论：" + ("全部通过 ✓" if not failed else "失败：%s" % failed))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
