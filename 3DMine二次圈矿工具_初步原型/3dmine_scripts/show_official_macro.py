# -*- coding: utf-8 -*-
import io

p = r"E:\gzRJ\3Dmine\2022\common\cui\3dmine_profile_chinese\00_标准界面\menu_default.xml"
data = io.open(p, "rb").read()
pos = 0
for i in range(10):
    pos = data.find(b"Macro Path", pos)
    if pos == -1:
        break
    print("=== occurrence", i, "at", pos)
    print(data[max(0, pos - 700) : pos + 260].decode("utf-8", "replace"))
    print()
    pos += 1
