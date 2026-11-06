# -*- coding: utf-8 -*-
"""炮孔数据库读取适配器（T01 / T03.1）。

用**表头识别 + 字段映射**读「定位表 / pit_blast / 测斜表」，不再假设列位固定。
只读、不改源文件。返回 `Dataset`（原始记录 + 元数据 + 读取阶段异常）。

字段映射来自 `data.schemas`（可配置，精确匹配，不模糊猜测）。多来源分派见
`data.adapters.load()`；本模块的 `read_holes()` 保持 Excel 入口的向后兼容。
"""
from __future__ import annotations

import math
from pathlib import Path

from data import models, schemas


# ---------------------------------------------------------------------------
# 单元格数值解析
# ---------------------------------------------------------------------------
def _to_float(v) -> float | None:
    """把单元格值转 float；空/非数值/NaN/±Inf 一律返回 None（T02.1 修复）。

    原实现只挡「空串/非数值」，`float('nan')`/`float('inf')` 会漏过去；
    这里显式拦截 NaN 与正负无穷，避免被当成有效数值进入缺失/异常判定。
    """
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, str) and not v.strip():
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def _read_workbook(path: Path):
    """读 Excel，返回 [(工作表名, [[cell,...], ...])]，兼容 .xls（xlrd）与 .xlsx（openpyxl）。"""
    suffix = path.suffix.lower()
    if suffix == ".xlsx":
        import openpyxl
        wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
        out = []
        for ws in wb.worksheets:
            out.append((ws.title, [[c for c in row] for row in ws.iter_rows(values_only=True)]))
        wb.close()
        return out
    import xlrd
    wb = xlrd.open_workbook(str(path))
    out = []
    for ws in wb.sheets():
        out.append((ws.name, [[ws.cell_value(r, c) for c in range(ws.ncols)]
                              for r in range(ws.nrows)]))
    return out


# ---------------------------------------------------------------------------
# 表头定位与解析
# ---------------------------------------------------------------------------
def _find_sheet(workbook, names: tuple) -> int | None:
    for i, (sn, _) in enumerate(workbook):
        if schemas._norm(sn) in {schemas._norm(x) for x in names}:
            return i
    return None


def _header_row(rows, kind, schema, ds, sheet_name):
    """在 rows 前 5 行找表头，返回 (行索引, {字段:列索引})。找不到记 header_not_found。"""
    for r, row in enumerate(rows[:5]):
        mapping, unmatched = schemas.resolve_mapping(row, kind, schema)
        if len(mapping) >= 2:
            for name in unmatched:
                ds.issues.append(models.Issue(
                    "unmapped_column", models.SEV_INFO,
                    "列头「%s」未识别，该列已跳过（不会静默当作某字段）" % name,
                    "%s/列「%s」" % (sheet_name, name),
                    "如需使用请在 schemas 里注册该列头"))
            ds.field_map[sheet_name] = mapping
            return r, mapping
    ds.issues.append(models.Issue("header_not_found", models.SEV_ERROR,
                                  "「%s」里没找到表头" % sheet_name, sheet_name))
    return -1, {}


def _is_blank(row) -> bool:
    return not row or all(c is None or str(c).strip() == "" for c in row)


def _raw_of(row, header_texts) -> dict:
    """把一整行按原始列头存成 {列头: 原始值}，供追溯。"""
    out = {}
    for i, v in enumerate(row):
        name = header_texts[i] if i < len(header_texts) and str(header_texts[i]).strip() else ("列%d" % (i + 1))
        out[str(name).strip()] = v
    return out


def _read_loc(rows, sheet_name, ds, schema) -> list:
    hdr_row, mapping = _header_row(rows, "loc", schema, ds, sheet_name)
    if hdr_row < 0:
        return []
    header_texts = rows[hdr_row]
    recs = []
    for idx in range(hdr_row + 1, len(rows)):
        row = rows[idx]
        if _is_blank(row):
            continue
        get = lambda f: row[mapping[f]] if f in mapping and mapping[f] < len(row) else None  # noqa: E731
        hid = str(get("hid") or "").strip()
        if not hid:
            ds.issues.append(models.Issue("empty_hid", models.SEV_ERROR,
                                          "定位表这一行没有工程号", "%s/行%d" % (sheet_name, idx + 1)))
            continue
        x, y, z = _to_float(get("x")), _to_float(get("y")), _to_float(get("z"))
        depth = _to_float(get("depth"))
        for fld, val in (("x", x), ("y", y), ("z", z), ("depth", depth)):
            if val is None:
                ds.issues.append(models.Issue("non_numeric", models.SEV_ERROR,
                                              "定位表「%s」这一列不是数字" % fld,
                                              "%s/行%d/%s" % (sheet_name, idx + 1, hid)))
        trajectory = str(get("trajectory") or "").strip()
        recs.append(models.HoleRecord(
            hid=hid, x=x, y=y, z=z, depth=depth, row=idx + 1,
            raw=_raw_of(row, header_texts), trajectory=trajectory, sheet=sheet_name))
    return recs


