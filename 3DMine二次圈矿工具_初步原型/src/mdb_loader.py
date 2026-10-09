# -*- coding: utf-8 -*-
"""
mdb_loader / xls_loader：读取 3DMine 炮孔数据库（Access .mdb 或 Excel .xls）
---------------------------------------------------------------------------
对应人工流程"把 Excel 炮孔数据库导入 3DMine 支持的 mdb 数据库格式"。
两种数据源共用同一张三表结构：

  定位表 ：工程号 | 开孔坐标E(X) | 开孔坐标N(Y) | 开孔坐标R(Z) | 轨迹类型 | 最大孔深
  测斜表 ：工程号 | 深度 | 方位角 | 倾角          （直孔：方位角 0、倾角 -90）
  pit_blast：工程号 | 从 | 至 | Au             （整孔品位段，每孔 1 条）

返回与 CSV 同结构的炮孔品位 DataFrame（Hole_ID/X/Y/Z/Depth_m/Grade/Bench_ID/
Platform_ID/Date），可直接接入 prepare_hole_points 之后的圈矿流程。
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def build_composite(loc: pd.DataFrame, sur: pd.DataFrame, bl: pd.DataFrame) -> pd.DataFrame:
    """三表 JOIN 成每孔一行台阶品位点（mdb / xls 共用）。"""
    loc = loc.rename(columns={"工程号": "Hole_ID", "开孔坐标E": "X", "开孔坐标N": "Y",
                              "开孔坐标R": "Z", "最大孔深": "Depth_m"})
    sur = sur.rename(columns={"工程号": "Hole_ID", "深度": "Depth_sur"})
    bl = bl.rename(columns={"工程号": "Hole_ID", "从": "From_m", "至": "To_m", "Au": "Au_g_t"})

    for df in (loc, sur, bl):
        df["Hole_ID"] = df["Hole_ID"].astype(str).str.strip()

    comp = loc.merge(sur, on="Hole_ID", how="left").merge(bl, on="Hole_ID", how="left")
    comp["Depth_m"] = comp["Depth_m"].fillna(comp["Depth_sur"]).fillna(comp["To_m"])
    comp["Grade"] = comp["Au_g_t"].astype(float)
    comp["Bench_ID"] = ""

    # 解析工程号前缀：BS-3940-0915 / BSS-3940-0922-P* / BL-3940-0922-BL* → 平台/日期取第 2、3 段
    def parse_prefix(hid: str):
        parts = hid.split("-")
        if len(parts) >= 3:
            return parts[1], parts[2]
        return "", ""

    pref = comp["Hole_ID"].apply(parse_prefix)
    comp["Platform_ID"] = [p[0] for p in pref]
    comp["Date"] = [p[1] for p in pref]

    comp = comp.dropna(subset=["X", "Y", "Grade"]).reset_index(drop=True)
    return comp


def load_mdb_blast(mdb_path: str | Path) -> pd.DataFrame:
    """读 mdb 三表并 JOIN。直孔按孔口坐标处理（测斜倾角 -90°，平面 X/Y 不变）。"""
    import pyodbc

    mdb_path = Path(mdb_path)
    drivers = [d for d in pyodbc.drivers() if "Access" in d]
    if not drivers:
        raise RuntimeError("未找到 Microsoft Access 驱动（Microsoft Access Driver (*.mdb)），无法读取 mdb。")
    conn_str = r"DRIVER={%s};DBQ=%s;PWD=" % (drivers[0], mdb_path)
    conn = pyodbc.connect(conn_str)
    cur = conn.cursor()

    def table_name(alias: str) -> str:
        names = [r.table_name for r in cur.tables() if r.table_type == "TABLE"]
        if alias in names:
            return alias
        raise RuntimeError(f"mdb 中缺少表 {alias}，实际表：{names}")

    # 用 SELECT * 读取（pyodbc 对 SQL 中中文列名解析不稳定），列名从游标描述取
    # pandas 3.0 无法直接消费 pyodbc.Row，先转 tuple
    def read_table(tname: str) -> pd.DataFrame:
        cur.execute(f'SELECT * FROM "{tname}"')
        cols = [d[0] for d in cur.description]
        return pd.DataFrame([tuple(r) for r in cur.fetchall()], columns=cols)

    loc = read_table(table_name("定位表"))
    sur = read_table(table_name("测斜表"))
    bl = read_table(table_name("pit_blast"))
    conn.close()
    return build_composite(loc, sur, bl)


def load_xls_blast(xls_path: str | Path) -> pd.DataFrame:
    """读 Excel .xls（xlrd）三表并 JOIN（与 mdb 三表同构）。"""
    import xlrd

    xls_path = Path(xls_path)
    wb = xlrd.open_workbook(str(xls_path))

    def read_sheet(name: str) -> pd.DataFrame:
        if name not in wb.sheet_names():
            raise RuntimeError(f"xls 中缺少 sheet {name}，实际：{wb.sheet_names()}")
        sh = wb.sheet_by_name(name)
        cols = [str(sh.cell_value(0, c)) for c in range(sh.ncols)]
        rows = [[sh.cell_value(r, c) for c in range(sh.ncols)] for r in range(1, sh.nrows)]
        return pd.DataFrame(rows, columns=cols)

    loc = read_sheet("定位表")
    sur = read_sheet("测斜表")
    bl = read_sheet("pit_blast")
    return build_composite(loc, sur, bl)


__all__ = ["load_mdb_blast", "load_xls_blast", "build_composite"]
