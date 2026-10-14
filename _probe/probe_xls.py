# -*- coding: utf-8 -*-
import xlrd, os, sys
files = [
 r"D:/WK/N CRT/北部山头3940平台2026/7、单日数据/北部山头3940平台-1008/1、3940平台 炮孔数据库1008.xls",
 r"D:/WK/N CRT/北部山头3940平台2026/1、北部山头3940平台 炮孔数据库-2026.xls",
]
for f in files:
    print("="*100)
    print("FILE:", f)
    try:
        bk = xlrd.open_workbook(f)
    except Exception as e:
        print("  ERR", e); continue
    print("  sheets:", bk.sheet_names())
    for sn in bk.sheet_names():
        sh = bk.sheet_by_name(sn)
        print("  --- sheet [%s] rows=%d cols=%d" % (sn, sh.nrows, sh.ncols))
        for i in range(min(sh.nrows, 30)):
            vals = sh.row_values(i)
            print("    r%02d|" % i, " | ".join(repr(v) for v in vals[:14]))
