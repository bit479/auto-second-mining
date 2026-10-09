# -*- coding: utf-8 -*-
"""恢复 2023 版 appsetting.txt m_pyPath 为空（原版状态）。"""
import re

p = r"E:\gzRJ\3Dmine\2023\3DMine V202310\3DMine V202310\common\config\appsetting.txt"
s = open(p, encoding="gbk", errors="replace").read()
if re.search(r"m_pyPath=", s):
    s2 = re.sub(r"m_pyPath=[^\r\n]*", "m_pyPath=", s)
    open(p, "w", encoding="gbk").write(s2)
    print("restored m_pyPath empty")
else:
    print("no m_pyPath key")
# 确认
s3 = open(p, encoding="gbk", errors="replace").read()
for l in s3.splitlines():
    if "pyPath" in l:
        print("CONFIRM:", repr(l))
