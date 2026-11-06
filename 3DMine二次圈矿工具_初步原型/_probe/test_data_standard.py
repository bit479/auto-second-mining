# -*- coding: utf-8 -*-
"""T02.1（质量加固）+ T03.1（标准化数据结构）自检。

用法:
    python _probe/test_data_standard.py

覆盖：1008 读取、Excel/SQLite 双源、不同表头映射、未知字段/单位、多段化验保留、
原始追溯、平台日期隔离、NaN/无穷/逆序/越界区间、旧结构兼容、只读安全。
不修改任何生产数据（真实 1008 只读，合成样本写临时目录）。
"""
from __future__ import annotations

import hashlib
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))

from data import models, schemas                       # noqa: E402
from data.readers import _to_float, read_holes, to_legacy_holes  # noqa: E402
from data.adapters import load                         # noqa: E402
from quality.check import check as run_check           # noqa: E402

CHECKS = []


def check(ok: bool, msg: str) -> None:
    CHECKS.append(bool(ok))
    print("  %s  %s" % ("OK  " if ok else "FAIL", msg))


def codes(issues) -> set:
    return {i.code for i in issues}


def _write_xlsx(path: Path, sheets: dict) -> None:
    import openpyxl
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for name, rows in sheets.items():
        ws = wb.create_sheet(name)
        for r in rows:
            ws.append(list(r))
    wb.save(str(path))


CLEAN = {
    "定位表": [
        ["工程号", "开孔坐标E", "开孔坐标N", "开孔坐标R", "轨迹类型", "最大孔深"],
        ["BS-3940-1008-P1", 470103.985, 4349729.2, 3940.856, "直线", 10.856],
        ["BS-3940-1008-P2", 470106.211, 4349731.335, 3940.788, "直线", 10.788],
        ["BS-3940-1008-P3", 470103.381, 4349733.749, 3941.177, "曲线", 11.177],
    ],
    "pit_blast": [
        ["工程号", "从", "至", "Au"],
        ["BS-3940-1008-P1", 0.0, 10.856, 1.108],
        ["BS-3940-1008-P2", 0.0, 10.788, 1.35],
        ["BS-3940-1008-P3", 0.0, 11.177, 1.323],
    ],
}


def test_clean_read_and_meta() -> None:
    print("\n[读取 + 元数据]")
    tmp = Path(tempfile.mkdtemp(prefix="t031_"))
    p = tmp / "clean.xlsx"
    _write_xlsx(p, CLEAN)
    ds = read_holes(p, platform="3940", date="1008")
    check(len(ds.loc_rows) == 3, "定位表 3 条")
    check(ds.meta.source == "excel" and ds.meta.source_file == str(p), "meta 来源已记录")
    check(ds.meta.platform == "3940" and ds.meta.date == "1008", "平台/日期隔离元数据")
    check(ds.meta.grade_unit == models.UNKNOWN, "品位单位默认 UNKNOWN（不擅自认定 g/t）")
    check(ds.meta.coord_sys == models.UNKNOWN, "坐标系默认 UNKNOWN")
    # 轨迹类型保留
    t = {h.hid: h.trajectory for h in ds.loc_rows}
    check(t["BS-3940-1008-P3"] == "曲线", "轨迹类型保留（曲线）")
    check(t["BS-3940-1008-P1"] == "直线", "轨迹类型保留（直线）")
    # 追溯：sheet + row + raw
    h = ds.loc_by_hid()["BS-3940-1008-P1"]
    check(h.sheet == "定位表" and h.row == 2, "追溯 sheet/row")
    check(h.raw.get("工程号") == "BS-3940-1008-P1" and h.raw.get("开孔坐标E") == 470103.985,
          "追溯原始字段和值")


def test_to_float_nan_inf() -> None:
    print("\n[_to_float NaN/Inf 修复]")
    import math
    check(_to_float(float("nan")) is None, "NaN → None")
    check(_to_float(float("inf")) is None, "+Inf → None")
    check(_to_float(float("-inf")) is None, "-Inf → None")
    check(_to_float("nan") is None, "字符串 nan → None")
    check(_to_float("") is None and _to_float(None) is None, "空值 → None")
    check(_to_float("12.5") == 12.5 and _to_float(0) == 0.0, "正常数值不受影响")


def test_sqlite_vs_excel() -> None:
    print("\n[Excel 与 SQLite 双源一致]")
    tmp = Path(tempfile.mkdtemp(prefix="t031_sqlite_"))
    x = tmp / "c.xlsx"
    _write_xlsx(x, CLEAN)
    db = tmp / "c.db"
    con = sqlite3.connect(str(db))
    for tbl, rows in CLEAN.items():
        con.execute("CREATE TABLE %s (%s)" % (tbl, ",".join(
            '"%s"' % c for c in rows[0])))
        for r in rows[1:]:
            con.execute("INSERT INTO %s VALUES (%s)" % (tbl, ",".join("?" * len(r))), list(r))
    con.commit(); con.close()

    dx = load(x)
    ds = load(db)
    check(ds.meta.source == "sqlite", "SQLite 来源识别")
    check(set(dx.loc_by_hid()) == set(ds.loc_by_hid()), "双源工程号集合一致")
    a = dx.loc_by_hid()["BS-3940-1008-P2"]; b = ds.loc_by_hid()["BS-3940-1008-P2"]
    check(abs(a.x - b.x) < 1e-6 and abs(a.depth - b.depth) < 1e-6, "双源坐标/孔深一致")


