# -*- coding: utf-8 -*-
import os
out = []
d = r"E:\gzRJ\3Dmine\2022\demo\专题示例\10_二次开发\VBA示例"
for f in ["创建点.vbm", "创建面.vbm"]:
    p = os.path.join(d, f)
    raw = open(p, "rb").read()
    out.append("=== %s ===" % f)
    try:
        txt = raw.decode("utf-16")
    except Exception as e:
        out.append("utf16 fail: %s" % e)
        continue
    # 过滤控制字符
    vis = "".join(ch for ch in txt if ch.isprintable() or ch in "\r\n\t")
    out.append(vis[:3000])
    out.append("")
open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\vba_utf16.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
