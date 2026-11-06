# -*- coding: utf-8 -*-
"""多来源统一入口（T03.1，最小实现）。

目前支持：Excel（.xls/.xlsx，复用 readers）与 SQLite（.db/.sqlite/.sqlite3）。
不做 CSV 等其它来源，避免一次性引入大量未经验证的功能（本阶段约束）。

SQLite 约定（最小、显式）：数据库里存在表「定位表 / pit_blast / 测斜表」，
列名与 Excel 表头一致（可被 schemas 映射识别）。表名可另行指定，未匹配则报错提示。
"""
from __future__ import annotations

from pathlib import Path

from data import models
from data.readers import _parse_workbook, _read_workbook

_SQLITE_EXTS = (".db", ".sqlite", ".sqlite3")
_EXCEL_EXTS = (".xls", ".xlsx")

# SQLite 表名 → 类别（可扩展）
SQLITE_TABLES = {"定位表": "loc", "pit_blast": "blast", "测斜表": "survey"}


def _read_sqlite(path: Path) -> list:
    """读 SQLite，返回与 Excel 同构的 [(表名, rows)]（表头 = 第一行）。"""
    import sqlite3
    con = sqlite3.connect(str(path))
    try:
        cur = con.cursor()
        tables = [r[0] for r in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        out = []
        for t in tables:
            cols = [c[1] for c in cur.execute("PRAGMA table_info(%s)" % t).fetchall()]
            rows = [cols]  # 第一行放列名（当表头），与 Excel 约定一致
            rows += [list(r) for r in cur.execute("SELECT * FROM %s" % t).fetchall()]
            out.append((t, rows))
        return out
    finally:
        con.close()


def load(source, fmt: str | None = None, platform: str = "", date: str = "",
         schema=None) -> models.Dataset:
    """按来源分派读取，返回标准 Dataset。

    ``fmt`` 可显式指定 'excel' / 'sqlite'；省略时按扩展名判断。
    """
    path = Path(source)
    ds = models.Dataset(source=str(path))
    ds.meta = models.DatasetMeta(source_file=str(path), platform=platform or "", date=date or "")

    kind = (fmt or "").lower()
    if not kind:
        if path.suffix.lower() in _SQLITE_EXTS:
            kind = "sqlite"
        elif path.suffix.lower() in _EXCEL_EXTS:
            kind = "excel"
        else:
            ds.issues.append(models.Issue("unknown_source", models.SEV_ERROR,
                                          "无法识别的数据来源/扩展名：%s" % path.suffix,
                                          str(path), "支持 Excel(.xls/.xlsx) 与 SQLite(.db)"))
            return ds

    ds.meta.source = kind
    try:
        if kind == "sqlite":
            wb = _read_sqlite(path)
        else:
            wb = _read_workbook(path)
    except Exception as exc:  # noqa: BLE001
        ds.issues.append(models.Issue("open_failed", models.SEV_ERROR,
                                      "打不开数据源：%s" % exc, str(path)))
        return ds
    _parse_workbook(wb, ds, schema)
    return ds
