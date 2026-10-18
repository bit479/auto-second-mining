# -*- coding: utf-8 -*-
# 看 N CR 1018 三个 .3ds 的结构：几条线、每条是否闭合、端点能不能串起来。
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))
from strip import read_3ds_polylines  # noqa: E402

D = Path(r"C:\Users\Administrator\Desktop\N CR 1018")


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


for name in ("N CR 1018未闭合线.3ds", "N CR 1018未闭合线NEW.3ds", "N CR 1018闭合线.3ds"):
    p = D / name
    if not p.exists():
        print("(缺) %s" % name)
        continue
    lines = read_3ds_polylines(p)
    print("=" * 70)
    print("%s → %d 条折线" % (name, len(lines)))
    for i, pts in enumerate(lines, 1):
        gap = dist(pts[0], pts[-1])
        print("  #%d: %d 点  首(%.2f,%.2f)  末(%.2f,%.2f)  首末距 %.2f m %s"
              % (i, len(pts), pts[0][0], pts[0][1], pts[-1][0], pts[-1][1], gap,
                 "（闭合）" if gap < 0.05 else ""))
