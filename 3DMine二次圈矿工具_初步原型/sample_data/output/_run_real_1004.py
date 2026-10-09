# -*- coding: utf-8 -*-
"""运行真实 1004 xls 数据（subprocess 方式，规避 cmd 中文路径引号问题）。"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型")
xls = Path(r"D:\WK\N CRT\北部山头3940平台2026\7、单日数据\北部山头3940平台-1004\1、3940平台 炮孔数据库1004.xls")

r = subprocess.run(
    [sys.executable, "-X", "utf8", "main.py", "--csv", str(xls)],
    cwd=str(ROOT), capture_output=True, encoding="utf-8", errors="replace",
)
print("EXIT:", r.returncode)
print(r.stdout)
if r.stderr:
    print("--- STDERR ---")
    print(r.stderr[:4000])
