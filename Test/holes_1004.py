# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型")
sys.path.insert(0, r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\src")
from mdb_loader import load_xls_blast
import numpy as np

c = load_xls_blast(r"D:\WK\N CRT\北部山头3940平台2026\7、单日数据\北部山头3940平台-1004\1、3940平台 炮孔数据库1004.xls")
o = c[c["Grade"] >= 0.5]
print(f"{'hole':<18}{'grade':>7}{'X':>12}{'Y':>12}")
for _, r in o.sort_values("Grade", ascending=False).iterrows():
    print(f"{r['Hole_ID']:<18}{r['Grade']:>7.3f}{r['X']:>12.2f}{r['Y']:>12.2f}")
# 高品位簇（>=1.0）两两距离
hi = o[o["Grade"] >= 1.0].reset_index(drop=True)
print("\n== >=1.0 孔两两距离（m）==")
for i in range(len(hi)):
    row = []
    for j in range(i + 1, len(hi)):
        d = np.hypot(hi.loc[i, "X"] - hi.loc[j, "X"], hi.loc[i, "Y"] - hi.loc[j, "Y"])
        row.append(f"{hi.loc[j,'Hole_ID'].split('-')[-1]}:{d:.1f}")
    print(f"{hi.loc[i,'Hole_ID'].split('-')[-1]:>4}  " + "  ".join(row))
