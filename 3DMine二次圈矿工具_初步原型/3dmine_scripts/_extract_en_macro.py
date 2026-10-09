# -*- coding: utf-8 -*-
import re

p = r"E:\gzRJ\3Dmine\2022\common\cui\3dmine_profile_english\03_Ventilation  Profile\menu_default.xml"
s = open(p, encoding="utf-8").read()
i = s.find('name="Macro"')
out = s[i:i + 1200]
open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\macro_group_en.txt", "w", encoding="utf-8").write(out)
print("ok")
