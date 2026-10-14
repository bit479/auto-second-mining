# -*- coding: utf-8 -*-
import sys, os, xlrd, pyodbc
sys.stdout.reconfigure(encoding='utf-8')
SB = r"D:/WK/N CRT/_probe/sandbox/北部山头3940平台2026"
DAY = os.path.join(SB, r"7、单日数据\北部山头3940平台-1008")

print("########## 1) xls 校验 ##########")
src = os.path.join(DAY, "1、3940平台 炮孔数据库1008.xls")
dst = os.path.join(SB, "1、北部山头3940平台 炮孔数据库-2026.xls")
sb = xlrd.open_workbook(dst, formatting_info=True)
print("sheets:", sb.sheet_names())
sd = xlrd.open_workbook(src)
for t in ["定位表","测斜表","pit_blast"]:
    a, b = sd.sheet_by_name(t), sb.sheet_by_name(t)
    print(" --", t, "单日", a.nrows, "x", a.ncols, "| 总表", b.nrows, "x", b.ncols)
    # compare appended rows: single-day rows 1..50  <-> master rows 71..120
    bad = 0
    for i in range(1, a.nrows):
        for j in range(a.ncols):
            va, vb = a.cell_value(i,j), b.cell_value(70+i, j)
            if isinstance(va, float):
                if abs(va-vb) > 1e-9: bad += 1; print("    DIFF", (i,j), repr(va), repr(vb))
            elif str(va) != str(vb):
                bad += 1; print("    DIFF", (i,j), repr(va), repr(vb))
    print("    追加行比对差异:", bad)
    print("    列宽:", {k: v.width for k,v in b.colinfo_map.items()})
    # style of last appended row vs original last row
    sh_t = sb.sheet_by_name(t)
    c_old = sh_t.cell(70, 0); c_new = sh_t.cell(120, 0)
    fo = sb.font_list[sb.xf_list[c_old.xf_index].font_index]
    fn = sb.font_list[sb.xf_list[c_new.xf_index].font_index]
    print("    末行样式 旧=%s/%s 新=%s/%s" % (fo.name, fo.height/20, fn.name, fn.height/20))

print("########## 2) mdb 校验 ##########")
srcm = os.path.join(DAY, "2、3940平台炮孔数据库1008.mdb")
dstm = os.path.join(SB, "2、北部山头3940平台炮孔数据库-2026.mdb")
def rows(p, t):
    cn = pyodbc.connect(r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=%s;ReadOnly=1;" % p)
    cur = cn.cursor(); cur.execute("SELECT * FROM [%s]" % t); 
    r = cur.fetchall(); cn.close(); return r
for t in ["定位表","测斜表","pit_blast"]:
    a, b = rows(srcm, t), rows(dstm, t)
    print(" --", t, "单日", len(a), "总表", len(b))
    bad = 0
    for i in range(len(a)):
        ra, rb = a[i], b[70+i]
        for x, y in zip(ra, rb):
            if isinstance(x, float):
                if abs(x-y) > 1e-9: bad += 1; print("    DIFF", (i,), repr(x), repr(y))
            elif str(x) != str(y):
                bad += 1; print("    DIFF", (i,), repr(x), repr(y))
    print("    追加行比对差异:", bad)
    print("    前3/后3:", str(tuple(b[0]))[:60], "...", str(tuple(b[-1]))[:60])

print("########## 3) 报告校验 ##########")
from openpyxl import load_workbook
p = os.path.join(SB, "3、北部山头3940平台炮孔数据报告-2026综合.xlsx")
wb = load_workbook(p, data_only=False); ws = wb.active
print("dims", ws.dimensions, "merged", [str(m) for m in ws.merged_cells.ranges])
for i, row in enumerate(ws.iter_rows(values_only=True), start=1):
    print("  r%02d|" % i, " | ".join(repr(v) for v in row))
# styles of new block
for (r,c) in [(23,1),(24,1),(27,3),(30,1)]:
    cell = ws.cell(r,c)
    print("  style %s%d: font=%s/%s bold=%s numfmt=%r border=%s align=%s" % (
        chr(64+c), r, cell.font.name, cell.font.size, cell.font.bold, cell.number_format,
        cell.border.left.style, cell.alignment.horizontal))
wb.close()
