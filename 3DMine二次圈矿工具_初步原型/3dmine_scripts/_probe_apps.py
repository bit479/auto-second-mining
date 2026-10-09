# -*- coding: utf-8 -*-
import os, re

out = []
# 1) pit_optmize 目录
d = r"E:\gzRJ\3Dmine\2022\common\help_chn\pit_optmize"
if os.path.isdir(d):
    out.append("=== pit_optmize ===")
    for f in os.listdir(d):
        out.append("  " + f)

# 2) menu 里 AppLoad/应用/插件
p = r"E:\gzRJ\3Dmine\2022\common\cui\3dmine_profile_chinese\00_标准界面\menu_default.xml"
s = open(p, encoding="utf-8").read()
out.append("\n=== AppLoad/应用 in menu ===")
for kw in ["AppLoad", "AppServerM0::App", "应用", "插件"]:
    idxs = [m.start() for m in re.finditer(kw, s)]
    out.append("kw=%s hits=%d" % (kw, len(idxs)))
    for i in idxs[:5]:
        seg = s[max(0, i - 120):i + 120].replace("\n", " ")
        out.append("   ..." + seg[:200])

# 3) 尝试 7z 是否存在
out.append("\n=== 7z ===")
for c in [r"C:\Program Files\7-Zip\7z.exe", r"C:\Program Files (x86)\7-Zip\7z.exe"]:
    out.append("%s -> %s" % (c, os.path.exists(c)))

open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\probe2.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
