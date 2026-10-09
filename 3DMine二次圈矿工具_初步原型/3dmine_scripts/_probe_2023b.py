# -*- coding: utf-8 -*-
import os, re
out = []
root = r"E:\gzRJ\3Dmine\2023\3DMine V202310免安装程序\3DMine V202310免安装程序"

# demo Python 示例
d = os.path.join(root, "demo")
out.append("=== demo ===")
if os.path.isdir(d):
    for f in sorted(os.listdir(d)):
        out.append("  " + f)

# python 目录
py = os.path.join(root, "common", "python")
out.append("\n=== common\\python ===")
if os.path.isdir(py):
    for f in sorted(os.listdir(py)):
        out.append("  " + f)

# plugin 目录
pl = os.path.join(root, "common", "plugin")
out.append("\n=== common\\plugin ===")
if os.path.isdir(pl):
    for f in sorted(os.listdir(pl))[:30]:
        out.append("  " + f)

# 菜单里 Macro Path / python
out.append("\n=== 菜单 Macro/Python 搜索 ===")
cui = os.path.join(root, "common", "cui", "3dmine_profile_chinese")
for prof in os.listdir(cui):
    mp = os.path.join(cui, prof, "menu_default.xml")
    if not os.path.exists(mp):
        continue
    s = open(mp, encoding="utf-8", errors="replace").read()
    macros = re.findall(r"<Macro Path[^>]*>", s)
    pys = re.findall(r"[Pp]ython", s)
    out.append("  %s: MacroPath=%d python字=%d" % (prof, len(macros), len(pys)))
    for mm in macros[:5]:
        i = s.rfind("<menu_item", 0, s.find(mm))
        seg = s[i:s.find(mm)+200].replace("\n", " ")
        out.append("     " + re.sub(r"\s+", " ", seg)[:200])

# license.ini 摘要
lic = os.path.join(root, "common", "config", "license.ini")
out.append("\n=== license.ini ===")
if os.path.exists(lic):
    s = open(lic, encoding="gbk", errors="replace").read()
    out.append(s[:400])

open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\probe2023b.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
