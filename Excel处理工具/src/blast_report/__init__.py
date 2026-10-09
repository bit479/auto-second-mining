"""炮孔数据报告业务层：解析 3DMine 报告、按品位档汇总、生成成果表。"""

from .builder import MergeOptions, group_records, merge_reports
from .parser import BlockRecord, SourceReport, parse_report_file, parse_report_files
from .schema import OUTPUT_COLUMNS

__all__ = [
    "MergeOptions", "group_records", "merge_reports",
    "BlockRecord", "SourceReport", "parse_report_file", "parse_report_files",
    "OUTPUT_COLUMNS",
]
