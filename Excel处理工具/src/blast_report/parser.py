"""解析 3DMine 导出的炮孔数据库报告（单个工作簿）。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from ..excel_core.model import DataTable, to_number, to_text
from ..excel_core.reader import detect_header_row, read_workbook
from .schema import (COL_BODY, COL_GRADE, COL_METAL, COL_TYPE, COL_VOLUME,
                     COL_WEIGHT, COLUMN_SYNONYMS, NUMERIC_COLUMNS, SUMMARY_TOKENS)

__all__ = ["BlockRecord", "SourceReport", "parse_report_file", "parse_report_files"]


@dataclass
class BlockRecord:
    """一个矿块（体）的一条报告数据。"""

    grade_type: str          # 品位档，如 "1.500-3.000"
    body: Any                # 体号
    volume: float | None     # 体积 m3
    weight: float | None     # 重量 t
    grade: float | None      # 平均品位 g/t
    metal: float | None      # 金属量（百克）
    source: str = ""         # 来源文件名
    order: int = 0           # 全局出现顺序，用于保持同档内的原始次序


@dataclass
class SourceReport:
    """一个源文件的解析结果。"""

    path: str = ""
    title: str = ""                     # 表上方的大标题
    header: list[str] = field(default_factory=list)
    raw_rows: list[list[Any]] = field(default_factory=list)  # 含"小计"行的原始行，用于附录
    records: list[BlockRecord] = field(default_factory=list)

    @property
    def name(self) -> str:
        return os.path.basename(self.path)


def parse_report_file(path: str) -> SourceReport:
    """解析单个报告文件（只取第一个 sheet）。"""
    sheets = read_workbook(path)
    if not sheets:
        return SourceReport(path=path)
    sheet_name, matrix = sheets[0]
    return parse_report_matrix(matrix, path=path, sheet=sheet_name)


def parse_report_matrix(matrix: list[list[Any]], path: str = "", sheet: str = "Sheet1") -> SourceReport:
    """从原始矩阵解析报告。"""
    report = SourceReport(path=path)
    if not matrix:
        return report

    hr = detect_header_row(matrix)
    report.title = to_text(matrix[0][0]) if hr > 0 else ""
    report.header = [to_text(v) for v in matrix[hr] if to_text(v)]

    ncol = len(report.header)
    raw = []
    for row in matrix[hr + 1:]:
        if all(to_text(v) == "" for v in row):
            continue
        raw.append([row[i] if i < len(row) else None for i in range(ncol)])
    report.raw_rows = raw

    table = DataTable.from_matrix(matrix[hr:], name=sheet, source=os.path.basename(path))
    table = table.map_columns(COLUMN_SYNONYMS)
    table = table.drop_rows_matching(COL_TYPE, SUMMARY_TOKENS)
    table = table.filter_blank(COL_TYPE)
    table = table.cast({c: to_number for c in NUMERIC_COLUMNS if c in table.columns})

    for i, row in enumerate(table.rows):
        report.records.append(BlockRecord(
            grade_type=to_text(row.get(COL_TYPE)),
            body=row.get(COL_BODY),
            volume=row.get(COL_VOLUME),
            weight=row.get(COL_WEIGHT),
            grade=row.get(COL_GRADE),
            metal=row.get(COL_METAL),
            source=os.path.basename(path),
            order=i,
        ))
    return report


def parse_report_files(paths) -> list[SourceReport]:
    """批量解析，单个文件失败只告警不中断。"""
    reports = []
    for p in paths:
        try:
            reports.append(parse_report_file(p))
        except Exception as exc:  # noqa: BLE001
            print("[警告] 跳过无法解析的文件 %s：%s" % (p, exc))
    return reports
