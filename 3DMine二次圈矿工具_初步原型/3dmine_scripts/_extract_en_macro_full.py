# -*- coding: utf-8 -*-
import re

p = r"E:\gzRJ\3Dmine\2022\common\cui\3dmine_profile_english\03_Ventilation  Profile\menu_default.xml"
s = open(p, encoding="utf-8").read()
i = s.find('name="Macro"')
# 到下一个 menu_group 为止
j = s.find("<menu_group", i + 10)
block = s[i:j if j > 0 else i + 4000]
open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\macro_group_en_full.txt", "w", encoding="utf-8").write(block)
print("ok", len(block))