def test_custom_header_mapping() -> None:
    print("\n[不同表头字段映射 + 未知字段]")
    tmp = Path(tempfile.mkdtemp(prefix="t031_hdr_"))
    p = tmp / "alt.xlsx"
    _write_xlsx(p, {
        "定位表": [
            ["孔号", "东坐标", "北坐标", "高程", "备注X", "孔深"],
            ["H1", 470101.0, 4349701.0, 3940.0, "abc", 9.5],
        ],
        "pit_blast": [
            ["孔号", "从", "至", "Au"],
            ["H1", 0.0, 9.5, 1.2],
        ],
    })
    alt = {"loc": {"hid": ["孔号"], "x": ["东坐标"], "y": ["北坐标"],
                   "z": ["高程"], "depth": ["孔深"]},
           "blast": {"hid": ["孔号"], "frm": ["从"], "to": ["至"], "grade": ["Au"]}}
    ds = read_holes(p, schema=alt)
    check(len(ds.loc_rows) == 1 and ds.loc_by_hid()["H1"].x == 470101.0, "自定义表头映射成功")
    # 未知字段「备注X」应输出提示，不静默
    um = [i for i in ds.issues if i.code == "unmapped_column"]
    check(any("备注X" in i.where for i in um), "未知列头「备注X」有明确提示")


def test_multi_interval_preserved() -> None:
    print("\n[多段化验完整保留（不合并）]")
    tmp = Path(tempfile.mkdtemp(prefix="t031_multi_"))
    p = tmp / "m.xlsx"
    _write_xlsx(p, {
        "定位表": [["工程号", "开孔坐标E", "开孔坐标N", "开孔坐标R", "最大孔深"],
                    ["M", 470101.0, 4349701.0, 3940.0, 10.0]],
        "pit_blast": [["工程号", "从", "至", "Au"],
                      ["M", 0.0, 4.0, 1.1],
                      ["M", 4.0, 10.0, 0.9]],
    })
    ds = read_holes(p)
    segs = ds.intervals_by_hid()["M"]
    check(len(segs) == 2, "两段化验完整保留")
    check(segs[0].grade == 1.1 and segs[1].grade == 0.9, "两段品位未被提前合并")
    iss = run_check(ds)
    check("multi_interval" in codes(iss), "多段化验有告警")


def test_interval_checks() -> None:
    print("\n[区间逆序 / 越界校验]")
    tmp = Path(tempfile.mkdtemp(prefix="t031_intv_"))
    p = tmp / "i.xlsx"
    _write_xlsx(p, {
        "定位表": [["工程号", "开孔坐标E", "开孔坐标N", "开孔坐标R", "最大孔深"],
                    ["REV", 470101.0, 4349701.0, 3940.0, 10.0],
                    ["OVR", 470102.0, 4349702.0, 3940.0, 8.0]],
        "pit_blast": [["工程号", "从", "至", "Au"],
                      ["REV", 6.0, 4.0, 1.0],      # 逆序
                      ["OVR", 0.0, 9.5, 1.0]],     # to > depth(8.0)
    })
    iss = run_check(read_holes(p))
    c = codes(iss)
    check("interval_reversed" in c, "逆序区间检出")
    check("interval_exceeds_depth" in c, "区间超孔深检出")


def test_legacy_compat_and_readonly() -> None:
    print("\n[旧结构兼容 + 只读安全]")
    tmp = Path(tempfile.mkdtemp(prefix="t031_cmp_"))
    p = tmp / "c.xlsx"
    _write_xlsx(p, CLEAN)
    before = hashlib.md5(p.read_bytes()).hexdigest()
    ds = read_holes(p)
    after = hashlib.md5(p.read_bytes()).hexdigest()
    check(before == after, "读取不修改源文件（md5 不变）")

    legacy = to_legacy_holes(ds)
    check(set(legacy) == {"BS-3940-1008-P1", "BS-3940-1008-P2", "BS-3940-1008-P3"},
          "to_legacy_holes 结构兼容")
    check(abs(legacy["BS-3940-1008-P1"].grade - 1.108) < 1e-9, "旧结构品位 = last 规则")
    check(abs(legacy["BS-3940-1008-P1"].x - 470103.985) < 1e-9, "旧结构坐标一致")


def test_real_1008() -> None:
    print("\n[真实 1008 回归]")
    p = Path(r"E:\AAAWK\NNN CRT\auto-second-mining\北部山头3940平台2026"
             r"\7、单日数据\北部山头3940平台-1008\1、3940平台 炮孔数据库1008.xls")
    if not p.exists():
        check(True, "本机无 1008，跳过")
        return
    from oreblocks import load_holes_xls
    legacy = load_holes_xls(p)
    ds = read_holes(p)
    check(set(ds.loc_by_hid()) == set(legacy), "工程号集合一致（%d 孔）" % len(legacy))
    bad = sum(1 for hid, h in legacy.items()
              if abs(ds.loc_by_hid()[hid].x - h.x) > 1e-6
              or abs(ds.loc_by_hid()[hid].depth - h.depth) > 1e-6)
    check(bad == 0, "逐孔坐标/孔深一致（%d 处不一致）" % bad)
    iss = run_check(ds)
    check(not [i for i in iss if i.severity == "error"], "无阻断项")


def main() -> int:
    test_clean_read_and_meta()
    test_to_float_nan_inf()
    test_sqlite_vs_excel()
    test_custom_header_mapping()
    test_multi_interval_preserved()
    test_interval_checks()
    test_legacy_compat_and_readonly()
    test_real_1008()

    failed = CHECKS.count(False)
    print("\n" + "=" * 60)
    print("共 %d 项检查，%d 项通过" % (len(CHECKS), len(CHECKS) - failed))
    if failed:
        print("结论：有 %d 项未通过" % failed)
        return 1
    print("结论：全部通过 ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
