# -*- coding: utf-8 -*-
"""恢复新路径 menu_default.xml 到原版：删除 PyMacro 组、恢复测试python2 原路径。"""
import re

p = r"E:\gzRJ\3Dmine\2023\3DMine V202310\3DMine V202310\common\cui\3dmine_profile_chinese\00_标准界面\menu_default.xml"
s = open(p, encoding="utf-8", errors="replace").read()
out = []

# 1) 删 PyMacro 组
i = s.find('name="PyMacro')
if i >= 0:
    gi = s.rfind("<menu_group", 0, i)
    ge = s.find("</menu_group>", i)
    if ge < 0:
        out.append("ERROR: PyMacro group not closed")
    else:
        ge = ge + len("</menu_group>")
        seg = s[gi:ge]
        s = s.replace(seg, "")
        out.append("removed PyMacro group: %d chars" % len(seg))
else:
    out.append("PyMacro not present")

# 2) 恢复测试python2 原路径
i2 = s.find('name="测试python2"')
if i2 >= 0:
    j2 = s.find("</menu_item>", i2)
    block = s[i2:j2]
    nb = re.sub(r'<Macro Path[^>]*>', lambda m: '<Macro Path ="D:\\3d_mine_2\\test.py" />', block)
    s = s[:i2] + nb + s[j2:]
    out.append("restored 测试python2")
else:
    out.append("测试python2 not present")

open(p, "w", encoding="utf-8").write(s)

import xml.dom.minidom as md
try:
    md.parse(p)
    out.append("XML PARSE OK")
except Exception as e:
    out.append("XML PARSE FAIL: %s" % e)

open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\restore2023new_log.txt", "w", encoding="utf-8").write("\n".join(out))
print("\n".join(out))
