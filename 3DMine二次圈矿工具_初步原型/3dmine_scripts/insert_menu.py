# -*- coding: utf-8 -*-
"""Insert standalone PyMacro menu group with ABSOLUTE Macro Path (C:\\tmp\\test_mine.py)."""
import io

path = r"E:\gzRJ\3Dmine\2022\common\cui\3dmine_profile_chinese\00_标准界面\menu_default.xml"

with io.open(path, "rb") as f:
    data = f.read()

root_open = b"<3dmine_menu>"
assert root_open in data, "root not found"

group = (
    '  <menu_group name="PyMacro(^M)">\r\n'
    '    <menu_item name="RunMacroTest">\r\n'
    '      <Version ID="1.0" />\r\n'
    '      <Visibility value="yes" />\r\n'
    '      <Function name="" />\r\n'
    '      <Icon small_image_name="" large_image_name="" />\r\n'
    '      <Help Tip="RunMacroTest" HelpSource="AAA" />\r\n'
    '      <Macro Path="test_mine.py" />\r\n'
    '    </menu_item>\r\n'
    '  </menu_group>\r\n'
).encode("utf-8")

idx = data.find(root_open) + len(root_open)
data2 = data[:idx] + b"\r\n" + group + data[idx:]

with io.open(path, "wb") as f:
    f.write(data2)

print("inserted:", len(data2) - len(data))
