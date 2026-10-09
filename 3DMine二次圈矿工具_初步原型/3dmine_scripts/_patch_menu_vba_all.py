# -*- coding: utf-8 -*-
"""给全部中文 profile 的 menu_default.xml 插入 VBA 宏菜单组。"""
import os, re

profiles = [
    "00_标准界面", "01_煤炭界面", "02_地勘界面", "03_通风界面",
]
base = r"E:\gzRJ\3Dmine\2022\common\cui\3dmine_profile_chinese"

macro_group = '''  <menu_group name="宏(^V)">
    <menu_item name="运行宏">
      <Version ID="1.0" />
      <Visibility value="yes" />
      <Function name="AppServerMain::VBARunMacro" />
      <Icon small_image_name="main_move.png" large_image_name="main_move32.png" />
      <Help Tip="运行VBA宏" HelpSource="AAA" />
    </menu_item>
    <menu_separator------------ />
    <menu_item name="宏安全设置">
      <Version ID="1.0" />
      <Visibility value="yes" />
      <Function name="AppServerMain::VBASecurity" />
      <Icon small_image_name="main_VBASecurity.png" large_image_name="main_VBASecurity32.png" />
      <Help Tip="宏安全设置" HelpSource="AAA" />
    </menu_item>
    <menu_separator------------ />
    <menu_item name="加载工程">
      <Version ID="1.0" />
      <Visibility value="yes" />
      <Function name="AppServerMain::VBAProjectLoad" />
      <Icon small_image_name="main_loading_the_project.png" large_image_name="main_loading_the_project32.png" />
      <Help Tip="加载VBA工程" HelpSource="AAA" />
    </menu_item>
    <menu_item name="新建工程">
      <Version ID="1.0" />
      <Visibility value="yes" />
      <Function name="AppServerMain::VBANewProject" />
      <Icon small_image_name="main_new_obj.png" large_image_name="main_new_obj32.png" />
      <Help Tip="新建VBA工程" HelpSource="AAA" />
    </menu_item>
    <menu_separator------------ />
    <menu_item name="VBA编辑器">
      <Version ID="1.0" />
      <Visibility value="yes" />
      <Function name="AppServerMain::VBAIDE" />
      <Icon small_image_name="main_vba_editor.png" large_image_name="main_vba_editor32.png" />
      <Help Tip="打开VBA编辑器" HelpSource="AAA" />
    </menu_item>
  </menu_group>
'''

out = []
for prof in profiles:
    p = os.path.join(base, prof, "menu_default.xml")
    if not os.path.exists(p):
        out.append("%s: MISSING" % prof)
        continue
    s = open(p, encoding="utf-8").read()
    if 'name="宏(^V)"' in s:
        out.append("%s: already has macro group" % prof)
        continue
    # 插到第一个 menu_group 前
    m = re.search(r"<menu_group\b", s)
    if not m:
        out.append("%s: no menu_group found" % prof)
        continue
    s = s[:m.start()] + macro_group + "\n" + s[m.start():]
    open(p, "w", encoding="utf-8").write(s)
    out.append("%s: patched OK" % prof)

open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\patch_all_profiles.txt", "w", encoding="utf-8").write("\n".join(out))
print("\n".join(out))
