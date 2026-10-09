# -*- coding: utf-8 -*-
import os
out = []
d = r"E:\gzRJ\3Dmine\2022\common\cui"
for dirpath, dirnames, filenames in os.walk(d):
    depth = dirpath[len(d):].count(os.sep)
    if depth > 1:
        continue
    rel = os.path.relpath(dirpath, d)
    out.append("[%s]" % rel)
    for sub in dirnames:
        out.append("   <dir> " + sub)
    for f in filenames:
        if f.endswith(".xml"):
            out.append("        " + f)
open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\cui_profiles.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
