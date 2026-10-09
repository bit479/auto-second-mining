# -*- coding: utf-8 -*-
import re
p = r"E:\gzRJ\3Dmine\2023\3DMine V202310\3DMine V202310\common\cui\3dmine_profile_chinese\00_标准界面\menu_default.xml"
s = open(p, encoding="utf-8", errors="replace").read()
i = s.find('name="采矿设计"')
out = []
if i >= 0:
    gi = s.rfind("<menu_group", 0, i)
    ge = s.find("</menu_group>", gi) + len("</menu_group>")
    out.append(s[gi:ge])
else:
    out.append("采矿设计 NOT FOUND")
# 矿房设计
out.append("\n矿房设计出现次数: %d" % s.count("矿房设计"))
i2 = s.find('name="矿房设计"')
if i2 >= 0:
    out.append("矿房设计上下文: " + re.sub(r"\s+", " ", s[i2-200:i2+300]))
open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\stope_group.txt", "w", encoding="utf-8").write("\n".join(out))
print("done")
