# -*- coding: utf-8 -*-
"""在 3DMine 安装目录里按多种编码查找关键字符串，定位"函数未注册"的来源。

用法: python find_strings.py <dir> <关键词1> [关键词2 ...]
"""
from __future__ import annotations

import sys
from pathlib import Path


def variants(s: str):
    out = [("gbk", s.encode("gbk", "ignore")),
           ("utf16le", s.encode("utf-16-le")),
           ("ascii", s.encode("ascii", "ignore"))]
    return [(n, b) for n, b in out if b]


def main() -> None:
    root = Path(sys.argv[1])
    keys = sys.argv[2:]
    exts = {".dll", ".exe", ".pyd", ".py", ".xml", ".ini", ".txt"}
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in exts:
            continue
        try:
            data = p.read_bytes()
        except Exception:
            continue
        for k in keys:
            for name, pat in variants(k):
                i = data.find(pat)
                if i < 0:
                    continue
                ctx = data[max(0, i - 60): i + 80]
                try:
                    shown = ctx.decode("gbk", "replace")
                except Exception:
                    shown = repr(ctx)
                print("== %s  [%s/%s] @%d" % (p, k, name, i))
                print("   %s" % shown.replace("\r", " ").replace("\n", " "))


if __name__ == "__main__":
    main()
