# -*- coding: utf-8 -*-
import olefile

p = r"E:\gzRJ\3Dmine\2022\demo\专题示例\10_二次开发\VBA示例\创建点.vbm"
ole = olefile.OleFileIO(p)
data = ole.openstream("apc/The VBA Project/_VBA_Project/VBA/ThisDrawing").read()
ole.close()
print("size", len(data))
print("head bytes:", data[:40].hex(" "))
# 找 01 00 00
for i in range(min(40, len(data))):
    if data[i:i+3] == b"\x01\x00\x00":
        print("header at", i)
# 全字节分析：非零分布
import collections
c = collections.Counter(data)
print("nonzero count:", sum(1 for b in data if b))
