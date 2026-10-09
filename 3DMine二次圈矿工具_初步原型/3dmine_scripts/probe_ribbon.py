# -*- coding: utf-8 -*-
import io
p = r"E:\gzRJ\3Dmine\2022\common\cui\3dmine_profile_chinese\00_标准界面\ribbon_default.xml"
data = io.open(p, "rb").read()
marker = "\u52a0\u8f7d".encode("utf-8")  # 加载
i = data.find(b'PANEL Name="' + marker + b'"')
print("panel at", i)
if i > 0:
    print(data[i - 100 : i + 1600].decode("utf-8", "replace"))
