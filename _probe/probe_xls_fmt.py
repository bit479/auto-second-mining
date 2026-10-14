# -*- coding: utf-8 -*-
import xlrd
f = r"D:/WK/N CRT/北部山头3940平台2026/1、北部山头3940平台 炮孔数据库-2026.xls"
bk = xlrd.open_workbook(f, formatting_info=True)
for sn in bk.sheet_names():
    sh = bk.sheet_by_name(sn)
    print("sheet", sn, "nrows", sh.nrows, "ncols", sh.ncols)
    print("  colinfo:", [(c.first_col, c.last_col, c.width) for c in sh.colinfo_map.values()])
    for i in range(min(3, sh.nrows)):
        for j in range(sh.ncols):
            cell = sh.cell(i, j)
            xf = bk.xf_list[cell.xf_index]
            font = bk.font_list[xf.font_index]
            print("   (%d,%d) type=%d val=%r font=%r size=%s bold=%s" % (i, j, cell.ctype, cell.value, font.name, font.height/20, font.bold))
    # data types in whole sheet
    import collections
    tc = collections.Counter(sh.cell(i,j).ctype for i in range(sh.nrows) for j in range(sh.ncols))
    print("  ctype counts:", dict(tc))
