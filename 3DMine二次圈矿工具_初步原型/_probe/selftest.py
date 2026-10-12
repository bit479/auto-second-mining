# -*- coding: utf-8 -*-
"""验收自检（回归闸门）：拿 5 张人工图当基准，打印自动结果与人工的差距。

用法: python selftest.py [-v]
  退出码 0 = 全部达标；1 = 有指标退化（CI/改代码前后各跑一次）

达标线（1008 是已验收的基线）：
  1008：矿界 IoU ≥ 0.90 且体积差 ≤ ±5%
  其余：矿界 IoU ≥ 0.75 且体积差 ≤ ±20%
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))

from shapely.geometry import Polygon, Point                     # noqa: E402
from shapely.ops import unary_union                            # noqa: E402

from oreblocks import load_holes_xls                           # noqa: E402
from run_strip import pick_zone                                # noqa: E402
from strip import zone_outline, average_blocks, LAST_RING      # noqa: E402
from composite import load_composite_blocks                    # noqa: E402
import params as _params                                       # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DAY = ROOT.parent / "北部山头3940平台2026"
DATA = DAY / "7、单日数据"
COMP = DAY / "5、 北部山头3940平台二次圈矿矿块图-2026综合.dwg"
PROBE = ROOT / "_probe"
SKIP = {"爆区方格网", "钻孔", "点", "线条", "孔口文字"}

# 人工报告里的合计体积（来自各日 3940平台 <日期>炮孔数据报告.xlsx）
MANUAL_VOL = {"0915": 13497.316, "0922": 7075.279, "1003": 9435.031,
              "1004": 9846.363, "1008": 3951.494}
LIMIT = {"1008": (0.90, 0.05)}
DEFAULT_LIMIT = (0.75, 0.20)
DATES = ["0915", "0922", "1003", "1004", "1008"]


def manual_blocks(date):
    f = PROBE / ("manual_%s_c.json" % date)
    if not f.exists():
        return None
    j = json.loads(f.read_text(encoding="utf-8"))
    out = []
    for p in j["polylines"]:
        if p["layer"] in SKIP or len(p["pts"]) < 3:
            continue
        poly = Polygon(p["pts"]).buffer(0)
        if poly.area >= 5.0:
            out.append(poly)
    return unary_union(out) if out else None


def main() -> None:
    verbose = "-v" in sys.argv
    comp = load_composite_blocks(COMP) if COMP.exists() else []
    bad, rows = [], []
    for d in DATES:
        folder = DATA / ("北部山头3940平台-%s" % d)
        xls = sorted(folder.glob("1、*.xls"))
        man_poly = manual_blocks(d)
        if not xls or man_poly is None:
            rows.append((d, "-", "-", "-", "缺数据/缺人工图", False))
            continue
        P = _params.for_blast(d)
        holes = load_holes_xls(xls[0])
        allh = list(holes.values())
        ore, pending = pick_zone(holes, adjacent_max=P["zone_link_m"])
        ring = zone_outline(ore, allh, P["extrude_m"], comp_blocks=comp,
                            merge_gap=P["merge_gap_m"], blast=d,
                            simplify=P["simplify_m"],
                            alpha_k=P.get("ring_alpha_k", 0.0))
        blocks = average_blocks(ore, ring, 2.7, min_fragment=P["min_fragment_m2"])
        iou = ring.intersection(man_poly).area / ring.union(man_poly).area
        tv = sum(b.volume_m3 for b in blocks)
        mv = MANUAL_VOL.get(d)
        dev = (tv - mv) / mv if mv else 0.0
        out_holes = [h.short for h in ore if not ring.contains(Point(h.x, h.y))]
        warn = list(LAST_RING.get("warn") or [])
        note = ("环外孔" + ",".join(out_holes)) if out_holes else \
            ("自检修补:" + "；".join(warn) if warn else "OK")
        if d == "0922":
            note += "  [特殊炮区，不纳入闸门]"
        lim_iou, lim_dev = LIMIT.get(d, DEFAULT_LIMIT)
        ok = iou >= lim_iou and abs(dev) <= lim_dev
        if not ok and d != "0922":
            bad.append(d)
        rows.append((d, "%.3f" % iou, "%d" % len(blocks),
                     "%9.1f / %9.1f (%+5.1f%%)" % (tv, mv or 0, dev * 100),
                     note,
                     ok))
    print("%-6s %-6s %-5s %-30s %s" % ("炮区", "矿界IoU", "块数", "体积(自动/人工)", "备注"))
    for r in rows:
        print("%-6s %-6s %-5s %-30s %s%s" % (r[0], r[1], r[2], r[3], r[4],
                                              "" if r[5] else "   ← 未达标"))
    print()
    if bad:
        print("未达标：%s（阈值 1008 IoU≥0.90 且 ±5%%，其余 IoU≥0.75 且 ±20%%）"
              % "、".join(bad))
        sys.exit(1)
    print("全部达标 ✓")


if __name__ == "__main__":
    main()
