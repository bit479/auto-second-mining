# -*- coding: utf-8 -*-
"""提取 menu_default.xml 的工具菜单组和 PyMacro 菜单组完整定义。"""
import re

p = r"E:\gzRJ\3Dmine\2022\common\cui\3dmine_profile_chinese\00_标准界面\menu_default.xml"
s = open(p, encoding="utf-8").read()

out = []
# PyMacro 组完整
i = s.find('name="PyMacro')
out.append("=== PyMacro group ===")
out.append(s[i:i + 400])

# 工具 菜单组
i2 = s.find('name="工具')
if i2 < 0:
    i2 = s.find("工具(^T)")
out.append("\n=== 工具 group (idx %d) ===" % i2)
out.append(s[i2:i2 + 1800])

open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\tools_menu.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
