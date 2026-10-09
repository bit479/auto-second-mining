# -*- coding: utf-8 -*-
"""部署 1004 宏（UTF-8）到 3 个候选位置。"""
import os

SRC = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\3dmine_scripts\mine_1004_macro.py"
s = open(SRC, encoding="utf-8").read()

targets = [
    r"E:\gzRJ\3Dmine\2022\common\test_mine.py",
    r"E:\gzRJ\3Dmine\2022\common\cui\test_mine.py",
    r"E:\gzRJ\3Dmine\2022\common\cui\3dmine_profile_chinese\00_标准界面\test_mine.py",
]
for t in targets:
    os.makedirs(os.path.dirname(t), exist_ok=True)
    open(t, "w", encoding="utf-8").write(s)
    compile(s, t, "exec")
    print("deployed+compile ok:", t)
