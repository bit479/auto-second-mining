# -*- coding: utf-8 -*-
"""数据质量层：校验 + 报告 + 多段化验汇总（T02）。"""

from quality.aggregate import RULES, aggregate_grade  # noqa: F401
from quality.check import CHECK_CONFIG, check          # noqa: F401
from quality.report import render_markdown, render_text, summary  # noqa: F401
