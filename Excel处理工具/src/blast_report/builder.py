"""把若干份 3DMine 炮孔数据库报告汇总成一份炮孔数据报告。

汇总规则（与人工成果一致）：
1. 按"品位档"归组，档位由高到低排列；同档内保持源文件出现顺序；
2. 每个档位列出全部明细行，随后一行"小计"；
3. 末尾一行"合计"汇总所有"小计"；
4. 小计/合计的体积、重量、金属量直接求和；
   平均品位 = 金属量 × 100 ÷ 重量（不是简单平均）；
5. 可选在每个源文件原始报告追加在汇总表下方（便于截图贴进 CAD）。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Sequence

from ..excel_core.writer import SheetPlan, StyleSpec, write_workbook
from .parser import BlockRecord, SourceReport
from .schema import METAL_SCALE, OUTPUT_COLUMNS, grade_sort_key

__all__ = ["MergeOptions", "merge_reports", "group_records"]

_NCOL = len(OUTPUT_COLUMNS)          # 6
_C_VOL, _C_WGT, _C_GRD, _C_MTL = "C", "D", "E", "F"


@dataclass
class MergeOptions:
    title: str | None = None        # 大标题，默认取输出文件名
    with_appendix: bool = True      # 是否追加各源文件原始报告
    appendix_gap: int = 8           # 汇总区与附录区之间空多少行
    use_formula: bool = True        # 小计/合计写公式（False 则写死数值）
    sheet_name: str = "Sheet1"
    column_widths: dict[str, float] = field(
        default_factory=lambda: {"A": 18.55, "B": 9.0, "C": 12.0, "D": 12.0, "E": 18.55, "F": 18.55}
    )


def group_records(records: Sequence[BlockRecord]) -> list[tuple[str, list[BlockRecord]]]:
    """按品位档归组，档位由高到低；同档保持录入顺序。"""
    buckets: dict[str, list[BlockRecord]] = {}
    for rec in records:
        buckets.setdefault(rec.grade_type, []).append(rec)
    ordered = sorted(buckets.items(), key=lambda kv: grade_sort_key(kv[0]))
    return [(k, list(v)) for k, v in ordered]


def _sum_expr(col: str, rows: Sequence[int]) -> str | None:
    if not rows:
        return None
    if len(rows) == 1:
        return "=%s%d" % (col, rows[0])
    return "=" + "+".join("%s%d" % (col, r) for r in rows)


def _num(values: Sequence[Any]) -> float:
    return sum(v for v in values if isinstance(v, (int, float)) and not isinstance(v, bool))


def _avg_grade(metal: float | None, weight: float | None) -> float | None:
    if not weight:
        return None
    return (metal or 0.0) * METAL_SCALE / weight


def _blank_row() -> list[Any]:
    return [""] * _NCOL


def merge_reports(inputs: Sequence[str] | Sequence[SourceReport],
                  output: str,
                  options: MergeOptions | None = None) -> dict:
    """汇总并写出报告，返回统计信息。

    Parameters
    ----------
    inputs
        源报告路径列表，或已解析的 :class:`SourceReport` 列表。
    output
        输出 xlsx 路径。
    """
    from .parser import parse_report_file  # 局部导入避免循环

    opt = options or MergeOptions()

    reports: list[SourceReport] = []
    for item in inputs:
        if isinstance(item, SourceReport):
            reports.append(item)
        else:
            reports.append(parse_report_file(item))
    reports = [r for r in reports if r.records or r.raw_rows]
    if not reports:
        raise ValueError("没有解析到任何有效数据，请检查输入文件")

    records: list[BlockRecord] = []
    for i, rep in enumerate(reports):
        for j, rec in enumerate(rep.records):
            rec.order = i * 1000 + j
            records.append(rec)

    groups = group_records(records)

    # ---- 第一遍：排布行号（第 1 行标题，第 2 行表头，数据从第 3 行起）----
    row_no = 3
    group_rows: list[tuple[str, list[BlockRecord], list[int], int]] = []
    subtotal_rows: list[int] = []
    for key, recs in groups:
        detail_rows = []
        for _ in recs:
            detail_rows.append(row_no)
            row_no += 1
        subtotal = row_no
        row_no += 1
        subtotal_rows.append(subtotal)
        group_rows.append((key, recs, detail_rows, subtotal))
    total_row = row_no

    # ---- 第二遍：填值 ----
    body: list[list[Any]] = []

    for key, recs, detail_rows, subtotal in group_rows:
        for rec in recs:
            body.append([rec.grade_type, rec.body, rec.volume, rec.weight, rec.grade, rec.metal])
        body.append(_subtotal_row(detail_rows, subtotal, recs, opt.use_formula))

    body.append(_total_row(subtotal_rows, total_row, groups, opt.use_formula))

    summary_end = len(body) - 1   # 合计行在 body 中的下标

    # ---- 附录：各源文件原始报告 ----
    appendix_titles: list[int] = []
    if opt.with_appendix:
        body.extend(_blank_row() for _ in range(opt.appendix_gap))
        for rep in reports:
            appendix_titles.append(len(body))
            body.append([rep.title] + [""] * (_NCOL - 1))
            body.append(_pad_row(rep.header))
            for raw in rep.raw_rows:
                body.append(_pad_row(raw))
            body.append(_blank_row())

    def row_style(row, index):
        """汇总区带边框；附录区不带边框，标题加粗。"""
        if index > summary_end:
            return {"bold": index in appendix_titles, "border": False}
        return {"bold": False, "border": True}

    title = opt.title or os.path.splitext(os.path.basename(output))[0]

    plan = SheetPlan(
        name=opt.sheet_name,
        title=title,
        columns=OUTPUT_COLUMNS,
        rows=body,
        merged=[],
        style=StyleSpec(
            border=True,
            center=True,
            column_widths=opt.column_widths,
            number_formats={_C_GRD: "0.00_);[Red]\\(0.00\\)"},
        ),
        row_style=row_style,
    )
    write_workbook(output, [plan])

    return {
        "output": os.path.abspath(output),
        "sources": [r.name for r in reports],
        "blocks": len(records),
        "tiers": [k for k, _ in groups],
        "total": _collect_total(groups),
        "total_row": total_row,
    }


def _subtotal_row(detail_rows, subtotal, recs, use_formula: bool) -> list[Any]:
    if use_formula:
        return [
            "小计", "",
            _sum_expr(_C_VOL, detail_rows),
            _sum_expr(_C_WGT, detail_rows),
            "=%s%d/%s%d*%g" % (_C_MTL, subtotal, _C_WGT, subtotal, METAL_SCALE),
            _sum_expr(_C_MTL, detail_rows),
        ]
    volume = _num([r.volume for r in recs])
    weight = _num([r.weight for r in recs])
    metal = _num([r.metal for r in recs])
    return ["小计", "", volume, weight, _avg_grade(metal, weight), metal]


def _total_row(subtotal_rows, total_row, groups, use_formula: bool) -> list[Any]:
    if use_formula:
        return [
            "合计", "",
            _sum_expr(_C_VOL, subtotal_rows),
            _sum_expr(_C_WGT, subtotal_rows),
            "=%s%d/%s%d*%g" % (_C_MTL, total_row, _C_WGT, total_row, METAL_SCALE),
            _sum_expr(_C_MTL, subtotal_rows),
        ]
    all_recs = [r for _, recs in groups for r in recs]
    volume = _num([r.volume for r in all_recs])
    weight = _num([r.weight for r in all_recs])
    metal = _num([r.metal for r in all_recs])
    return ["合计", "", volume, weight, _avg_grade(metal, weight), metal]


def _collect_total(groups) -> dict:
    all_recs = [r for _, recs in groups for r in recs]
    volume = _num([r.volume for r in all_recs])
    weight = _num([r.weight for r in all_recs])
    metal = _num([r.metal for r in all_recs])
    return {"体积": volume, "重量": weight, "金属量": metal, "平均品位": _avg_grade(metal, weight)}


def _pad_row(values: Sequence[Any]) -> list[Any]:
    row = list(values)[:_NCOL]
    row += [""] * (_NCOL - len(row))
    return row
