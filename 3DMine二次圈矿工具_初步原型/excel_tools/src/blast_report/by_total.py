"""按「总计」行汇总。

与 :mod:`builder` 的旧口径（把每行明细拆出来按品位档归组）不同，
这里**一份源文件只取它的「总计」行，整行当成一个矿块**：

* 体积 / 重量 / 平均品位 / 金属量 四个值原样搬用，不重新计算；
* 档位由「总计的品位」落在哪个标准区间反推（源文件自己的档位不能直接用：
  一份文件的总计可能跨了好几个源档位）。**区间按矿段取** —— 金斗山
  ``0.5-1 / 1-1.5 / 1.5-3 / ≥3``，中心矿段 ``0.5-0.8 / 0.8-1 / ≥1``，
  具体用哪套由 :func:`profiles.resolve_profile` 按「当前矿段」决定；
* 同档内保持源文件的先后顺序；体号在最终顺序上重新编号 1→N。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from .parser import BlockRecord, SourceReport
from .profiles import GradeProfile, get_profile
from .schema import COL_GRADE, COL_METAL, COL_VOLUME, COL_WEIGHT, METAL_SCALE

__all__ = ["TotalBlock", "collect_total_blocks", "records_from_totals"]


@dataclass
class TotalBlock:
    """一个矿块 = 一份源文件的「总计」行。"""

    source: str
    grade_type: str
    volume: float | None
    weight: float | None
    grade: float | None
    metal: float | None
    order: int


def _num(value: Any) -> float | None:
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def collect_total_blocks(reports: Sequence[SourceReport],
                         profile: GradeProfile | None = None) -> tuple[list[TotalBlock], list[str]]:
    """逐份取「总计」行，按 ``profile``（当前矿段）落档，返回 ``(矿块列表, 告警列表)``。"""
    bands = profile or get_profile(None)
    blocks: list[TotalBlock] = []
    warnings: list[str] = []

    for i, rep in enumerate(reports):
        values = rep.total_values
        if not values or all(_num(values.get(k)) is None
                             for k in (COL_VOLUME, COL_WEIGHT, COL_METAL)):
            warnings.append("%s：没找到「总计」行，这份文件不产出矿块" % rep.name)
            continue

        volume = _num(values.get(COL_VOLUME))
        weight = _num(values.get(COL_WEIGHT))
        metal = _num(values.get(COL_METAL))
        grade = _num(values.get(COL_GRADE))
        if grade is None and weight:
            grade = (metal or 0.0) * METAL_SCALE / weight
            warnings.append("%s：总计行没有品位值，已按 金属量×100÷重量 补算" % rep.name)

        grade_type = bands.band_of(grade)
        if grade_type.startswith("<") and grade is not None:
            warnings.append(
                "%s：总计品位 %.3f 低于「%s」的工业品位下限 %.3f，"
                "已单列 %s 一档（不并进最低档，请核对是否混进了废石块）"
                % (rep.name, grade, bands.name, bands.cutoff, grade_type))

        blocks.append(TotalBlock(
            source=rep.name,
            grade_type=grade_type,
            volume=volume,
            weight=weight,
            grade=grade,
            metal=metal,
            order=i,
        ))
    return blocks, warnings


def records_from_totals(reports: Sequence[SourceReport],
                        profile: GradeProfile | None = None,
                        warnings: list[str] | None = None) -> list[BlockRecord]:
    """给 :func:`builder.merge_reports` 用的矿块构造器。

    ``profile`` = 当前矿段分级；``warnings`` 传进来时把告警一起带出去
    （界面上要显示，不能只打印到控制台）。
    """
    blocks, collected = collect_total_blocks(reports, profile)
    for message in collected:
        print("[警告] %s" % message)
    if warnings is not None:
        warnings.extend(collected)
    return [
        BlockRecord(
            grade_type=block.grade_type,
            body=None,                 # 体号由 builder 在最终顺序上重新编号
            volume=block.volume,
            weight=block.weight,
            grade=block.grade,
            metal=block.metal,
            source=block.source,
            order=block.order,
        )
        for block in blocks
    ]
