# -*- coding: utf-8 -*-
import os
out = []
d = r"E:\gzRJ\3Dmine\2022\common\help_chn"
for f in sorted(os.listdir(d)):
    p = os.path.join(d, f)
    if os.path.isfile(p):
        out.append("%s  %d" % (f, os.path.getsize(p)))
    else:
        out.append(f + "  <dir>")
open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\help_chn_list.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
