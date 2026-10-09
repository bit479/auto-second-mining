# -*- coding: utf-8 -*-
import os
base = r"E:\gzRJ\3Dmine\2023\3DMine V202310\3DMine V202310\common\cui\3dmine_profile_chinese"
for prof in ["00_标准界面", "01_煤炭界面", "02_地勘界面", "03_通风界面"]:
    p = os.path.join(base, prof, "menu_default.xml")
    if not os.path.exists(p):
        print(prof, "MISSING")
        continue
    s = open(p, encoding="utf-8", errors="replace").read()
    print("%s: groups %d/%d, items %d/%d" % (prof, s.count("<menu_group"), s.count("</menu_group>"), s.count("<menu_item"), s.count("</menu_item>")))
# 删除点上下文（00 界面 PyMacro 原位置）
p0 = os.path.join(base, "00_标准界面", "menu_default.xml")
s0 = open(p0, encoding="utf-8", errors="replace").read()
i = s0.find("</3dmine_menu>")
print("\nclosing tag area:")
print(s0[i-300:i+50])
