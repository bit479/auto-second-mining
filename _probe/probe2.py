# -*- coding: utf-8 -*-
import xlrd, pyodbc, collections
f = r"D:/WK/N CRT/北部山头3940平台2026/1、北部山头3940平台 炮孔数据库-2026.xls"
bk = xlrd.open_workbook(f, formatting_info=True)
for sn in bk.sheet_names():
    sh = bk.sheet_by_name(sn)
    print("sheet", sn, "nrows", sh.nrows, "ncols", sh.ncols)
    for ci in sorted(sh.colinfo_map):
        c = sh.colinfo_map[ci]
        print("   colinfo", ci, "width", c.width)
    tc = collections.Counter(sh.cell(i,j).ctype for i in range(sh.nrows) for j in range(sh.ncols))
    print("   ctype counts:", dict(tc))
    for i in range(min(2, sh.nrows)):
        for j in range(sh.ncols):
            cell = sh.cell(i, j)
            xf = bk.xf_list[cell.xf_index]; font = bk.font_list[xf.font_index]
            print("     (%d,%d) t=%d v=%r font=%r sz=%s bold=%s" % (i,j,cell.ctype,cell.value,font.name,font.height/20,font.bold))

print("="*60)
m = r"D:/WK/N CRT/北部山头3940平台2026/2、北部山头3940平台炮孔数据库-2026.mdb"
cn = pyodbc.connect(r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=%s;" % m)
cur = cn.cursor()
for t in ['定位表','测斜表','pit_blast']:
    rows = list(cur.statistics(table=t))
    print(t, "stat cols:", [d[0] for d in cur.description] if cur.description else None)
    for r in rows:
        print("   ", tuple(r)[:8])
cn.close()
