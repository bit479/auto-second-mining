# -*- coding: utf-8 -*-
"""从 3DMine 的 DLL 里抽取可打印字符串，用于判断有哪些可用接口名。

只读，不修改任何文件。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

BIN2022 = Path(r"E:\gzRJ\3Dmine\2022\bin\nt_x64")
BIN2023 = Path(r"E:\gzRJ\3DMine\2023\3DMine V202310\3DMine V202310\bin\nt_x64")

KEYWORDS = (
    "Voronoi", "voronoi", "OreBlock", "oreblock", "OreZone", "oreZone",
    "DrillHole", "drillhole", "PitBlast", "pitblast", "Blast",
    "Grade", "grade", "Sample", "Polygon", "Union", "Intersect",
)


def strings(path: Path, min_len: int = 6):
    data = path.read_bytes()
    for m in re.finditer(rb"[\x20-\x7e]{%d,}" % min_len, data):
        yield m.group(0).decode("ascii", "replace")


def main() -> None:
    targets = []
    for base in (BIN2022, BIN2023):
        for name in ("MineDrillHole.Dll", "Module_18_OpenPit_Blast.dll",
                     "Module_22_PitBlast_Database.dll", "MineDB.dll",
                     "MineApi.dll", "mine.pyd"):
            p = base / name
            if p.exists():
                targets.append(p)

    seen = set()
    for p in targets:
        hits = []
        for s in strings(p):
            if any(k in s for k in KEYWORDS):
                if s not in seen:
                    seen.add(s)
                    hits.append(s)
        print("=" * 70)
        print("%s  (%d bytes)  hits=%d" % (p, p.stat().st_size, len(hits)))
        for s in sorted(set(hits))[:400]:
            print("   ", s)


if __name__ == "__main__":
    main()
    sys.stdout.flush()
