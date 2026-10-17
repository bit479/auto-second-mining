# -*- coding: utf-8 -*-
"""自检：**格式自适应**（xls / xlsx 混着来也不崩）。

背景（2026-10 真实故障）：南部山头那套数据的扩展名与真实格式和北部山头相反 ——
``1、…炮孔数据表.xlsx`` 是真 xlsx、``3、…矿块报告.xls`` 是真 BIFF，
旧代码按扩展名选读取器，于是同时报：

* ``炮孔数据报告 (.xlsx)：openpyxl does not support the old .xls file format``
* ``炮孔数据库 (.xls)：formatting_info=True not yet implemented``

本自检覆盖六件事：

1. 魔数嗅探：扩展名与内容一致/相反都能认对；
2. 南部山头沙箱：``--daily`` 预演不再抛异常，四类文件都识别到；
3. 并入 xlsx 数据库：新孔追加上去，值/样式对，其余工作表（含 ``每日坐标``）仍在；
4. 并入 xls 综合报告：块追加到末尾，原有行一字不动，其余 3 个 sheet 不动，标题行合并；
5. 重复执行幂等：报告跳过、数据库新增 0 行；
6. 合计自检在 BIFF 源上也能跑。

数据缺口时自动跳过（只在国内这台机器上有原始数据）。

用法::

    python tests/test_formats.py
"""

from __future__ import annotations

import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import xlrd  # noqa: E402
from openpyxl import load_workbook  # noqa: E402

from src.daily_merge import db_xls, report_xlsx  # noqa: E402
from src.daily_merge.pipeline import DailyMergeOptions, run  # noqa: E402
from src.daily_merge.schema import KIND_DWG, KIND_MDB, KIND_REPORT, KIND_XLS  # noqa: E402
from src.excel_core.filetype import FMT_XLS, FMT_XLSX, sniff  # noqa: E402

NAN_BASE = (r"D:\WK\26.09.22南部山头二号矿体\南部山头新增Ⅱ号矿体资料"
            r"\二次圈矿资料\南部山头2026\南部山头3970平台-2026")
BEI_MASTER = r"D:\WK\N CRT\北部山头3940平台2026"
SANDBOX = os.path.join(ROOT, "_out", "format_test")

MASTER_XLSX = "1、3970平台炮孔数据表.xlsx"
MASTER_MDB = "2、南部山头3970平台炮孔数据库.mdb"
MASTER_REPORT = "3、南部山头3970平台数据库矿块报告-2026年综合表.xls"
DAY_DIR = "南部山头3970平台-0719"

_checks: list[tuple[bool, str]] = []


def check(ok: bool, message: str) -> None:
    _checks.append((bool(ok), message))
    print("  %s  %s" % ("OK  " if ok else "FAIL", message))


def build_sandbox() -> str:
    if os.path.exists(SANDBOX):
        shutil.rmtree(SANDBOX)
    base = os.path.join(SANDBOX, "平台")
    day = os.path.join(base, "7、单日数据", DAY_DIR)
    os.makedirs(day)
    os.makedirs(os.path.join(base, "6、3970平台二次圈矿矿块图"))
    for name in (MASTER_XLSX, MASTER_MDB, MASTER_REPORT):
        shutil.copy2(os.path.join(NAN_BASE, name), os.path.join(base, name))
    src_day = os.path.join(NAN_BASE, "7、单日数据", DAY_DIR)
    for name in os.listdir(src_day):
        s = os.path.join(src_day, name)
        if os.path.isfile(s):
            shutil.copy2(s, os.path.join(day, name))
    return day


def snapshot(path: str) -> tuple[list[str], list[list[list]]]:
    """把 xls 的全部 sheet 内容读成快照（值）。"""
    book = xlrd.open_workbook(path)
    try:
        names = book.sheet_names()
        grids = [[book.sheet_by_name(n).row_values(r)
                  for r in range(book.sheet_by_name(n).nrows)] for n in names]
        return names, grids
    finally:
        book.release_resources()


