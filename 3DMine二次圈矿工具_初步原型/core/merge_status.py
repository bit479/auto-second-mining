# -*- coding: utf-8 -*-
"""检查哪些炮区的矿块**已经并入综合图**（用几何重合度判，不靠人工记录）。

用法: python merge_status.py <父目录> <综合图.dwg>

判据：把该炮区自动圈出来的每个矿块，拿去跟综合图里已有的多边形比——
若某个综合图多边形与它的重叠率达到 ≥80%，就算"这块已经并进去了"。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from oreblocks import load_holes_xls                        # noqa: E402
from pipeline import run_blast                              # noqa: E402
from composite import load_composite_blocks                 # noqa: E402
import params as _params                                    # noqa: E402
from run_batch import parse_folder                          # noqa: E402

MATCH = 0.80        # 重叠率达到这个数就算并进去了


def day_status(folder: Path, comp) -> tuple:
    """返回 (日期, 已并入块数, 总块数, 详情)。"""
    xls = sorted(folder.glob("1、*.xls")) or sorted(folder.glob("*.xls"))
    if not xls:
        return None
    xls = xls[0]
    plat, date = parse_folder(folder.name)
    if not date:
        plat, date = parse_folder(xls.name)
    holes = load_holes_xls(xls)
    res = run_blast(holes, list(holes.values()), _params.for_blast(date), comp, blast=date)
    done, detail = 0, []
    for b in res["blocks"]:
        if b.polygon is None or b.polygon.is_empty:
            continue
        best = 0.0
        for layer, _c, poly in comp:
            if poly is None or poly.is_empty or not poly.intersects(b.polygon):
                continue
            inter = poly.intersection(b.polygon).area
            best = max(best, inter / max(b.polygon.area, 1e-9))
        done += int(best >= MATCH)
        detail.append("%d号%.0f%%" % (b.no, best * 100))
    return date, done, len(res["blocks"]), " ".join(detail)


def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__)
        return
    parent, comp_dwg = Path(sys.argv[1]), Path(sys.argv[2])
    comp = load_composite_blocks(comp_dwg)
    print("综合图里已有 %d 个多边形" % len(comp))
    print("%-8s %-12s %s" % ("炮区", "已并入/总块", "各块与综合图的最大重叠率"))
    todo = []
    for f in sorted(d for d in parent.iterdir() if d.is_dir()):
        r = day_status(f, comp)
        if r is None:
            continue
        date, done, total, detail = r
        mark = "✓ 已并入" if done == total and total else "✗ 还有 %d 块没并入" % (total - done)
        print("%-8s %-12s %s   %s" % (date, "%d/%d" % (done, total), detail, mark))
        if done != total:
            todo.append(date)
    if todo:
        print("\n还没并完的炮区：%s" % "、".join(todo))
    else:
        print("\n各炮区都已并入综合图 ✓")


if __name__ == "__main__":
    main()
