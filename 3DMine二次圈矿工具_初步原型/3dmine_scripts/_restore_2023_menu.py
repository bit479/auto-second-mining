# -*- coding: utf-8 -*-
"""恢复 2023 版 menu_default.xml：删除 PyMacro 组、恢复测试python2 原路径。"""
import re

p = r"E:\gzRJ\3Dmine\2023\3DMine V202310免安装程序\3DMine V202310免安装程序\common\cui\3dmine_profile_chinese\00_标准界面\menu_default.xml"
s = open(p, encoding="utf-8", errors="replace").read()
out = []

# 1) 删除 PyMacro 组（含其前导换行/缩进）
i = s.find('name="PyMacro')
if i >= 0:
    start = i - 100
    gi = s.rfind("<menu_group", 0, i)
    ge = s.find("</menu_group>", i)
    if ge < 0:
        out.append("ERROR: PyMacro group not closed")
    else:
        ge = ge + len("</menu_group>")
        # 连同前导空白和可能的换行一起删
        seg = s[gi:ge]
        s = s.replace(seg, "")
        out.append("removed PyMacro group: %d chars" % len(seg))
else:
    out.append("PyMacro group not found (already removed?)")

# 2) 恢复测试python2
i2 = s.find('name="测试python2"')
if i2 >= 0:
    j2 = s.find("</menu_item>", i2)
    block = s[i2:j2]
    nb = re.sub(r'<Macro Path[^>]*>', '<Macro Path ="D:\\3d_mine_2\\test.py" />', block)
    s = s[:i2] + nb + s[j2:]
    out.append("restored 测试python2 -> D:\\3d_mine_2\\test.py")
else:
    out.append("测试python2 not found")

open(p, "w", encoding="utf-8").write(s)

# 3) XML 合法性检查
import xml.dom.minidom as md
try:
    md.parse(p)
    out.append("XML PARSE OK")
except Exception as e:
    out.append("XML PARSE FAIL: %s" % e)

open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\restore2023_log.txt", "w", encoding="utf-8").write("\n".join(out))
print("\n".join(out))
