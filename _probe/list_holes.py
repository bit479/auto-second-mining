# -*- coding: utf-8 -*-
import xlrd, pyodbc
def xls_holes(f, sheet="定位表"):
    bk = xlrd.open_workbook(f); sh = bk.sheet_by_name(sheet)
    return [sh.row_values(i)[0] for i in range(1, sh.nrows)]
def mdb_holes(f, t="定位表"):
    cn = pyodbc.connect(r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=%s;" % f)
    cur = cn.cursor(); cur.execute("SELECT 工程号 FROM [%s]" % t)
    r = [row[0] for row in cur.fetchall()]; cn.close(); return r
def prefix(lst):
    # group by the BS-xxxx-xxxx part
    import re, collections
    c = collections.Counter()
    for h in lst:
        m = re.match(r"(BS-\d+-\d+)", str(h))
        c[m.group(1) if m else str(h)] += 1
    return dict(c), lst[0], lst[-1], len(lst)

pairs = [
 ("单日xls", r"D:/WK/N CRT/北部山头3940平台2026/7、单日数据/北部山头3940平台-1008/1、3940平台 炮孔数据库1008.xls"),
 ("总表xls", r"D:/WK/N CRT/北部山头3940平台2026/1、北部山头3940平台 炮孔数据库-2026.xls"),
]
for lab, f in pairs:
    print(lab, prefix(xls_holes(f)))
pairs2 = [
 ("单日mdb", r"D:/WK/N CRT/北部山头3940平台2026/7、单日数据/北部山头3940平台-1008/2、3940平台炮孔数据库1008.mdb"),
 ("总表mdb", r"D:/WK/N CRT/北部山头3940平台2026/2、北部山头3940平台炮孔数据库-2026.mdb"),
]
for lab, f in pairs2:
    print(lab, prefix(mdb_holes(f)))
