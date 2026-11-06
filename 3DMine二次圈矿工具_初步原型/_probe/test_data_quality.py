# -*- coding: utf-8 -*-
"""T01/T02 自检：数据模型 + 读取 + 质量检查。

用法:
    python _probe/test_data_quality.py          # 全量（含真实 1008 与合成异常样本）

不修改任何生产数据：合成样本写在临时目录，真实 1008 只读。
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))

from data import models                    # noqa: E402
from data.readers import read_holes        # noqa: E402
from quality.check import check as run_check  # noqa: E402
from quality import report                 # noqa: E402

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


def test_reader_and_clean() -> None:
    print("\n[读取 + 干净样本]")
    tmp = Path(tempfile.mkdtemp(prefix="t01_"))
    p = tmp / "clean.xlsx"
    _write_xlsx(p, {
        "定位表": [
            ["工程号", "开孔坐标E", "开孔坐标N", "开孔坐标R", "轨迹类型", "最大孔深"],
            ["BS-3940-1008-P1", 470103.985, 4349729.2, 3940.856, "直线", 10.856],
            ["BS-3940-1008-P2", 470106.211, 4349731.335, 3940.788, "直线", 10.788],
            ["BS-3940-1008-P3", 470103.381, 4349733.749, 3941.177, "直线", 11.177],
        ],
        "pit_blast": [
            ["工程号", "从", "至", "Au"],
            ["BS-3940-1008-P1", 0.0, 10.856, 1.108],
            ["BS-3940-1008-P2", 0.0, 10.788, 1.35],
            ["BS-3940-1008-P3", 0.0, 11.177, 1.323],
        ],
    })
    ds = read_holes(p)
    check(len(ds.loc_rows) == 3, "定位表读到 3 条记录")
    check(len(ds.intervals) == 3, "pit_blast 读到 3 段化验")
    check(ds.loc_by_hid()["BS-3940-1008-P1"].x == 470103.985, "坐标字段映射正确")
    iss = run_check(ds)
    check(not [i for i in iss if i.severity == "error"], "干净样本无阻断项：%s" % codes(iss))


def test_quality_issues() -> None:
    print("\n[质量异常检测]")
    tmp = Path(tempfile.mkdtemp(prefix="t02_"))
    p = tmp / "dirty.xlsx"
    _write_xlsx(p, {
        "定位表": [
            ["工程号", "开孔坐标E", "开孔坐标N", "开孔坐标R", "最大孔深"],
            ["D1", 470101.0, 4349701.0, 3940.0, 10.0],   # 重复工程号（下面再来一行）
            ["D1", 470102.0, 4349702.0, 3940.0, 10.0],   # dup_hid
            ["D2", 470103.0, 4349703.0, 3940.0, 10.0],   # 近重复坐标（与 D1 距离 <1m? 实际约2.8m，改用 D2b）
            ["D2b", 470103.1, 4349703.05, 3940.0, 10.0], # near_dup_coord（与 D2 距离约0.11m）
            ["MISS", None, None, 3940.0, 10.0],          # missing_coord
            ["ZERO", 470104.0, 4349704.0, 3940.0, 0.0],  # bad_depth
            ["NEG", 470105.0, 4349705.0, 3940.0, 10.0],  # 下面给负品位
            ["HIGH", 470106.0, 4349706.0, 3940.0, 10.0], # 特高品位
            ["MULTI", 470107.0, 4349707.0, 3940.0, 10.0],# 多段化验
            ["NOGRADE", 470108.0, 4349708.0, 3940.0, 10.0],  # pit_blast 缺失
        ],
        "pit_blast": [
            ["工程号", "从", "至", "Au"],
            ["D1", 0.0, 10.0, 1.0],
            ["D2", 0.0, 10.0, 1.0],
            ["D2b", 0.0, 10.0, 1.0],
            ["MISS", 0.0, 10.0, 1.0],
            ["ZERO", 0.0, 10.0, 1.0],
            ["NEG", 0.0, 10.0, -0.5],          # negative_grade
            ["HIGH", 0.0, 10.0, 88.0],         # high_grade（>30 阈值）
            ["MULTI", 0.0, 4.0, 1.1],          # multi_interval
            ["MULTI", 4.0, 10.0, 0.9],         # multi_interval
            ["ORPHAN", 0.0, 10.0, 1.5],        # orphan_interval（定位表无）
        ],
    })
    ds = read_holes(p)
    iss = run_check(ds)
    c = codes(iss)
    check("dup_hid" in c, "检出重复工程号 dup_hid")
    check("near_dup_coord" in c, "检出近重复孔位 near_dup_coord")
    check("missing_coord" in c, "检出缺失坐标 missing_coord")
    check("bad_depth" in c, "检出异常孔深 bad_depth")
    check("missing_grade" in c, "检出缺失品位 missing_grade（与低品位区分）")
    check("orphan_interval" in c, "检出多余工程号 orphan_interval")
    check("negative_grade" in c, "检出负品位 negative_grade")
    check("high_grade" in c, "检出特高品位 high_grade")
    check("multi_interval" in c, "检出多段化验 multi_interval")

    # 定位到行/工程号
    dup = next(i for i in iss if i.code == "dup_hid")
    check("D1" in dup.where and "D1" in dup.message, "异常可定位到工程号：%s" % dup.message)

    # 报告可渲染
    md = report.render_markdown(iss, source=str(p))
    check("阻断" in md and "multi_interval" in md, "Markdown 报告可渲染")
    print("\n---- 报告摘要 ----")
    print(report.render_text(iss)[:600])


def test_multi_interval_aggregate() -> None:
    print("\n[多段化验汇总口径（待确认，默认不改生产行为）]")
    from quality import aggregate
    segs = [models.SampleInterval("H", 0.0, 4.0, 1.1, row=1),
            models.SampleInterval("H", 4.0, 10.0, 0.9, row=2)]
    check(aggregate.aggregate_grade(segs, "last") == 0.9, "last 规则（=当前生产行为）")
    check(aggregate.aggregate_grade(segs, "first") == 1.1, "first 规则")
    check(aggregate.aggregate_grade(segs, "max") == 1.1, "max 规则")
    check(abs(aggregate.aggregate_grade(segs, "simple_avg") - 1.0) < 1e-9, "simple_avg 规则")
    lw = aggregate.aggregate_grade(segs, "length_weighted")
    check(abs(lw - (1.1 * 4 + 0.9 * 6) / 10) < 1e-9, "length_weighted 规则 = %.4f" % lw)
    check(aggregate.aggregate_grade([], "last") is None, "无化验段返回 None")


def test_real_1008_equivalence() -> None:
    print("\n[真实 1008：与 oreblocks.load_holes_xls 等价]")
    p = Path(r"E:\AAAWK\NNN CRT\auto-second-mining\北部山头3940平台2026"
             r"\7、单日数据\北部山头3940平台-1008\1、3940平台 炮孔数据库1008.xls")
    if not p.exists():
        check(True, "本机没有 1008 数据库，跳过等价核对")
        return
    from oreblocks import load_holes_xls
    legacy = load_holes_xls(p)
    ds = read_holes(p)
    loc = ds.loc_by_hid()
    check(set(loc.keys()) == set(legacy.keys()), "工程号集合一致（%d 孔）" % len(legacy))
    bad = 0
    for hid, h in legacy.items():
        r = loc.get(hid)
        if r is None:
            bad += 1
            continue
        if abs(r.x - h.x) > 1e-6 or abs(r.y - h.y) > 1e-6 or abs(r.z - h.z) > 1e-6 \
                or abs(r.depth - h.depth) > 1e-6:
            bad += 1
    check(bad == 0, "逐孔坐标/孔深一致（%d 处不一致）" % bad)
    iss = run_check(ds)
    errs = [i for i in iss if i.severity == "error"]
    print("  真实 1008 质量检查：%s" % report.summary(iss))
    check(not errs, "真实 1008 无阻断项（%d 条阻断）" % len(errs))


def main() -> int:
    test_reader_and_clean()
    test_quality_issues()
    test_multi_interval_aggregate()
    test_real_1008_equivalence()

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
