# -*- coding: utf-8 -*-
"""一键验收（改完代码跑这一条就够）：

  python accept_all.py            # 缺省 3940 3960
  python accept_all.py 3940       # 只跑 3940

三件事：
  ① 圈矿验收闸门（`selftest.py`，两档：常规 / 严格）
  ② 报告口径回归（`report_check_all.py`，版式 + 每块自洽 + 合计对账）
  ③ 精确模式自检（用人工导出的四段 .3ds 拼矿界，与人工 1008 图求 IoU）

退出码 0 = 全过；1 = 有退化。每一步的输出原样打出来（不吞日志）。
"""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROBE = ROOT / "_probe"
sys.path.insert(0, str(ROOT / "core")); sys.path.insert(0, str(PROBE))
try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

PLATS = [a for a in sys.argv[1:] if not a.startswith("-")] or ["3940", "3960"]
results = []


def run(name, args, ok_when=None):
    print("")
    print("=" * 78)
    print("== %s" % name)
    print("=" * 78)
    p = subprocess.run([sys.executable, "-X", "utf8"] + [str(a) for a in args],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (p.stdout or "") + (p.stderr or "")
    print(out.rstrip())
    ok = (p.returncode == 0) if ok_when is None else ok_when(p.returncode, out)
    results.append((name, ok, p.returncode))
    return out


def check_exact():
    """精确模式自检：人工四段 .3ds 拼出的矿界 vs 人工 1008 图，要求 IoU ≥ 0.9。"""
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    from oreblocks import load_holes_xls
    import baseline as _bl
    import strip as S
    D = Path(r"C:\Users\Administrator\Desktop")
    parts = ["左边界，已外推3m.3ds", "与综合图边界.3ds", "右边界，已外推3m.3ds",
             "连接辅助线中点形成右上边界.3ds"]
    missing = [n for n in parts if not (D / n).exists()]
    if missing:
        return None, "人工导出的样例文件不在桌面（%s），跳过" % "、".join(missing)
    ring = S.ring_from_outline_files([D / n for n in parts])
    if ring is None:
        return False, "拼不出矿界"
    day = ROOT.parent / "北部山头3940平台2026"
    folder = [d for d in (day / "7、单日数据").iterdir() if d.is_dir() and d.name.endswith("1008")][0]
    holes = load_holes_xls(sorted(folder.glob("1、*.xls"))[0])
    allh = list(holes.values())
    j = json.loads(_bl.scan_path("3940", "1008").read_text(encoding="utf-8"))
    mb = [Polygon(p["pts"]).buffer(0) for p in j["polylines"]
          if p["layer"] not in {"爆区方格网", "钻孔", "点", "线条", "孔口文字"}
          and len(p["pts"]) >= 3 and _bl.is_block(Polygon(p["pts"]).buffer(0), p["layer"], allh)]
    man = unary_union(mb)
    iou = ring.intersection(man).area / ring.union(man).area
    return (iou >= 0.9), "精确模式拼出的矿界 %.1f m²，与人工 1008 图 IoU %.4f（门槛 0.90）" % (ring.area, iou)


run("① 圈矿验收闸门（selftest.py，两档）", [PROBE / "selftest.py"] + PLATS)
if "3940" in PLATS:
    run("② 报告口径回归（report_check_all.py）", [PROBE / "report_check_all.py", "3940"])
print("")
print("=" * 78)
print("== ③ 精确模式自检（人工四段 .3ds 拼矿界）")
print("=" * 78)
try:
    ok3, msg3 = check_exact()
    print(msg3)
    if ok3 is not None:
        results.append(("③ 精确模式自检", ok3, 0 if ok3 else 1))
except Exception as exc:
    print("自检异常：%s" % exc)
    results.append(("③ 精确模式自检", False, 1))

print("")
print("=" * 78)
print("== 汇总")
print("=" * 78)
for name, ok, rc in results:
    print("  %-40s %s%s" % (name, "通过" if ok else "**没通过**",
                            "" if ok else "（退出码 %s）" % rc))
bad = [r for r in results if not r[1]]
print("")
if bad:
    print("结论：有 %d 项没通过：%s" % (len(bad), "、".join(b[0] for b in bad)))
    sys.exit(1)
print("结论：一键验收全部通过 ✓")