def main() -> int:
    if not os.path.isdir(NAN_BASE):
        print("没找到南部山头原始数据，跳过：%s" % NAN_BASE)
        return 0

    print("=" * 74)
    print("[1/6] 魔数嗅探")
    bei = os.path.join(BEI_MASTER, "1、北部山头3940平台 炮孔数据库-2026.xls")
    if os.path.isfile(bei):
        check(sniff(bei) == FMT_XLS, "北部山头 数据库(.xls) -> BIFF")
    check(sniff(os.path.join(NAN_BASE, MASTER_XLSX)) == FMT_XLSX,
          "南部山头 炮孔数据表(.xlsx) -> 真 xlsx")
    check(sniff(os.path.join(NAN_BASE, MASTER_REPORT)) == FMT_XLS,
          "南部山头 综合报告(.xls) -> 真 BIFF")
    check(sniff(os.path.join(NAN_BASE, "7、单日数据", DAY_DIR,
                             "3970平台 0719炮孔数据报告.xlsx")) == FMT_XLSX,
          "南部山头 单日报告(.xlsx) -> 真 xlsx")

    day_dir = build_sandbox()
    base = os.path.join(SANDBOX, "平台")

    print("\n[2/6] 预演（旧代码在这里抛异常）")
    preview = run(DailyMergeOptions(day_dir=day_dir, dry_run=True))
    kinds = [k for k, _s, _d in preview["plan"].pairs]
    check(not preview["errors"], "预演没有报错：%s" % (preview["errors"] or "无"))
    check(set(kinds) == {KIND_XLS, KIND_MDB, KIND_REPORT, KIND_DWG},
          "识别到 4 类文件：%s" % "/".join(kinds))
    check(preview["results"][KIND_REPORT]["added"] > 0,
          "报告块预计追加 %d 行" % preview["results"][KIND_REPORT]["added"])

    print("\n[3/6] xlsx 数据库写入（造一组 TEST- 新孔）")
    day_src = os.path.join(day_dir, "1、3970平台 炮孔数据库0719.xls")
    fake = os.path.join(SANDBOX, "test_holes.xls")
    book = xlrd.open_workbook(day_src, formatting_info=True)
    from xlutils.filter import XLRDReader, XLWTWriter, process

    writer = XLWTWriter()
    process(XLRDReader(book, "x.xls"), writer)
    wt = writer.output[0][1]
    for table in ("定位表", "测斜表", "pit_blast"):
        ws, sh = wt.get_sheet(table), book.sheet_by_name(table)
        for r in range(1, sh.nrows):
            if sh.cell_value(r, 0) in (None, ""):
                continue
            ws.write(r, 0, "TEST-" + str(sh.cell_value(r, 0)),
                     writer.style_list[sh.cell(r, 0).xf_index])
    wt.save(fake)

    dst_xlsx = os.path.join(base, MASTER_XLSX)
    before_sheets = load_workbook(dst_xlsx).sheetnames
    before_rows = {}
    wb = load_workbook(dst_xlsx, data_only=True)
    for name in ("定位表", "测斜表", "pit_blast"):
        before_rows[name] = [[wb[name].cell(r, c).value
                              for c in range(1, wb[name].max_column + 1)]
                             for r in range(2, wb[name].max_row + 1)]
    wb.close()

    res = db_xls.merge_xls(fake, dst_xlsx)
    check(res["added"] > 0, "追加了 %d 行" % res["added"])
    check(res["format"] == {"src": FMT_XLS, "dst": FMT_XLSX}, "格式识别：xls 源 -> xlsx 总表")

    wb = load_workbook(dst_xlsx, data_only=True)
    check(wb.sheetnames == before_sheets, "工作表没少也没多：%s" % "/".join(wb.sheetnames))
    last = wb["定位表"].max_row
    check(str(wb["定位表"].cell(last, 1).value).startswith("TEST-"),
          "新孔落在最后一行：%s" % wb["定位表"].cell(last, 1).value)
    untouched = True
    for name, grid in before_rows.items():
        ws = wb[name]
        for i, row in enumerate(grid):
            # 只比"原本就有内容"的行：总表末尾常带一串只有格式的空行，追加时正好填进去
            if not any(v is not None and str(v).strip() != "" for v in row):
                continue
            for j, value in enumerate(row):
                if ws.cell(i + 2, j + 1).value != value:
                    untouched = False
    check(untouched, "原有内容逐值未动")
    has_daily = "每日坐标" in wb.sheetnames
    check(has_daily, "「每日坐标」等其它工作表仍在")
    wb.close()

    print("\n[4/6] xls 综合报告写入")
    report_master = os.path.join(base, MASTER_REPORT)
    names_before, grids_before = snapshot(report_master)
    result = run(DailyMergeOptions(day_dir=day_dir))
    check(not result["errors"], "正式并入没有报错：%s" % (result["errors"] or "无"))
    added = result["results"][KIND_REPORT]["added"]
    check(added > 0, "报告追加 %d 行" % added)

    names_after, grids_after = snapshot(report_master)
    check(names_after == names_before, "4 个 sheet 都还在：%s" % "/".join(names_after))
    untouched = True
    for idx, name in enumerate(names_before):
        old, new = grids_before[idx], grids_after[idx]
        for r, row in enumerate(old):
            if new[r] != row:
                untouched = False
                break
    check(untouched, "原有内容一字未改")
    tail = grids_after[0][-added:]
    check("报告" in str(tail[0][0]), "新块标题行：%r" % tail[0][0])
    check(str(tail[1][0]).strip() == "类型", "新块表头行首列是「类型」")
    check(str(tail[-1][0]).strip() in ("合计", "总计"),
          "新块末尾是「%s」" % tail[-1][0])
    book = xlrd.open_workbook(report_master, formatting_info=True)
    merged = [m for m in book.sheet_by_index(0).merged_cells
              if m[0] >= len(grids_before[0])]
    check(bool(merged), "标题行合并单元格已建：%s" % merged)
    book.release_resources()

    print("\n[5/6] 重复执行幂等")
    again = run(DailyMergeOptions(day_dir=day_dir))
    check(again["results"][KIND_REPORT].get("skipped") is True, "报告块被跳过，没重复粘")
    check(again["results"][KIND_XLS]["added"] == 0, "数据库新增 0 行")
    names2, grids2 = snapshot(report_master)
    check(len(grids2[0]) == len(grids_after[0]), "报告行数没再增长")

    print("\n[6/6] 合计自检（xlsx 源）")
    info = report_xlsx.check_totals(os.path.join(
        day_dir, "3970平台 0719炮孔数据报告.xlsx"))
    check(info.get("checked") is True, "自检跑通，明细 %s 行" % info.get("detail_rows"))
    check(not info.get("mismatches"),
          "合计与明细之和一致：%s" % (info.get("mismatches") or "无差异"))

    passed = sum(1 for ok, _ in _checks if ok)
    print("\n" + "=" * 74)
    print("共 %d 项检查，%d 项通过" % (len(_checks), passed))
    print("结论：" + ("全部一致 ✓" if passed == len(_checks) else "存在问题 ✗"))
    if os.path.isdir(SANDBOX):
        shutil.rmtree(SANDBOX, ignore_errors=True)
    return 0 if passed == len(_checks) else 1


if __name__ == "__main__":
    sys.exit(main())
