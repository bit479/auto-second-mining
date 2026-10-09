# -*- coding: utf-8 -*-
import olefile, os

out = []
p = r"E:\gzRJ\3Dmine\2022\demo\专题示例\10_二次开发\VBA示例\创建点.vbm"
if not olefile.isOleFile(p):
    out.append("NOT an OLE file")
else:
    ole = olefile.OleFileIO(p)
    out.append("OLE streams:")
    for entry in ole.listdir():
        out.append("  /".join(entry))
    # 找源码类流
    for entry in ole.listdir():
        if len(entry) == 1:
            continue
        name = "/".join(entry)
        if any(k in name.lower() for k in ("macro", "module", "basic", "source", "vba", "text")):
            try:
                data = ole.openstream(entry).read()
                txt = None
                for enc in ("utf-16", "utf-8", "gbk"):
                    try:
                        txt = data.decode(enc)
                        break
                    except Exception:
                        continue
                out.append("\n=== stream %s size=%d ===" % (name, len(data)))
                if txt:
                    vis = "".join(ch for ch in txt if ch.isprintable() or ch in "\r\n\t")
                    out.append(vis[:4000])
            except Exception as e:
                out.append("stream %s read fail: %s" % (name, e))
    ole.close()

open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\vbm_ole.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
