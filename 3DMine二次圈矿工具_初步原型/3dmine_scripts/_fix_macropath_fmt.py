# -*- coding: utf-8 -*-
"""检查 2022 版 PyMacro 原版 XML 格式（备份）与 2023 官方 Macro Path 格式对比，并统一修正。"""
import re, os

# 1) 2022 版备份里 PyMacro 原格式
bak = r"E:\gzRJ\3Dmine\2022\common\cui\3dmine_profile_chinese\00_标准界面\menu_default.xml"
out = []
if os.path.exists(bak):
    s = open(bak, encoding="utf-8", errors="replace").read()
    i = s.find("PyMacro")
    if i >= 0:
        j = s.find("</menu_group>", i)
        out.append("=== 2022 原版 PyMacro 组 ===")
        out.append(s[i:j][:1200])

# 2) 2023 当前 PyMacro 组
p23 = r"E:\gzRJ\3Dmine\2023\3DMine V202310免安装程序\3DMine V202310免安装程序\common\cui\3dmine_profile_chinese\00_标准界面\menu_default.xml"
s23 = open(p23, encoding="utf-8", errors="replace").read()
i23 = s23.find("PyMacro")
if i23 >= 0:
    j23 = s23.find("</menu_group>", i23)
    out.append("\n=== 2023 当前 PyMacro 组 ===")
    out.append(s23[i23:j23][:1200])

# 3) 修正 2023 PyMacro 组为带空格格式
new_group = '''  <menu_group name="PyMacro(^M)">
    <menu_item name="RunMacroTest">
      <Version ID="1.0" />
      <Visibility value="yes" />
      <Function name="" />
      <Icon small_image_name="" large_image_name="" />
      <Help Tip="RunMacroTest" HelpSource="AAA" />
      <Macro Path ="test_mine.py" />
    </menu_item>
    <menu_item name="RunMacroTest2">
      <Version ID="1.0" />
      <Visibility value="yes" />
      <Function name="" />
      <Icon small_image_name="" large_image_name="" />
      <Help Tip="RunMacroTest2" HelpSource="AAA" />
      <Macro Path ="..\\test_mine.py" />
    </menu_item>
    <menu_item name="RunMacroTest3">
      <Version ID="1.0" />
      <Visibility value="yes" />
      <Function name="" />
      <Icon small_image_name="" large_image_name="" />
      <Help Tip="RunMacroTest3" HelpSource="AAA" />
      <Macro Path ="..\\..\\common\\test_mine.py" />
    </menu_item>
  </menu_group>
'''
if i23 >= 0:
    j23 = s23.find("</menu_group>", i23) + len("</menu_group>")
    s23 = s23[:i23] + new_group + s23[j23:]
    open(p23, "w", encoding="utf-8").write(s23)
    out.append("\n=== patched 2023 PyMacro group (spaced format) ===")

open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\macropath_fmt.txt", "w", encoding="utf-8").write("\n".join(out))
print("done")
