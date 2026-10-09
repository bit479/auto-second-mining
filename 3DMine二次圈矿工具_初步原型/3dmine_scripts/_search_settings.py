# -*- coding: utf-8 -*-
import os, re
out = []
base = r"E:\gzRJ\3Dmine\2022\common\cui\3dmine_profile_chinese"
for prof in ["00_标准界面", "01_煤炭界面", "02_地勘界面", "03_通风界面"]:
    p = os.path.join(base, prof, "menu_default.xml")
    s = open(p, encoding="utf-8").read()
    hits = []
    for kw in ["系统设置", "设置界面", "Python", "Python环境", "python环境", "运行环境", "环境设置", "Option", "选项"]:
        for m in re.finditer(kw, s):
            seg = s[max(0, m.start()-150):m.start()+200].replace("\n", " ")
            seg = re.sub(r"\s+", " ", seg)
            hits.append("kw=%s :: ...%s..." % (kw, seg[:220]))
    out.append("### %s ###" % prof)
    out.extend(hits[:12] if hits else ["(none)"])
    out.append("")
open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\settings_search.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
