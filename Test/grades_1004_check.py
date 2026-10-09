# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型")
sys.path.insert(0, r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\src")
from mdb_loader import load_xls_blast
c = load_xls_blast(r"D:\WK\N CRT\北部山头3940平台2026\7、单日数据\北部山头3940平台-1004\1、3940平台 炮孔数据库1004.xls")
o = c[c["Grade"] >= 0.5]
l1 = o[(o["Grade"] >= 0.5) & (o["Grade"] < 1.0)].sort_values("Grade", ascending=False)
print(f"L1 孔数={len(l1)}")
for _, r in l1.iterrows():
    print(f"  {r['Hole_ID']:<12s} X={r['X']:.2f} Y={r['Y']:.2f} 品位={r['Grade']:.4f}")
print(f"L1 简单平均 = {l1['Grade'].mean():.4f}")
print(f"全部矿孔(<1.0 含0.5-1)简单平均 = {o[o['Grade']<1.0]['Grade'].mean():.4f}")
print(f"废孔品位: {sorted(c[c['Grade']<0.5]['Grade'].tolist())}")
print(f"全部 31 孔平均(含废孔) = {c['Grade'].mean():.4f}")