def _read_blast(rows, sheet_name, ds, schema) -> list:
    hdr_row, mapping = _header_row(rows, "blast", schema, ds, sheet_name)
    if hdr_row < 0:
        return []
    header_texts = rows[hdr_row]
    ints = []
    for idx in range(hdr_row + 1, len(rows)):
        row = rows[idx]
        if _is_blank(row):
            continue
        get = lambda f: row[mapping[f]] if f in mapping and mapping[f] < len(row) else None  # noqa: E731
        hid = str(get("hid") or "").strip()
        if not hid:
            ds.issues.append(models.Issue("empty_hid", models.SEV_WARNING,
                                          "pit_blast 这一行没有工程号", "%s/行%d" % (sheet_name, idx + 1)))
            continue
        gv = get("grade")
        ints.append(models.SampleInterval(
            hid=hid, frm=_to_float(get("frm")), to=_to_float(get("to")),
            grade=_to_float(gv), grade_raw=gv, row=idx + 1, sheet=sheet_name,
            raw=_raw_of(row, header_texts)))
    return ints


def _read_survey(rows, sheet_name, ds, schema) -> list:
    hdr_row, mapping = _header_row(rows, "survey", schema, ds, sheet_name)
    if hdr_row < 0:
        return []
    header_texts = rows[hdr_row]
    out = []
    for idx in range(hdr_row + 1, len(rows)):
        row = rows[idx]
        if _is_blank(row):
            continue
        get = lambda f: row[mapping[f]] if f in mapping and mapping[f] < len(row) else None  # noqa: E731
        hid = str(get("hid") or "").strip()
        if not hid:
            continue
        out.append(models.SurveyRow(
            hid=hid, depth=_to_float(get("depth")), azimuth=_to_float(get("azimuth")),
            dip=_to_float(get("dip")), row=idx + 1, sheet=sheet_name,
            raw=_raw_of(row, header_texts)))
    return out


def _parse_workbook(workbook, ds, schema=None) -> None:
    """把已载入的 [(表名, rows)] 解析进 ds（定位表/pit_blast/测斜表）。"""
    i_loc = _find_sheet(workbook, schemas.SHEET_KINDS["loc"])
    i_blast = _find_sheet(workbook, schemas.SHEET_KINDS["blast"])
    i_survey = _find_sheet(workbook, schemas.SHEET_KINDS["survey"])

    if i_loc is None:
        ds.issues.append(models.Issue("sheet_missing", models.SEV_ERROR,
                                      "缺少工作表「定位表」", ds.source,
                                      "需要：定位表（工程号/开孔坐标E/N/R/最大孔深）"))
    else:
        name = workbook[i_loc][0]
        ds.sheets[name] = "定位表"
        ds.loc_rows = _read_loc(workbook[i_loc][1], name, ds, schema)

    if i_blast is None:
        ds.issues.append(models.Issue("sheet_missing", models.SEV_ERROR,
                                      "缺少工作表「pit_blast」", ds.source,
                                      "需要：pit_blast（工程号/从/至/Au）"))
    else:
        name = workbook[i_blast][0]
        ds.sheets[name] = "pit_blast"
        ds.intervals = _read_blast(workbook[i_blast][1], name, ds, schema)

    if i_survey is not None:
        name = workbook[i_survey][0]
        ds.sheets[name] = "测斜表"
        ds.survey_rows = _read_survey(workbook[i_survey][1], name, ds, schema)


def read_holes(path, platform: str = "", date: str = "", schema=None) -> models.Dataset:
    """读一个 Excel 炮孔数据库，返回 Dataset（向后兼容入口）。"""
    path = Path(path)
    ds = models.Dataset(source=str(path))
    ds.meta = models.DatasetMeta(source="excel", source_file=str(path),
                                 platform=platform or "", date=date or "")
    try:
        wb = _read_workbook(path)
    except Exception as exc:  # noqa: BLE001
        ds.issues.append(models.Issue("open_failed", models.SEV_ERROR,
                                      "打不开数据库：%s" % exc, str(path)))
        return ds
    _parse_workbook(wb, ds, schema)
    return ds


def to_legacy_holes(ds: models.Dataset, grade_rule: str = "last"):
    """把 Dataset 转成现有 `oreblocks.Hole` 的 dict（算量链路兼容用）。

    ``grade_rule`` 决定多段化验如何取品位：last/first/max/min/length_weighted/simple_avg。
    默认 ``last`` **仅作为旧生产行为的兼容选项**，不代表已获矿山批准；多段化验的
    正式汇总规则待地质负责人确认（A 类事项），确认前不应把本函数接进生产。
    """
    from quality import aggregate
    loc = ds.loc_by_hid()
    ints = ds.intervals_by_hid()
    out = {}
    for hid, h in loc.items():
        grade = aggregate.aggregate_grade(ints.get(hid, []), grade_rule)
        out[hid] = _LegacyHole(hid=hid, x=h.x, y=h.y, z=h.z, depth=h.depth, grade=grade)
    return out


class _LegacyHole:
    """占位：结构与 `oreblocks.Hole` 对齐（hid/x/y/z/depth/grade）。"""

    def __init__(self, hid, x, y, z, depth, grade):
        self.hid = hid
        self.x = x
        self.y = y
        self.z = z
        self.depth = depth if depth is not None else 0.0
        self.grade = grade if grade is not None else 0.0
        self.short = hid.split("-")[-1] if hid else ""
