# -*- coding: utf-8 -*-
import xlrd
from xlutils.copy import copy as xlcopy
f = r"D:/WK/N CRT/北部山头3940平台2026/1、北部山头3940平台 炮孔数据库-2026.xls"
rb = xlrd.open_workbook(f, formatting_info=True)
sh = rb.sheet_by_name('定位表')
for (i,j) in [(0,0),(1,0),(1,1),(1,5),(2,3)]:
    xf = rb.xf_list[sh.cell(i,j).xf_index]
    print((i,j), "format_key=", xf.format_key, "fmt=", rb.format_map.get(xf.format_key))
wb = xlcopy(rb)
out = r"D:/WK/N CRT/_probe/roundtrip.xls"
wb.save(out)
print("saved", out)
rb2 = xlrd.open_workbook(out, formatting_info=True)
print("sheets:", rb2.sheet_names())
for sn in rb2.sheet_names():
    a = rb.sheet_by_name(sn); b = rb2.sheet_by_name(sn)
    print(sn, "orig", a.nrows, a.ncols, "→ new", b.nrows, b.ncols)
    diff = 0
    for i in range(a.nrows):
        for j in range(a.ncols):
            va, vb = a.cell(i,j).value, b.cell(i,j).value
            if va != vb:
                diff += 1
                if diff < 6: print("   DIFF", (i,j), repr(va), repr(vb))
    print("   diffs:", diff)
    # widths
    print("   widths orig:", {k: v.width for k,v in a.colinfo_map.items()})
    print("   widths new :", {k: v.width for k,v in b.colinfo_map.items()})
