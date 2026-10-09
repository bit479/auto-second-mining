# -*- coding: utf-8 -*-
"""核对 1004 全部 31 孔的品位档位与归属，找出漏圈孔。"""
import json, os

d = json.load(open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\1004_blocks.json", encoding="utf-8"))
out = []
out.append("=== 3块版各块 ===")
for b in d["blocks"]:
    out.append("块#%s %s 孔数=%d 面积=%.1f m2 品位=%.3f 孔=%s" % (
        b["id"], b.get("grade_label", ""), len(b.get("holes", [])),
        b.get("area_m2", 0), b.get("avg_grade_g_t", 0),
        [h.get("hole_id", "") for h in b.get("holes", [])]))

# 源数据（炮孔品位）——从生成脚本读
import sys
sys.path.insert(0, r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro")
# 直接解析 xls 源
import xlrd
wb = xlrd.open_workbook(r"D:\WK\N CRT\北部山头3940平台2026\7、单日数据\北部山头3940平台-1004\1、3940平台 炮孔数据库1004.xls", formatting_info=False)
out.append("\n=== 源数据 sheet ===")
for sh in wb.sheets():
    out.append("sheet=%s rows=%d cols=%d" % (sh.name, sh.nrows, sh.ncols))
# 品位表 pit_blast
for sh in wb.sheets():
    if "blast" in sh.name.lower():
        out.append("\n=== %s 全部行 ===" % sh.name)
        hdr = [str(sh.cell_value(0, c)).strip() for c in range(sh.ncols)]
        out.append("HDR: " + " | ".join(hdr))
        for r in range(1, sh.nrows):
            vals = [str(sh.cell_value(r, c)).strip() for c in range(sh.ncols)]
            out.append(" | ".join(vals))
        # 品位列定位
        gi = None
        for c, h in enumerate(hdr):
            if "品位" in h or "grade" in h.lower() or "au" in h.lower():
                gi = c
                break
        if gi is not None:
            out.append("\n品位列=%s" % hdr[gi])

open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\hole_audit.txt", "w", encoding="utf-8").write("\n".join(out))
print("done")
