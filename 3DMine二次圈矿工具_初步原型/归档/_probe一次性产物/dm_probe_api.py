# -*- coding: utf-8 -*-
"""3DMine 内嵌 Python 探针：dump mine API 能力，供原生通道可行性判定。

部署位置（无空格路径）：E:\\gzRJ\\3Dmine\\2022\\common\\py_tools\\dm_probe_api.py
触发方式：3DMine 菜单 "CodexPy(^K)" -> 各 Probe 项
输出：D:\\WK\\N CRT\\3DMine二次圈矿工具_初步原型\\_probe\\probe_out.txt
"""
import os
import sys
import traceback

OUT = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\_probe\probe_out.txt"


def w(msg):
    try:
        with open(OUT, "a", encoding="utf-8") as f:
            f.write(str(msg) + "\n")
    except Exception:
        pass


def head(title):
    w("")
    w("===== %s =====" % title)
    w("pid=%s" % os.getpid())
    w("sys.executable=%s" % sys.executable)
    w("cwd=%s" % os.getcwd())
    w("argv=%r" % (sys.argv,))
    w("frozen=%s" % getattr(sys, "frozen", None))
    w("sys.path=%r" % (sys.path,))


def main():
    head("START")
    try:
        import mine

        w("import mine: OK (%s)" % getattr(mine, "__file__", "?"))
    except Exception:
        w("import mine: FAIL")
        w(traceback.format_exc())
        w("===== ABORT =====")
        return

    names = sorted(n for n in dir(mine) if not n.startswith("_"))
    w("mine 成员数=%d" % len(names))
    w("mine 成员: " + ", ".join(names))

    g = globals()
    try:
        g.update(mine.__dict__)
        w("注入 mine 全局: OK")
    except Exception:
        w("注入 mine 全局 FAIL: %s" % traceback.format_exc())

    try:
        import mine_enum

        enames = sorted(n for n in dir(mine_enum) if not n.startswith("_"))
        w("mine_enum 成员数=%d" % len(enames))
        w("mine_enum 成员: " + ", ".join(enames))
        g.update({k: getattr(mine_enum, k) for k in enames})
        w("注入 mine_enum 全局: OK")
    except Exception:
        w("mine_enum FAIL: %s" % traceback.format_exc())

    for fn_name in ("GetActiveDbDatabase", "GetAppSetting", "Update_Layer_Manager"):
        w("%s 可用=%s" % (fn_name, callable(g.get(fn_name))))

    db = None
    try:
        db = g["GetActiveDbDatabase"]()
        w("GetActiveDbDatabase() -> %r" % (db,))
    except Exception:
        w("GetActiveDbDatabase FAIL: %s" % traceback.format_exc())

    if db is not None:
        dnames = sorted(n for n in dir(db) if not n.startswith("_"))
        w("database 成员数=%d" % len(dnames))
        w("database 成员: " + ", ".join(dnames))
        for meth in ("getDrillHoleManage", "getBlockModel"):
            try:
                obj = getattr(db, meth)()
                mnames = sorted(n for n in dir(obj) if not n.startswith("_"))
                w("%s() -> %r  成员数=%d" % (meth, obj, len(mnames)))
                w("%s 成员: %s" % (meth, ", ".join(mnames)))
            except Exception:
                w("%s FAIL: %s" % (meth, traceback.format_exc()))

    w("===== END =====")


main()
