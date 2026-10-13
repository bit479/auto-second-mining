# -*- coding: utf-8 -*-
"""屏幕截图小工具（读屏，不改动任何业务数据）。

用法: python shot.py <输出png> [x y w h]
"""
from __future__ import annotations

import ctypes
import sys
from pathlib import Path

from PIL import ImageGrab


def main() -> None:
    out = Path(sys.argv[1])
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass
    if len(sys.argv) >= 6:
        box = tuple(int(v) for v in sys.argv[2:6])
        img = ImageGrab.grab(bbox=box)
    else:
        img = ImageGrab.grab()
    img.save(out)
    print("saved %s  size=%s" % (out, img.size))


if __name__ == "__main__":
    main()
