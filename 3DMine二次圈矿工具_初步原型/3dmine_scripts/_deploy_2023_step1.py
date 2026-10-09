# -*- coding: utf-8 -*-
"""配置 2023 版 3DMine：m_pyPath + 部署宏 + 加 PyMacro 菜单。"""
import os, re

root = r"E:\gzRJ\3Dmine\2023\3DMine V202310免安装程序\3DMine V202310免安装程序"
out = []

# 1) appsetting.txt: 配置 m_pyPath
ap = os.path.join(root, "common", "config", "appsetting.txt")
s = open(ap, encoding="gbk", errors="replace").read()
if re.search(r"m_pyPath=..\\bin\\nt_x64\\python39.dll", s):
    out.append("appsetting: m_pyPath already set")
elif re.search(r"m_pyPath=", s):
    s2 = re.sub(r"m_pyPath=[^\r\n]*", r"m_pyPath=..\\bin\\nt_x64\\python39.dll", s)
    open(ap, "w", encoding="gbk").write(s2)
    out.append("appsetting: m_pyPath set (was empty/other)")
else:
    out.append("appsetting: no m_pyPath key found!")
open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\deploy2023_log.txt", "w", encoding="utf-8").write("\n".join(out))
print("\n".join(out))
