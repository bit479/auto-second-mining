# -*- coding: utf-8 -*-
import os

out = []
root = r"E:\gzRJ\3Dmine\2022"
hits = []
for dirpath, dirnames, filenames in os.walk(root):
    # 跳过过大目录
    if "demo" in dirpath and "Python示例" not in dirpath:
        pass
    for f in filenames:
        low = f.lower()
        if low.endswith((".dvb", ".bas", ".vba", ".frm", ".cls")) or "macro" in low or "vba" in low:
            hits.append(os.path.join(dirpath, f))
out.append("=== VBA/macro files ===")
out.extend(hits[:40] if hits else ["(none)"])

# chm_extract 目录再看
d = r"E:\gzRJ\3Dmine\2022\common\help_chn\chm_extract"
out.append("\n=== chm_extract ===")
if os.path.isdir(d):
    out.extend(os.listdir(d)[:20] or ["(empty)"])
else:
    out.append("(not a dir)")

# 3dmine evaluation.chm 有没有相关帮助（826KB 小 chm 可尝试 hh）
open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\probe3.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
