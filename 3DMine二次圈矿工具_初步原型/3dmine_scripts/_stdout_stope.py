# -*- coding: utf-8 -*-
import re
base = r"E:\gzRJ\3Dmine\2023\3DMine V202310\3DMine V202310"
out = []
# mine_stdout.py
try:
    s = open(base + r"\bin\nt_x64\mine_stdout.py", encoding="utf-8", errors="replace").read()
    out.append("=== mine_stdout.py (%d chars) ===" % len(s))
    out.append(s[:1500])
except Exception as e:
    out.append("stdout err: %s" % e)
# 矿房设计 group
p = base + r"\common\cui\3dmine_profile_chinese\00_标准界面\menu_default.xml"
s = open(p, encoding="utf-8", errors="replace").read()
i = s.find('name="矿房设计"')
out.append("\n=== 矿房设计 group ===")
if i >= 0:
    gi = s.rfind("<menu_group", 0, i)
    ge = s.find(">", gi)
    out.append("group: " + s[gi:ge+1])
    ge2 = s.find("</menu_group>", gi)
    out.append("items: " + " | ".join(re.findall(r'<menu_item name="([^"]+)"', s[gi:ge2])))
else:
    out.append("矿房设计 not found")
open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\stdout_stope.txt", "w", encoding="utf-8").write("\n".join(out))
print("done")
