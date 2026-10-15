"""Excel 写出层。

负责把数据写成"人能直接用的表"：标题合并居中、表头加粗、全表边框、
冻结窗格、列宽自适应、数字格式、公式或直接写值。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Sequence

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, Side
from openpyxl.utils import get_column_letter

from .reader import column_letter_width, safe_sheet_title

__all__ = ["StyleSpec", "SheetPlan", "write_workbook"]

_THIN = Side(style="thin", color="FF000000")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)
_CENTER = Alignment(horizontal="center", vertical="center")


@dataclass
class StyleSpec:
    """输出样式。默认值与人工炮孔数据报告的版式一致。"""

    font_name: str = "等线"
    title_size: int = 10
    header_size: int = 11
    body_size: int = 11
    title_bold: bool = True
    header_bold: bool = False
    border: bool = True
    center: bool = True
    freeze_header: bool = False
    column_widths: dict[str, float] = field(default_factory=dict)   # {"A": 18.5}
    number_formats: dict[str, str] = field(default_factory=dict)    # {"E": "0.00"}
    auto_width: bool = False


@dataclass
class SheetPlan:
    """一张待写出的工作表。"""

    name: str = "Sheet1"
    title: str | None = None            # 大标题，会跨列合并居中
    columns: Sequence[str] = ()         # 表头
    rows: Sequence[Sequence[Any]] = ()  # 数据行（元素可以是值，也可以是 "=A1+B1" 形式的公式）
    merged: Sequence[str] = ()          # 额外合并区域，如 ["A1:F1"]
    style: StyleSpec = field(default_factory=StyleSpec)
    # 行级样式钩子：row -> {"font_size":.., "bold":.., "border":..}
    row_style: Any = None


def write_workbook(path: str, plans: Sequence[SheetPlan]) -> str:
    """按计划写出工作簿，返回文件路径。"""
    wb = Workbook()
    wb.remove(wb.active)

    for plan in plans:
        ws = wb.create_sheet(safe_sheet_title(plan.name))
        style = plan.style
        start = 1

        if plan.title:
            ncol = max(len(plan.columns), 1)
            ws.cell(1, 1, plan.title)
            ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ncol)
            c = ws.cell(1, 1)
            c.font = Font(name=style.font_name, size=style.title_size, bold=style.title_bold)
            c.alignment = _CENTER
            for col in range(1, ncol + 1):
                ws.cell(1, col).border = _BORDER if style.border else Border()
            start = 2

        if plan.columns:
            for i, name in enumerate(plan.columns, start=1):
                c = ws.cell(start, i, name)
                c.font = Font(name=style.font_name, size=style.header_size, bold=style.header_bold)
                if style.center:
                    c.alignment = _CENTER
                if style.border:
                    c.border = _BORDER
            start += 1

        for offset, row in enumerate(plan.rows):
            r = start + offset
            extra = plan.row_style(row, offset) if plan.row_style else {}
            for i, value in enumerate(row, start=1):
                if value is None:
                    value = ""
                c = ws.cell(r, i, value)
                c.font = Font(
                    name=style.font_name,
                    size=extra.get("font_size", style.body_size),
                    bold=extra.get("bold", False),
                )
                if style.center:
                    c.alignment = _CENTER
                if style.border and extra.get("border", True):
                    c.border = _BORDER
                letter = get_column_letter(i)
                if letter in style.number_formats:
                    c.number_format = style.number_formats[letter]

        for ref in plan.merged:
            ws.merge_cells(ref)

        for letter, width in style.column_widths.items():
            ws.column_dimensions[letter].width = width
        if style.auto_width:
            for i in range(1, len(plan.columns) + 1):
                letter = get_column_letter(i)
                if letter in style.column_widths:
                    continue
                values = [plan.columns[i - 1]] + [r[i - 1] for r in plan.rows if i <= len(r)]
                ws.column_dimensions[letter].width = column_letter_width(values)

        if style.freeze_header and plan.columns:
            ws.freeze_panes = ws.cell(start, 1)

    directory = os.path.dirname(os.path.abspath(path))
    if directory:
        os.makedirs(directory, exist_ok=True)
    wb.save(path)
    return path
