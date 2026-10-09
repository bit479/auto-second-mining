# -*- coding: utf-8 -*-
"""部署 1004 宏到 2023 版 3DMine 的 3 个位置 + 加 PyMacro 菜单组。"""
import os, re

root = r"E:\gzRJ\3Dmine\2023\3DMine V202310免安装程序\3DMine V202310免安装程序"
SRC = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\3dmine_scripts\mine_1004_macro.py"
s = open(SRC, encoding="utf-8").read()
out = []

# 1) 部署 3 位置
targets = [
    os.path.join(root, "common", "test_mine.py"),
    os.path.join(root, "common", "cui", "test_mine.py"),
    os.path.join(root, "common", "cui", "3dmine_profile_chinese", "00_标准界面", "test_mine.py"),
]
for t in targets:
    os.makedirs(os.path.dirname(t), exist_ok=True)
    open(t, "w", encoding="utf-8").write(s)
    compile(s, t, "exec")
    out.append("deployed: " + t)

# 2) 加 PyMacro 菜单组（00_标准界面）
mp = os.path.join(root, "common", "cui", "3dmine_profile_chinese", "00_标准界面", "menu_default.xml")
ms = open(mp, encoding="utf-8", errors="replace").read()
if 'name="PyMacro' in ms:
    out.append("menu: PyMacro already exists")
else:
    group = '''  <menu_group name="PyMacro(^M)">
    <menu_item name="RunMacroTest">
      <Version ID="1.0" />
      <Visibility value="yes" />
      <Function name="" />
      <Icon small_image_name="" large_image_name="" />
      <Help Tip="RunMacroTest" HelpSource="AAA" />
      <Macro Path="test_mine.py" />
    </menu_item>
    <menu_item name="RunMacroTest2">
      <Version ID="1.0" />
      <Visibility value="yes" />
      <Function name="" />
      <Icon small_image_name="" large_image_name="" />
      <Help Tip="RunMacroTest2" HelpSource="AAA" />
      <Macro Path="..\\test_mine.py" />
    </menu_item>
    <menu_item name="RunMacroTest3">
      <Version ID="1.0" />
      <Visibility value="yes" />
      <Function name="" />
      <Icon small_image_name="" large_image_name="" />
      <Help Tip="RunMacroTest3" HelpSource="AAA" />
      <Macro Path="..\\..\\common\\test_mine.py" />
    </menu_item>
  </menu_group>
'''
    m2 = re.search(r"<menu_group\b", ms)
    if m2:
        ms = ms[:m2.start()] + group + "\n" + ms[m2.start():]
        open(mp, "w", encoding="utf-8").write(ms)
        out.append("menu: PyMacro group added")
    else:
        out.append("menu: no menu_group anchor!")

open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\deploy2023_log.txt", "a", encoding="utf-8").write("\n" + "\n".join(out))
print("\n".join(out))
