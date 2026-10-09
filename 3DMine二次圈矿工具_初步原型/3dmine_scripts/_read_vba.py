# -*- coding: utf-8 -*-
import os
out = []
d = r"E:\gzRJ\3Dmine\2022\demo\专题示例\10_二次开发\VBA示例"
for f in ["创建点.vbm", "创建面.vbm", "创建多段线.vbm", "数据库测试_遍历所有孔_打印孔号.vbm", "创建单行文字.vbm"]:
    p = os.path.join(d, f)
    raw = open(p, "rb").read()
    head = raw[:64]
    # 尝试多种编码解码
    dec = "?"
    for enc in ("utf-8", "gbk", "utf-16"):
        try:
            head.decode(enc)
            dec = enc
            break
        except Exception:
            pass
    out.append("=== %s size=%d enc~%s ===" % (f, len(raw), dec))
    txt = None
    for enc in ("utf-8", "gbk", "utf-16"):
        try:
            txt = raw.decode(enc)
            break
        except Exception:
            continue
    if txt:
        out.append(txt[:1500])
    out.append("")
open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\vba_samples.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
