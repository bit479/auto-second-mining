# -*- coding: utf-8 -*-
"""把 2023 版官方"测试python2"菜单项指向我们的 1004 宏（绝对路径，与官方原格式一致）。"""
import re

p = r"E:\gzRJ\3Dmine\2023\3DMine V202310免安装程序\3DMine V202310免安装程序\common\cui\3dmine_profile_chinese\00_标准界面\menu_default.xml"
s = open(p, encoding="utf-8", errors="replace").read()

# 找 测试python2 块
i = s.find('name="测试python2"')
assert i >= 0, "not found"
j = s.find("</menu_item>", i)
block = s[i:j]
print("BEFORE:", re.sub(r"\s+", " ", block))

new_block = re.sub(
    r'<Macro Path[^>]*>',
    '<Macro Path="D:\\\\WK\\\\N CRT\\\\3DMine二次圈矿工具_初步原型\\\\3dmine_scripts\\\\mine_1004_macro.py" />',
    block,
)
s = s[:i] + new_block + s[j:]
open(p, "w", encoding="utf-8").write(s)
print("AFTER:", re.sub(r"\s+", " ", new_block))
print("patched")
