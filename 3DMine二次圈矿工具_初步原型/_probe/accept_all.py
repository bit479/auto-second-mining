# -*- coding: utf-8 -*-
"""一键验收（改完代码跑这一条就够）：

  python accept_all.py                # 缺省 3940 3960，全炮区
  python accept_all.py 3940           # 只跑 3940
  python accept_all.py --quick        # 成果图自检只挑代表炮区（快）

四件事：
  ① 圈矿验收闸门（`selftest.py`，两档：常规 / 严格）
  ② 报告口径回归（`report_check_all.py`，版式 + 每块自洽 + 合计对账）
  ③ 成果图实体自检（`dxf_check.py`，图上要素逐条验；全炮区，--quick 时只挑代表）
  ④ 精确模式自检（用人工导出的四段 .3ds 拼矿界，与人工 1008 图求 IoU）

跑完把全过程写进 `验收报告.md`（覆盖），退出码 0 = 全过。
"""
from __future__ import annotations
import datetime as _dt
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

QUICK = "--quick" in sys.argv
PLATS = [a for a in sys.argv[1:] if not a.startswith("-")] or ["3940", "3960"]
QUICK_CASES = {"3940": ["1004", "0915"], "3960": ["0919", "0908"]}
results, logbuf = [], []


def emit(s=""):
    print(s)
    logbuf.append(s)


def run(name, args, gate: bool = True):
    emit("")
    emit("=" * 78)
    emit("== %s" % name)
    emit("=" * 78)
    p = subprocess.run([sys.executable, "-X", "utf8"] + [str(a) for a in args],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = ((p.stdout or "") + (p.stderr or "")).rstrip()
    emit(out)
    ok = p.returncode == 0
    if gate:
        results.append((name, ok, p.returncode))
    else:
        emit("（这一项只作参考，不计入结论：%s）" % ("数字对得上" if ok else "有出入，见上"))
    return out


def scan_dates(plat):
    """该平台有"人工图扫描"的炮区号（＝闸门覆盖的那些）。"""
    import baseline as _bl
    day = ROOT.parent / ("北部山头%s平台2026" % plat)
    out = []
    for d in sorted(x for x in (day / "7、单日数据").iterdir() if x.is_dir()):
        from run_batch import parse_folder
        date = parse_folder(d.name)[1]
        if date and _bl.scan_path(plat, date).exists():
            out.append(date)
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
if "3960" in PLATS:
    # 3960 的人工报告与人工图本身对不上（用户 2026-10-13 定"以图为准"），
    # 所以这一档只打印参考、不作为闸门。
    run("② 报告口径回归（3960，仅参考：该平台人工报告与人工图对不上，口径以图为准）",
        [PROBE / "report_check_all.py", "3960"], gate=False)

cases = []
for p in PLATS:
    ds = scan_dates(p)
    cases += [(p, d) for d in (QUICK_CASES.get(p, []) if QUICK else ds)]
if cases:
    for p, d in cases:
        run("③ 成果图实体自检 %s-%s" % (p, d), [PROBE / "dxf_check.py", p, d, "--fresh"])
    ok3 = all(ok for n, ok, _ in results if n.startswith("③ "))
    results.append(("③ 成果图实体自检（%d 个炮区%s）" % (len(cases), "，快检" if QUICK else "，全量"),
                    ok3, 0 if ok3 else 1))

emit("")
emit("=" * 78)
emit("== ④ 精确模式自检（人工四段 .3ds 拼矿界）")
emit("=" * 78)
try:
    ok4, msg4 = check_exact()
    emit(msg4)
    if ok4 is not None:
        results.append(("④ 精确模式自检", ok4, 0 if ok4 else 1))
except Exception as exc:
    emit("自检异常：%s" % exc)
    results.append(("④ 精确模式自检", False, 1))

# ⑤ 整合进来的"Excel 工具"（炮孔数据工具）自己的自检
XL = ROOT / "excel_tools"
if XL.exists():
    xl_ok = True
    for name, script in (("报告汇总(total口径)", "tests/test_by_total.py"),
                         ("报告汇总(detail口径)", "tests/test_merge.py"),
                         ("单日数据并入总表", "tests/test_daily_merge.py"),
                         ("xls/xlsx 格式自适应", "tests/test_formats.py"),
                         ("文件占用检测", "tests/test_locks.py")):
        p = subprocess.run([sys.executable, "-X", "utf8", str(XL / script)],
                           cwd=str(XL), capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        out = ((p.stdout or "") + (p.stderr or "")).rstrip()
        emit("")
        emit("== ⑤ Excel 工具自检：%s" % name)
        emit(out.splitlines()[-1] if out else "(没有输出)")
        xl_ok = xl_ok and p.returncode == 0
    results.append(("⑤ Excel 工具自检（5 项）", xl_ok, 0 if xl_ok else 1))

# ⑥ 数据库生成：TXT 坐标 + 粘贴品位表 -> xls/mdb
mkdb = PROBE / "test_make_database.py"
if mkdb.exists():
    p = subprocess.run([sys.executable, "-X", "utf8", str(mkdb)],
                       capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    out = ((p.stdout or "") + (p.stderr or "")).rstrip()
    emit("")
    emit("== ⑥ 数据库生成自检（TXT + 品位表）")
    emit(out.splitlines()[-1] if out else "(没有输出)")
    results.append(("⑥ 数据库生成（TXT + 品位表）", p.returncode == 0, p.returncode))

emit("")
emit("=" * 78)
emit("== 汇总")
emit("=" * 78)
for name, ok, rc in results:
    emit("  %-44s %s%s" % (name, "通过" if ok else "**没通过**",
                           "" if ok else "（退出码 %s）" % rc))
bad = [r for r in results if not r[1]]
emit("")
emit("结论：%s" % ("全部通过 ✓" if not bad else
                  "有 %d 项没通过：%s" % (len(bad), "、".join(b[0] for b in bad))))

# 落一份报告
def git_head():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT),
                              capture_output=True, text=True).stdout.strip()
    except Exception:
        return ""

head = ["# 验收报告（自动生成）", "",
        "- 时间：%s" % _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "- 代码版本：`%s`" % git_head(),
        "- 平台：%s  模式：%s" % ("、".join(PLATS), "快检" if QUICK else "全量"),
        "- 结论：**%s**" % ("全部通过 ✓" if not bad else "有 %d 项没通过" % len(bad)),
        "", "| 项 | 结果 |", "|---|---|"]
for name, ok, rc in results:
    head.append("| %s | %s |" % (name, "通过" if ok else "没通过（退出码 %s）" % rc))
head += ["", "---", "", "```text"]
report = ROOT / "验收报告.md"
report.write_text("\n".join(head + logbuf + ["```"]) + "\n", encoding="utf-8")
print("\n报告已写入：%s" % report)
if "--open" in sys.argv and "--no-open" not in sys.argv:   # 给 .bat 用：跑完直接把报告打开
    try:
        import os
        os.startfile(str(report))
    except Exception as exc:
        print("（打开报告失败：%s）" % exc)
sys.exit(1 if bad else 0)
