# -*- coding: utf-8 -*-
import os, re
out = []
root = r"E:\gzRJ\3Dmine\2023\3DMine V202310免安装程序\3DMine V202310免安装程序"

# 矿房设计 Macro Path 完整
mp = os.path.join(root, "common", "cui", "3dmine_profile_chinese", "00_标准界面", "menu_default.xml")
s = open(mp, encoding="utf-8", errors="replace").read()
for mm in re.finditer(r"<Macro Path[^>]*>", s):
    i = s.rfind("<menu_item", 0, mm.start())
    seg = s[i:mm.end()]
    out.append(re.sub(r"\s+", " ", seg))

# common\python\x64
py = os.path.join(root, "common", "python", "x64")
out.append("\n=== common\\python\\x64 ===")
if os.path.isdir(py):
    for f in sorted(os.listdir(py)):
        out.append("  " + f)

# plugin\python
pl = os.path.join(root, "common", "plugin", "python")
out.append("\n=== common\\plugin\\python ===")
if os.path.isdir(pl):
    for f in sorted(os.listdir(pl)):
        out.append("  " + f)

# 实体表面加密 文件存在性
for rel in [r"common\tools\mesh\pcldensitysurface.py", r"common\tools\ugtool\stope design.py"]:
    p = os.path.join(root, rel)
    out.append("%s -> %s" % (rel, os.path.exists(p)))

open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\probe2023c.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
