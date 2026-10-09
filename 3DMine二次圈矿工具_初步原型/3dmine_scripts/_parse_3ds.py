# -*- coding: utf-8 -*-
"""完整解析 .3ds 文件结构（3DMine 线文件格式）。"""
import re

P = r"C:\Users\Administrator\Desktop\选择集对象.3ds"
with open(P, "rb") as f:
    raw = f.read()
# 尝试 GBK/UTF-8 解码
for enc in ["gbk", "utf-8", "latin-1"]:
    try:
        txt = raw.decode(enc)
        print("decoded:", enc)
        break
    except Exception:
        continue
print("=== 全文（可打印） ===")
print(txt[:2000])
print("=== 结构解析 ===")
# 找所有顶点行
verts = re.findall(r"\.1,([-\d.]+),([-\d.]+),([-\d.]+),\.", txt)
print(f"顶点数: {len(verts)}")
for i, v in enumerate(verts[:25]):
    print(f"  v{i}: Y={v[0]} X={v[1]} Z={v[2]}")
# 非顶点部分
parts = re.split(r"\.1,[-\d.]+,[-\d.]+,[-\d.]+,\.", txt)
print("=== 段落（顶点之间） ===")
for i, p in enumerate(parts[:10]):
    print(f"  seg{i}: {p[:200]}")
