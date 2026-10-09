# -*- coding: utf-8 -*-
"""Patch PyMacro menu: replace absolute Macro Path with 3 relative-path variants."""
p = r"E:\gzRJ\3Dmine\2022\common\cui\3dmine_profile_chinese\00_标准界面\menu_default.xml"
s = open(p, encoding="utf-8").read()

old = """    <menu_item name="RunMacroTest">
      <Version ID="1.0" />
      <Visibility value="yes" />
      <Function name="" />
      <Icon small_image_name="" large_image_name="" />
      <Help Tip="RunMacroTest" HelpSource="AAA" />
      <Macro Path="E:\\gzRJ\\3Dmine\\2022\\common\\test_mine.py" />
    </menu_item>"""

new = """    <menu_item name="RunMacroTest">
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
    </menu_item>"""

assert old in s, "old block not found"
s = s.replace(old, new)
open(p, "w", encoding="utf-8").write(s)
print("patched ok")
