# -*- coding: utf-8 -*-
"""安全配置新解压版 2023：① appsetting m_pyPath 一行；② 部署 test_mine.py 到 3 位置（不动菜单 XML）。"""
import os, re

base = r"E:\gzRJ\3Dmine\2023\3DMine V202310\3DMine V202310"
SRC = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\3dmine_scripts\mine_1004_macro.py"
s = open(SRC, encoding="utf-8").read()
out = []

# 1) appsetting
ap = os.path.join(base, "common", "config", "appsetting.txt")
if os.path.exists(ap):
    as_ = open(ap, encoding="gbk", errors="replace").read()
    if re.search(r"m_pyPath=..\\bin\\nt_x64\\python39.dll", as_):
        out.append("m_pyPath already set")
    elif re.search(r"m_pyPath=", as_):
        as2 = re.sub(r"m_pyPath=[^\r\n]*", r"m_pyPath=..\\bin\\nt_x64\\python39.dll", as_)
        open(ap, "w", encoding="gbk").write(as2)
        out.append("m_pyPath set")
    else:
        out.append("NO m_pyPath key")
else:
    out.append("appsetting missing")

# 2) 部署宏 3 位置（不改菜单）
targets = [
    os.path.join(base, "common", "test_mine.py"),
    os.path.join(base, "common", "cui", "test_mine.py"),
    os.path.join(base, "common", "cui", "3dmine_profile_chinese", "00_标准界面", "test_mine.py"),
]
for t in targets:
    os.makedirs(os.path.dirname(t), exist_ok=True)
    open(t, "w", encoding="utf-8").write(s)
    compile(s, t, "exec")
    out.append("deployed: " + t)

# 3) 确认菜单未被改动（PyMacro 应不存在）
mp = os.path.join(base, "common", "cui", "3dmine_profile_chinese", "00_标准界面", "menu_default.xml")
ms = open(mp, encoding="utf-8", errors="replace").read()
out.append("menu PyMacro exists: %s" % ("PyMacro" in ms))

open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\deploy2023new_log.txt", "w", encoding="utf-8").write("\n".join(out))
print("\n".join(out))
