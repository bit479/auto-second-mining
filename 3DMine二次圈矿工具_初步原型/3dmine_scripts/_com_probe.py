# -*- coding: utf-8 -*-
"""尝试通过 COM 连接运行中的 3DMine。"""
import sys

try:
    import win32com.client
    print("win32com OK")
except Exception as e:
    print("win32com FAIL:", e)
    sys.exit(1)

import pythoncom

try:
    app = win32com.client.GetActiveObject("VisualMine.Application")
    print("GetActiveObject OK:", app)
except Exception as e:
    print("GetActiveObject FAIL:", e)
    try:
        app = win32com.client.Dispatch("VisualMine.Application")
        print("Dispatch OK:", app)
    except Exception as e2:
        print("Dispatch FAIL:", e2)
        sys.exit(1)

# 枚举接口成员
out = ["app=%s" % app]
try:
    d = win32com.client.Dispatch(app) if not hasattr(app, "_oleobj_") else app
    names = []
    for n in dir(d):
        if not n.startswith("_"):
            names.append(n)
    out.append("members=%s" % sorted(names)[:80])
except Exception as e:
    out.append("dir fail: %s" % e)

open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\com_probe.txt", "w", encoding="utf-8").write("\n".join(out))
print("\n".join(out[:5]))
