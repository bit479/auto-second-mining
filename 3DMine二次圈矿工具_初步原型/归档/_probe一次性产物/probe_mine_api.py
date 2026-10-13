# -*- coding: utf-8 -*-
"""探测 3DMine 内嵌 Python API（mine.pyd）能否在 3DMine 进程外导入。

用法（用 3DMine 自带 python39 运行）：
  E:\gzRJ\3DMine\2023\3DMine V202310\3DMine V202310\common\python\x64\python.exe probe_mine_api.py
"""
from __future__ import annotations

import os
import sys
import traceback

BASE = r"E:\gzRJ\3DMine\2023\3DMine V202310\3DMine V202310"
BIN = os.path.join(BASE, "bin", "nt_x64")


def main() -> None:
    print("python:", sys.version.replace("\n", " "))
    print("exe   :", sys.executable)
    print("cwd   :", os.getcwd())
    for extra in (BIN, os.path.join(BASE, "bin"), BASE):
        os.environ["PATH"] = extra + os.pathsep + os.environ["PATH"]
    try:
        os.add_dll_directory(BIN)
        print("add_dll_directory ok:", BIN)
    except Exception as exc:  # pragma: no cover - diagnostics only
        print("add_dll_directory fail:", exc)
    os.chdir(BIN)
    sys.path.insert(0, BIN)
    try:
        import mine  # noqa: PLC0415
    except Exception:
        print("IMPORT_FAILED")
        traceback.print_exc()
        return
    names = [n for n in dir(mine) if not n.startswith("_")]
    print("IMPORT_OK count=%d" % len(names))
    print("\n".join(names))


if __name__ == "__main__":
    main()
