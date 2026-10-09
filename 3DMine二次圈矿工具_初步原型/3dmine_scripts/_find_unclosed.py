# -*- coding: utf-8 -*-
"""找出 menu_default.xml 中未闭合的 <menu_group> 并修复。"""
import re

p = r"E:\gzRJ\3Dmine\2023\3DMine V202310\3DMine V202310\common\cui\3dmine_profile_chinese\00_标准界面\menu_default.xml"
s = open(p, encoding="utf-8", errors="replace").read()

# 去掉注释块（<!-- ... -->），避免注释里的标签干扰
s_no_cmt = re.sub(r"<!--.*?-->", "", s, flags=re.S)

# 栈式跟踪 menu_group
stack = []
for m in re.finditer(r"<menu_group\b[^>]*>|</menu_group>", s_no_cmt):
    tok = m.group(0)
    if tok.startswith("</"):
        if stack:
            stack.pop()
        else:
            print("EXTRA CLOSE at", m.start())
    else:
        stack.append((m.start(), tok[:60]))
print("UNCLOSED groups:", len(stack))
for pos, tok in stack:
    print("  at", pos, tok)
