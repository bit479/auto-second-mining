# -*- coding: utf-8 -*-
import os, re
p = r"E:\gzRJ\3Dmine\2022\common\cui\3dmine_profile_chinese\00_标准界面\menu_default.xml"
s = open(p, encoding="utf-8").read()
i = s.find('name="系统设置"')
seg = s[max(0, i - 900):i + 200]
open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\sysopt_ctx.txt", "w", encoding="utf-8").write(seg)
print("ok")
