# -*- coding: utf-8 -*-
"""给宏加阶段日志：任何执行都会留痕。"""
import io

p = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\3dmine_scripts\mine_1004_macro.py"
src = io.open(p, encoding="gbk").read()

old = """def main():
    try:
        from mine import *
        from mine_enum import *

        database = GetActiveDbDatabase()"""
new = """def main():
    log("SCRIPT_STARTED")
    try:
        import mine
        log("IMPORT_MINE_OK")
        from mine import *
        from mine_enum import *
        log("IMPORT_STAR_OK")

        database = GetActiveDbDatabase()
        log("DB_OBTAINED")"""
assert old in src, "main head not found"
src = src.replace(old, new)

# 每类对象创建后补一行计数日志
old2 = """        # ---- 1. 炮孔点（孔号 + 品位） ----
        for hd in data["holes"]:"""
new2 = """        # ---- 1. 炮孔点（孔号 + 品位） ----
        n_holes = 0
        for hd in data["holes"]:
            n_holes += 1"""
assert old2 in src, "holes block not found"
src = src.replace(old2, new2)

old3 = """            database.AddDbObject(pt, True)
        log("holes ok: %d" % len(data["holes"]))"""
new3 = """            database.AddDbObject(pt, True)
        log("holes ok: %d" % n_holes)"""
assert old3 in src, "holes log not found"
src = src.replace(old3, new3)

io.open(p, "w", encoding="gbk", newline="\n").write(src)
print("stage-log patched, size:", len(src.encode("gbk")))
