# -*- coding: utf-8 -*-
import os
out = []
d = r"E:\gzRJ\3Dmine\2022\demo\专题示例\10_二次开发"
for dirpath, dirnames, filenames in os.walk(d):
    rel = os.path.relpath(dirpath, d)
    out.append("[%s]" % rel)
    for f in filenames:
        p = os.path.join(dirpath, f)
        out.append("   %s  (%d)" % (f, os.path.getsize(p)))
open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\dev_examples.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
