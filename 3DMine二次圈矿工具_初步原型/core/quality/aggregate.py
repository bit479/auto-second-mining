# -*- coding: utf-8 -*-
"""多段化验的品位汇总（口径待地质负责人确认，见项目计划书「待确认事项」）。

当前生产行为是「同一工程号多行时，后写入的 Au 覆盖前面的」（等价于 rule="last"）。
本模块把可选规则显式化，但**默认不改变生产行为**；检测到多段化验时应由
`quality/check.py` 报「待确认」，而不是在这里悄悄合并。
"""
from __future__ import annotations

RULES = ("last", "first", "max", "min", "simple_avg", "length_weighted")


def aggregate_grade(intervals, rule: str = "last") -> float | None:
    """把同一工程号的多段品位按规则合并成单个品位。

    - intervals 里的 ``grade`` 可能为 None（缺失），会跳过。
    - 一段都没有 → 返回 None。
    - ``length_weighted`` 用 (至-从) 作权重；区间长度为 0 或缺失时退化为等权。
    """
    vals = [(i.frm, i.to, i.grade) for i in intervals if i.grade is not None]
    if not vals:
        return None
    if rule == "last":
        return vals[-1][2]
    if rule == "first":
        return vals[0][2]
    if rule == "max":
        return max(v[2] for v in vals)
    if rule == "min":
        return min(v[2] for v in vals)
    if rule == "simple_avg":
        return sum(v[2] for v in vals) / len(vals)
    if rule == "length_weighted":
        weights = []
        for frm, to, g in vals:
            w = (to - frm) if (frm is not None and to is not None and to > frm) else 1.0
            weights.append(w)
        return sum(v[2] * w for v, w in zip(vals, weights)) / sum(weights)
    raise ValueError("未知品位汇总规则：%s（可选 %s）" % (rule, "/".join(RULES)))
