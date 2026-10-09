# -*- coding: utf-8 -*-
import os
out = []
root = r"E:\gzRJ\3Dmine\2023\3DMine V202310免安装程序\3DMine V202310免安装程序"
out.append("=== root ===")
if os.path.isdir(root):
    for f in sorted(os.listdir(root)):
        out.append("  " + f)
else:
    out.append("NOT FOUND: " + root)

# bin
binp = os.path.join(root, "bin", "nt_x64")
out.append("\n=== bin\\nt_x64 关键模块 ===")
if os.path.isdir(binp):
    for f in sorted(os.listdir(binp)):
        low = f.lower()
        if any(k in low for k in ("python", "vba", "mineapi", "module_40", "module_11", "visualmine", "mine_enum", "mine.pyd")):
            p = os.path.join(binp, f)
            out.append("  %s (%d)" % (f, os.path.getsize(p)))
    # 全部 python/vba 相关
    out.append("\n=== python/vba 全部 ===")
    for f in sorted(os.listdir(binp)):
        low = f.lower()
        if "python" in low or "vba" in low:
            out.append("  " + f)

# common
common = os.path.join(root, "common")
out.append("\n=== common ===")
if os.path.isdir(common):
    for f in sorted(os.listdir(common)):
        out.append("  " + f)
# common\test_mine.py?
tp = os.path.join(common, "test_mine.py")
out.append("test_mine.py exists: %s" % os.path.exists(tp))
# config
cfg = os.path.join(common, "config")
out.append("\n=== common\\config ===")
if os.path.isdir(cfg):
    for f in sorted(os.listdir(cfg)):
        out.append("  " + f)
    ap = os.path.join(cfg, "appsetting.txt")
    if os.path.exists(ap):
        s = open(ap, encoding="gbk", errors="replace").read()
        for line in s.splitlines():
            if "py" in line.lower():
                out.append("  [appsetting] " + line[:120])
# cui profiles
cui = os.path.join(common, "cui", "3dmine_profile_chinese")
out.append("\n=== cui chinese profiles ===")
if os.path.isdir(cui):
    for f in sorted(os.listdir(cui)):
        out.append("  " + f)
# PyMacro in menu
for prof in os.listdir(cui) if os.path.isdir(cui) else []:
    mp = os.path.join(cui, prof, "menu_default.xml")
    if os.path.exists(mp):
        s = open(mp, encoding="utf-8", errors="replace").read()
        has = "PyMacro" in s
        has_vba = "VBARunMacro" in s or "AppServerMain::VBA" in s
        out.append("  %s: PyMacro=%s VBAmenu=%s" % (prof, has, has_vba))
        if has:
            i = s.find('name="PyMacro')
            seg = s[i:i+400].replace("\n", " ")
            out.append("     PyMacro段: " + seg[:350])
open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\probe2023.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
