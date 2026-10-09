# -*- coding: utf-8 -*-
import os, re
p = r"E:\gzRJ\3Dmine\2023\3DMine V202310免安装程序\3DMine V202310免安装程序\common\cui\3dmine_profile_chinese\00_标准界面\menu_default.xml"
s = open(p, encoding="utf-8", errors="replace").read()
# 找 测试python 所在 menu_group
i = s.find('name="测试python"')
# 向前找 menu_group
gi = s.rfind("<menu_group", 0, i)
gj = s.find(">", gi)
seg = s[gi:gj + 1]
out = ["测试python 所在组: " + seg]
# 该组内全部 menu_item 名
ge = s.find("</menu_group>", gi)
block = s[gi:ge]
items = re.findall(r'<menu_item name="([^"]+)"', block)
out.append("组内菜单项: " + " | ".join(items))
open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\testpython_loc.txt", "w", encoding="utf-8").write("\n".join(out))
print("\n".join(out))
