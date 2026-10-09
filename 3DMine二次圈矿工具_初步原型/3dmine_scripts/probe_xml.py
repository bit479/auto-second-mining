# -*- coding: utf-8 -*-
import io
path = r"E:\gzRJ\3Dmine\2022\common\cui\3dmine_profile_chinese\00_标准界面\menu_default.xml"
with io.open(path, "rb") as f:
    data = f.read()
print("len", len(data))
print("head bytes", data[:60])
# find first menu_group
idx = data.find(b"<menu_group")
print("first menu_group at", idx)
print(data[idx-30:idx+80])
