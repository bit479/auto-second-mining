# -*- coding: utf-8 -*-
import os
out = []
root = r"E:\gzRJ\3Dmine\2022\bin\nt_x64"
for f in sorted(os.listdir(root)):
    low = f.lower()
    if any(k in low for k in ("vba", "basic", "macro", "script", "api", "command", "module")):
        out.append("%s  (%d)" % (f, os.path.getsize(os.path.join(root, f)) if os.path.isfile(os.path.join(root, f)) else 0))
# 全部 dll 列表（找可疑的）
out.append("\n=== all dlls ===")
for f in sorted(os.listdir(root)):
    if f.lower().endswith(".dll"):
        out.append(f)
open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\bin_dlls.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
