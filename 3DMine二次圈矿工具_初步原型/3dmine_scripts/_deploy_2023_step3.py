# -*- coding: utf-8 -*-
"""重新部署（双日志版）宏到 2023 版 3DMine 的 3 个位置。"""
import os

root = r"E:\gzRJ\3Dmine\2023\3DMine V202310免安装程序\3DMine V202310免安装程序"
SRC = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\3dmine_scripts\mine_1004_macro.py"
s = open(SRC, encoding="utf-8").read()

targets = [
    os.path.join(root, "common", "test_mine.py"),
    os.path.join(root, "common", "cui", "test_mine.py"),
    os.path.join(root, "common", "cui", "3dmine_profile_chinese", "00_标准界面", "test_mine.py"),
]
for t in targets:
    open(t, "w", encoding="utf-8").write(s)
    compile(s, t, "exec")
    print("deployed:", t)
