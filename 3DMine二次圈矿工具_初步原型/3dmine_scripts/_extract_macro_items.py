# -*- coding: utf-8 -*-
"""找出 menu_default.xml 中所有 <Macro Path 出现处及上下文，判断官方宏菜单项结构。"""
import re

p = r"E:\gzRJ\3Dmine\2022\common\cui\3dmine_profile_chinese\00_标准界面\menu_default.xml"
s = open(p, encoding="utf-8").read()

out = []
for m in re.finditer(r"<Macro Path[^>]*>", s):
    # 找所在 menu_item 块
    start = s.rfind("<menu_item", 0, m.start())
    end = s.find("</menu_item>", m.end())
    block = s[start:end + len("</menu_item>")]
    out.append("----- @" + str(m.start()) + " -----\n" + block[:600])

open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\macro_items.txt", "w", encoding="utf-8").write(
    "\n\n".join(out))
print("found", len(out))
