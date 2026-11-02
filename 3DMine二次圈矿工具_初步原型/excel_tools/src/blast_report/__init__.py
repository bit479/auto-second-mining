"""炮孔数据报告业务层：解析 3DMine 报告、按矿段取品位分级、汇总、生成成果表。"""

from .builder import MergeOptions, group_records, merge_reports
from .parser import BlockRecord, SourceReport, parse_report_file, parse_report_files
from .profiles import (GradeProfile, GradeRegistry, load_registry, resolve_profile)
from .schema import OUTPUT_COLUMNS

__all__ = [
    "MergeOptions", "group_records", "merge_reports",
    "BlockRecord", "SourceReport", "parse_report_file", "parse_report_files",
    "OUTPUT_COLUMNS",
    "GradeProfile", "GradeRegistry", "load_registry", "resolve_profile",
]
