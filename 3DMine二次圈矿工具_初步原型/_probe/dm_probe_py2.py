# -*- coding: utf-8 -*-
"""在 3DMine(3DMIN PLUS, Python 2.7 内嵌) 里执行：dump mine API 能力。

输出: D:\\WK\\N CRT\\3DMine二次圈矿工具_初步原型\\_probe\\probe_out.txt
"""
import os
import sys
import traceback

OUT = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\_probe\probe_out.txt"


def w(msg):
    try:
        f = open(OUT, "a")
        f.write(str(msg) + "\n")
        f.close()
    except Exception:
        pass


def main():
    w("")
    w("===== START =====")
    w("pid=%s" % os.getpid())
    w("executable=%s" % sys.executable)
    w("version=%s" % sys.version.replace("\n", " "))
    w("cwd=%s" % os.getcwd())
    w("pythonhome=%s" % os.environ.get("PYTHONHOME"))
    w("sys.path=%s" % repr(sys.path))
    try:
        import mine
        w("import mine: OK (%s)" % getattr(mine, "__file__", "?"))
    except Exception:
        w("import mine: FAIL")
        w(traceback.format_exc())
        w("===== END =====")
        return

    names = sorted([n for n in dir(mine) if not n.startswith("_")])
    w("mine members = %d" % len(names))
    w("mine members: " + ", ".join(names))

    g = globals()
    try:
        g.update(mine.__dict__)
        w("inject mine globals: OK")
    except Exception:
        w("inject mine globals FAIL: %s" % traceback.format_exc())

    try:
        import mine_enum
        enames = sorted([n for n in dir(mine_enum) if not n.startswith("_")])
        w("mine_enum members = %d" % len(enames))
        w("mine_enum members: " + ", ".join(enames))
        for k in enames:
            g[k] = getattr(mine_enum, k)
        w("inject mine_enum globals: OK")
    except Exception:
        w("mine_enum FAIL: %s" % traceback.format_exc())

    for fn in ("GetActiveDbDatabase", "GetAppSetting", "Update_Layer_Manager"):
        w("%s callable=%s" % (fn, callable(g.get(fn))))

    db = None
    try:
        db = g["GetActiveDbDatabase"]()
        w("GetActiveDbDatabase() -> %r" % (db,))
    except Exception:
        w("GetActiveDbDatabase FAIL: %s" % traceback.format_exc())

    if db is not None:
        dnames = sorted([n for n in dir(db) if not n.startswith("_")])
        w("database members = %d" % len(dnames))
        w("database members: " + ", ".join(dnames))
        for meth in ("getDrillHoleManage", "getBlockModel", "getLayerTree"):
            try:
                obj = getattr(db, meth)()
                mnames = sorted([n for n in dir(obj) if not n.startswith("_")])
                w("%s() -> %r  members=%d" % (meth, obj, len(mnames)))
                w("%s members: %s" % (meth, ", ".join(mnames)))
            except Exception:
                w("%s FAIL: %s" % (meth, traceback.format_exc()))

    try:
        w("BlockEstimate: %r" % (g.get("BlockEstimate"),))
        w("BlocksReport: %r" % (g.get("BlocksReport"),))
        w("GetVisualMineCommand: %r" % (g.get("GetVisualMineCommand"),))
    except Exception:
        w("probe helpers FAIL: %s" % traceback.format_exc())

    w("===== END =====")


main()
