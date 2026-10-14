# -*- coding: utf-8 -*-
import xlrd, pyodbc
f = r"D:/WK/N CRT/北部山头3940平台2026/1、北部山头3940平台 炮孔数据库-2026.xls"
bk = xlrd.open_workbook(f, formatting_info=True)
for sn in bk.sheet_names():
    sh = bk.sheet_by_name(sn)
    print("### sheet", sn, "nrows", sh.nrows)
    for i in range(max(0, sh.nrows-4), sh.nrows):
        print("   r%d:" % i, [(sh.cell(i,j).ctype, sh.cell(i,j).value) for j in range(sh.ncols)])
print("="*60)
m = r"D:/WK/N CRT/北部山头3940平台2026/2、北部山头3940平台炮孔数据库-2026.mdb"
cn = pyodbc.connect(r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=%s;" % m)
cur = cn.cursor()
for t in ['定位表','测斜表','pit_blast']:
    print("table", t)
    for r in cur.statistics(table=t):
        print("   ", r.index_name, "non_unique=", r.non_unique, "pos=", r.ordinal_position, "col=", r.column_name, "card=", r.cardinality)
cn.close()
