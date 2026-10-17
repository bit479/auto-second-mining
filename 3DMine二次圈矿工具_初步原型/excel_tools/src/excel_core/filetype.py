"""按文件**内容**判断 Excel 的真实格式（不看扩展名）。

踩过的坑：南部山头那套数据的扩展名与真实格式正好和北部山头相反 ——
`1、3970平台炮孔数据表.xlsx` 是真 xlsx（被当 xls 读，xlrd 报
``formatting_info=True not yet implemented``），
`3、…数据库矿块报告-2026年综合表.xls` 是真 BIFF（被当 xlsx 读，openpyxl 报
``does not support the old .xls file format``）。

所以这里一律看文件头：

* ``PK\\x03\\x04`` —— zip 容器，即 xlsx / xlsm
* ``D0 CF 11 E0 A1 B1 1A E1`` —— OLE 复合文档，即 xls / doc / mdb
"""

from __future__ import annotations

__all__ = ["FMT_XLS", "FMT_XLSX", "FMT_UNKNOWN", "sniff", "is_xlsx", "is_xls", "ext_of"]

FMT_XLSX = "xlsx"
FMT_XLS = "xls"
FMT_UNKNOWN = "unknown"

_ZIP_MAGIC = b"PK\x03\x04"
_OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


def sniff(path: str) -> str:
    """返回 ``"xlsx"`` / ``"xls"`` / ``"unknown"``。"""
    try:
        with open(path, "rb") as fh:
            head = fh.read(8)
    except OSError:
        return FMT_UNKNOWN
    if head[:4] == _ZIP_MAGIC:
        return FMT_XLSX
    if head[:8] == _OLE_MAGIC:
        return FMT_XLS
    return FMT_UNKNOWN


def is_xlsx(path: str) -> bool:
    return sniff(path) == FMT_XLSX


def is_xls(path: str) -> bool:
    return sniff(path) == FMT_XLS


def ext_of(path: str) -> str:
    """给人看的格式标签，如 ``"xlsx"``。"""
    fmt = sniff(path)
    return fmt if fmt != FMT_UNKNOWN else "未知格式"
