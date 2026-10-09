# -*- coding: utf-8 -*-
import re
base = r"E:\gzRJ\3Dmine\2023\3DMine V202310\3DMine V202310"
p = base + r"\common\cui\3dmine_profile_chinese\00_标准界面\menu_default.xml"
s = open(p, encoding="utf-8", errors="replace").read()
out = []
i = s.find("PyMacro")
if i >= 0:
    gi = s.rfind("<menu_group", 0, i)
    ge = s.find("</menu_group>", i) + len("</menu_group>")
    out.append(s[gi:ge])
    # 该组在哪个父组里
    gi2 = s.rfind("<menu_group", 0, gi - 1)
    if gi2 >= 0:
        ge2 = s.find(">", gi2)
        out.append("\n父组: " + s[gi2:ge2+1])
else:
    out.append("no PyMacro")
# 顶层菜单组列表
tops = re.findall(r"<menu_group name=\"([^\"]+)\"", s)
out.append("\n顶层菜单组: " + " | ".join(tops[:40]))
open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\newmenu_pymacro.txt", "w", encoding="utf-8").write("\n".join(out))
print("done")
