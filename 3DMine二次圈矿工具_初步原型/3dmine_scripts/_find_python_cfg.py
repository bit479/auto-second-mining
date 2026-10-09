# -*- coding: utf-8 -*-
import os, re
out = []
# 1) common\config 下所有文件找 python
cfg = r"E:\gzRJ\3Dmine\2022\common\config"
if os.path.isdir(cfg):
    for f in os.listdir(cfg):
        p = os.path.join(cfg, f)
        if os.path.isfile(p):
            try:
                s = open(p, encoding="utf-8", errors="replace").read()
            except Exception:
                s = open(p, encoding="gbk", errors="replace").read()
            if re.search(r"python|py_|pythonexe|pyenv", s, re.I):
                out.append("FILE %s" % f)
                for m in list(re.finditer(r".{80}python.{120}", s, re.I))[:5]:
                    out.append("   ..." + re.sub(r"\s+", " ", m.group(0))[:200])
# 2) 安装根下的 ini/txt/xml 搜 python
out.append("\n=== root configs ===")
for f in os.listdir(r"E:\gzRJ\3Dmine\2022"):
    if f.lower().endswith((".ini", ".txt", ".cfg", ".xml", ".dat")):
        p = os.path.join(r"E:\gzRJ\3Dmine\2022", f)
        try:
            s = open(p, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        if re.search(r"python", s, re.I):
            out.append("ROOT FILE %s" % f)
# 3) 注册表 MineReporter 或 3DMine 相关
import winreg
for hive, name in [(winreg.HKEY_CURRENT_USER, "HKCU"), (winreg.HKEY_LOCAL_MACHINE, "HKLM")]:
    try:
        k = winreg.OpenKey(hive, r"Software\Classes", 0, winreg.KEY_READ)
        out.append("\n%s Classes VisualMine check: " % name)
    except Exception as e:
        out.append("open fail %s" % e)
open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\python_cfg_search.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
