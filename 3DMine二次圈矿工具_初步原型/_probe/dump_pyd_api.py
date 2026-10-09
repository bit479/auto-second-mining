# -*- coding: utf-8 -*-
"""从 mine.pyd（Python 扩展模块）里抽取暴露的类/函数名，判断原生 API 能力。

只读。Python 扩展模块的成员名以明文字符串存在于二进制中。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

PYDS = [
    Path(r"E:\gzRJ\3Dmine\2022\bin\nt_x64\mine.pyd"),
    Path(r"E:\gzRJ\3DMine\2023\3DMine V202310\3DMine V202310\bin\nt_x64\mine.pyd"),
    Path(r"E:\gzRJ\3Dmine\3Dmine plus e无限台安装\3DMIN PLUS\bin\nt_x64\mine.pyd"),
]
if len(sys.argv) > 1:
    PYDS = [Path(a) for a in sys.argv[1:]]

PREFIXES = (
    "py", "Py", "Get", "Set", "Add", "Remove", "Create", "Make", "Build",
    "Calc", "Compute", "Drill", "Hole", "Ore", "Grade", "Block", "Zone",
    "Voronoi", "Handle", "Manage", "Select", "Promote", "Print", "Draw",
    "Update", "Import", "Export", "Read", "Write", "Show", "Display",
    "Dialog", "Dlg", "Sample", "Composite", "Table", "Database", "Db",
)


def strings(path: Path, min_len: int = 4):
    data = path.read_bytes()
    for m in re.finditer(rb"[\x20-\x7e]{%d,}" % min_len, data):
        yield m.group(0).decode("ascii", "replace")


def main() -> None:
    for p in PYDS:
        if not p.exists():
            print("MISSING", p)
            continue
        names = set()
        for s in strings(p):
            if "?" in s or "@" in s or ".dll" in s.lower():
                continue
            for token in re.split(r"[^0-9A-Za-z_]+", s):
                if len(token) < 4 or len(token) > 60:
                    continue
                if token.startswith(PREFIXES):
                    names.add(token)
        ordered = sorted(names)
        print("=" * 78)
        print("%s   bytes=%d   候选成员名=%d" % (p, p.stat().st_size, len(ordered)))
        for n in ordered:
            print("   ", n)


if __name__ == "__main__":
    main()
