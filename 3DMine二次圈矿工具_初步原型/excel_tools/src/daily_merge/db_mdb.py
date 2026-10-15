"""炮孔数据库 .mdb（Access）的并入。

通过 Microsoft Access ODBC 驱动直连，把单日库里总表还没有的孔追加到
``定位表 / 测斜表 / pit_blast`` 三张表的末尾；其余 3DMine 元数据表
（config / style / constraint）一律不碰。

注意：``pit_blast`` 在 Access 里带 (工程号, 从) 唯一索引，所以判重按这两列做。
"""

from __future__ import annotations

import os
from typing import Any

from .schema import DB_KEY_COLUMNS, DB_TABLES, DB_TEXT_COLUMNS, KINDS, normalize_key

__all__ = ["connect", "list_tables", "read_table_rows", "merge_mdb", "ODBC_DRIVER"]

ODBC_DRIVER = "Microsoft Access Driver (*.mdb, *.accdb)"


def connection_string(path: str, write: bool = True) -> str:
    cs = "DRIVER={%s};DBQ=%s;" % (ODBC_DRIVER, os.path.abspath(path))
    if not write:
        cs += "ReadOnly=1;"
    return cs


def connect(path: str, write: bool = True):
    """连接 mdb。失败时抛出带中文说明的 RuntimeError。"""
    import pyodbc

    if not os.path.isfile(path):
        raise FileNotFoundError("找不到数据库文件：%s" % path)
    try:
        conn = pyodbc.connect(connection_string(path, write), autocommit=False)
    except pyodbc.Error as exc:
        hint = ""
        if any(d.startswith(ODBC_DRIVER) for d in pyodbc.drivers()):
            hint = "（文件可能正被 3DMine / Access 占用，请关闭后重试）"
        else:
            hint = "（本机缺少 %s，请安装 Microsoft Access Database Engine）" % ODBC_DRIVER
        raise RuntimeError("打开数据库失败：%s%s\n%s" % (path, hint, exc)) from exc
    return conn


def list_tables(conn) -> list[str]:
    cur = conn.cursor()
    return [r.table_name for r in cur.tables(tableType="TABLE")]


def read_table_rows(conn, table: str, columns: list[str]) -> list[dict[str, Any]]:
    """按列名读出整张表（列名不存在时返回空列表）。"""
    available = {c.column_name for c in conn.cursor().columns(table=table)}
    cols = [c for c in columns if c in available]
    if not cols:
        return []
    sql = "SELECT %s FROM [%s]" % (", ".join("[%s]" % c for c in cols), table)
    cur = conn.cursor()
    cur.execute(sql)
    names = [d[0] for d in cur.description]
    return [dict(zip(names, row)) for row in cur.fetchall()]


def _insert_rows(conn, table: str, columns: list[str], rows: list[list[Any]]) -> int:
    if not rows:
        return 0
    sql = "INSERT INTO [%s] (%s) VALUES (%s)" % (
        table,
        ", ".join("[%s]" % c for c in columns),
        ", ".join("?" * len(columns)),
    )
    cur = conn.cursor()
    cur.fast_executemany = False          # Access 驱动不支持批量协议
    count = 0
    for values in rows:
        cleaned = []
        for col, value in zip(columns, values):
            if value is None:
                cleaned.append("")
            elif col in DB_TEXT_COLUMNS or isinstance(value, str):
                cleaned.append(str(value))
            else:
                try:
                    cleaned.append(float(value))
                except (TypeError, ValueError):
                    cleaned.append(str(value))
        cur.execute(sql, cleaned)
        count += cur.rowcount if cur.rowcount and cur.rowcount > 0 else 1
    return count or len(rows)


def merge_mdb(src_path: str, dst_path: str, *,
              skip_duplicates: bool = True,
              dry_run: bool = False) -> dict:
    """把 ``src_path`` 的炮孔数据并入 ``dst_path``（总表）。"""
    src_conn = connect(src_path, write=False)
    dst_conn = connect(dst_path, write=not dry_run)
    try:
        src_tables = set(list_tables(src_conn))
        dst_tables = set(list_tables(dst_conn))

        stats: dict[str, dict] = {}
        additions: dict[str, list[list]] = {}
        for table, columns in DB_TABLES.items():
            if table not in src_tables or table not in dst_tables:
                stats[table] = {"status": "skip", "reason": "单日或总表缺少该表",
                                "existing": 0, "source": 0, "added": 0,
                                "skipped": 0, "duplicates": []}
                continue

            src_rows = read_table_rows(src_conn, table, columns)
            dst_rows = read_table_rows(dst_conn, table, columns)

            keys = DB_KEY_COLUMNS[table]
            existing = {tuple(normalize_key(r.get(c)) for c in keys) for r in dst_rows}
            added, duplicates, seen = [], [], set()
            for row in src_rows:
                sig = tuple(normalize_key(row.get(c)) for c in keys)
                if skip_duplicates and (sig in existing or sig in seen):
                    duplicates.append(str(row.get(keys[0])))
                    continue
                seen.add(sig)
                added.append([row.get(c) for c in columns])

            additions[table] = added
            stats[table] = {"status": "ok", "reason": "",
                            "existing": len(dst_rows), "source": len(src_rows),
                            "added": len(added), "skipped": len(duplicates),
                            "duplicates": duplicates}

        total_added = sum(s["added"] for s in stats.values())
        if total_added and not dry_run:
            try:
                for table, rows in additions.items():
                    _insert_rows(dst_conn, table, DB_TABLES[table], rows)
                dst_conn.commit()
            except Exception:
                dst_conn.rollback()
                raise

        return {
            "kind": KINDS[1],
            "src": os.path.abspath(src_path),
            "dst": os.path.abspath(dst_path),
            "written": bool(total_added) and not dry_run,
            "added": total_added,
            "tables": stats,
            "sheets": [t for t in DB_TABLES if t in dst_tables],
        }
    finally:
        src_conn.close()
        dst_conn.close()
