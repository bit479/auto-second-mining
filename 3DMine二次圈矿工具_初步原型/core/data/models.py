# -*- coding: utf-8 -*-
"""统一数据对象（T01 / T03.1）。

本模块只定义**数据表示**，不包含任何算量公式（面积/体积/品位/金属量仍在
`oreblocks` 与 `strip` 里，本阶段不改动）。目标：把「定位表 / pit_blast / 测斜表」
的原始记录映射成可校验、可追溯、可标准化的结构，供 `quality/check.py` 做质量检查。

与现有 `oreblocks.Hole` 的关系：`oreblocks.Hole` 是**算量用**的精简结构
（hid/x/y/z/depth/grade），本模块的 `HoleRecord` 是**读入用**的完整结构
（含行号、原始值、多段化验、来源追溯），两者并存、互不替代。

T03.1 新增：`DatasetMeta`（数据元数据）、`UNKNOWN`（未知值约定）、
记录级 `sheet`（来源工作表）与 `raw`（原始字段/值）追溯。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# 未知值约定：凡无法确定的值一律用 "UNKNOWN"，不允许静默猜测。
UNKNOWN = "UNKNOWN"


# ---------------------------------------------------------------------------
# 异常级别
# ---------------------------------------------------------------------------
SEV_ERROR = "error"      # 阻断：会导致圈矿/算量错误或数据被静默覆盖
SEV_WARNING = "warning"  # 警告：需要人工确认/待定口径
SEV_INFO = "info"        # 提示


@dataclass
class Issue:
    """一条质量异常。``where`` 统一写成「文件/工作表/行/工程号」便于定位。"""

    code: str            # 稳定错误码，如 dup_hid / missing_grade / multi_interval
    severity: str        # error / warning / info
    message: str         # 人类可读描述
    where: str = ""      # 定位信息
    hint: str = ""       # 建议 / 待确认事项

    def as_line(self) -> str:
        tag = {"error": "阻断", "warning": "警告", "info": "提示"}.get(self.severity, self.severity)
        line = "[%s][%s] %s" % (tag, self.code, self.message)
        if self.where:
            line += "  @ %s" % self.where
        if self.hint:
            line += "  （%s）" % self.hint
        return line


# ---------------------------------------------------------------------------
# 数据元数据（T03.1）
# ---------------------------------------------------------------------------
@dataclass
class DatasetMeta:
    """一次数据集读取的元数据。未知项一律 `UNKNOWN`，不静默猜测。

    - ``coord_sys`` 坐标系标识（如 CGCS2000/3°带…），未知 = UNKNOWN；
    - ``coord_unit`` / ``elev_unit`` / ``depth_unit`` 长度单位，未知 = UNKNOWN；
    - ``grade_unit`` Au 品位单位，未知 = UNKNOWN（不默认认定 g/t）；
    - ``source`` 来源类型：excel / sqlite / csv / unknown；
    - ``source_file`` 原始文件/数据库路径；
    - ``platform`` / ``date`` 数据集所属平台与炮区日期（读入时可能未知，可后补）；
    - ``mapping_name`` 本次使用的字段映射配置名；
    - ``unit_rules`` 实际应用的单位换算规则列表（本阶段为空 = 未换算）。
    """

    source: str = "unknown"
    source_file: str = ""
    coord_sys: str = UNKNOWN
    coord_unit: str = UNKNOWN
    elev_unit: str = UNKNOWN
    depth_unit: str = UNKNOWN
    grade_unit: str = UNKNOWN
    platform: str = ""
    date: str = ""
    mapping_name: str = "default"
    unit_rules: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# 数据对象
# ---------------------------------------------------------------------------
@dataclass
class SampleInterval:
    """pit_blast 里的一段化验（同一工程号可有多段 = 多行）。

    ``raw`` 保留原始「从/至/Au」三列值，``grade_raw`` 为兼容 T01 保留的别名。
    """

    hid: str
    frm: float | None        # 从
    to: float | None         # 至
    grade: float | None      # Au；None 表示该记录没有有效品位（缺失）
    grade_raw: Any = None    # 原始 Au 值（用于追溯，可能是空串/非数值）
    row: int = 0             # pit_blast 里的行号（1 起）
    sheet: str = ""          # 来源工作表/表名
    raw: dict = field(default_factory=dict)   # 原始字段 → 原始值（从/至/Au）


@dataclass
class HoleRecord:
    """定位表里的一条炮孔记录（保留原始值与行号，便于追溯）。"""

    hid: str
    x: float | None
    y: float | None
    z: float | None
    depth: float | None
    row: int = 0             # 定位表里的行号（1 起）
    raw: dict = field(default_factory=dict)      # 原始值 {列名: 值}
    intervals: list = field(default_factory=list)  # list[SampleInterval]
    trajectory: str = ""     # 轨迹类型（直线/曲线…，未知为空）
    sheet: str = ""          # 来源工作表/表名


@dataclass
class SurveyRow:
    """测斜表一行（孔深/方位角/倾角），用于与定位表孔深交叉核对。"""

    hid: str
    depth: float | None
    azimuth: float | None
    dip: float | None
    row: int = 0
    sheet: str = ""
    raw: dict = field(default_factory=dict)


@dataclass
class BenchBlast:
    """台阶 / 炮区元数据（平台号 + 炮区日期）。"""

    platform: str = ""
    date: str = ""
    note: str = ""


@dataclass
class GeologyFeature:
    """地质要素（阶段 D 用，目前占位，不参与圈矿）。"""

    kind: str = ""           # 界线 / 岩性 / 断层 / 蚀变
    geometry: Any = None     # 坐标几何（后续阶段定义）
    attrs: dict = field(default_factory=dict)


@dataclass
class Dataset:
    """一次读取的结果：全部原始记录 + 元数据 + 读取阶段的异常。"""

    source: str = ""                                  # 文件路径（兼容 T01）
    meta: DatasetMeta = field(default_factory=DatasetMeta)
    sheets: dict = field(default_factory=dict)        # {工作表名: 类型(定位表/pit_blast/测斜表)}
    field_map: dict = field(default_factory=dict)     # 追溯用：{工作表名: {字段: 列索引}}
    loc_rows: list = field(default_factory=list)      # list[HoleRecord]
    intervals: list = field(default_factory=list)     # list[SampleInterval]
    survey_rows: list = field(default_factory=list)   # list[SurveyRow]
    issues: list = field(default_factory=list)        # list[Issue]（读取阶段）

    # ---- 便捷视图 ----

    def loc_by_hid(self) -> dict:
        """工程号 → 定位表记录（重复工程号时保留第一条，重复由 quality.check 报出）。"""
        out = {}
        for h in self.loc_rows:
            if h.hid and h.hid not in out:
                out[h.hid] = h
        return out

    def intervals_by_hid(self) -> dict:
        """工程号 → 化验段列表。"""
        out: dict = {}
        for s in self.intervals:
            out.setdefault(s.hid, []).append(s)
        return out
