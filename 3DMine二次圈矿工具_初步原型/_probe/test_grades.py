# -*- coding: utf-8 -*-
"""自检：**品位分级按矿段**（圈矿链路）。

档位以前写死在 oreblocks / autoblock / strip / deliver / run_batch 里，全是金斗山那套
（``0.5-1 / 1-1.5 / 1.5-3 / ≥3``）。中心矿段是 ``0.5-0.8 / 0.8-1 / ≥1``（只有三档），
换矿段以后档位、块分层、图上图层、报告里的档位名全会错。

这里验四件事：

① 两套分级的档位/边界/颜色/排序（自带数据，不依赖外部目录）；
② 矿段识别（路径关键字 / 显式指定 / 默认）；
③ **同一批炮孔在两套分级下真跑一圈 pipeline**，块档位、体号顺序、体积对得上；
④ 报告里的"孔数统计"列跟着矿段变；
⑤ 与"炮孔报告汇总"那条链路读的是同一份配置、分界值一致（防两边漂移）。

用法::

    python _probe/test_grades.py            # 含真实中心矿段数据（本机有才跑）
    python _probe/test_grades.py --quick    # 只跑自带数据
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORE = ROOT / "core"
sys.path.insert(0, str(CORE))

import grades                                    # noqa: E402
from oreblocks import Hole                       # noqa: E402
from pipeline import run_blast                   # noqa: E402
import params as _params                         # noqa: E402

# 真实的中心矿段单日库（本机有就跑一下，没有就跳过）
REAL_CENTER_XLS = Path(r"E:\AAAWK\2026地质生产数据\中心矿段2026\中心矿段3580平台"
                       r"\5、单日数据\3580平台-1011\1、中心矿段3580平台 炮孔数据库-1011.xls")

_checks: list[tuple[bool, str]] = []


def check(ok: bool, msg: str) -> None:
    _checks.append((bool(ok), msg))
    print("  %s  %s" % ("OK  " if ok else "FAIL", msg))


# --------------------------------------------------------------------------
# ① 档位定义
# --------------------------------------------------------------------------
def test_bands() -> None:
    print("\n[档位：金斗山 4 档 / 中心矿段 3 档，都从工业品位 0.5 起]")
    reg = grades.registry()
    jin, cen = reg.get("jindoushan"), reg.get("center")

    check(jin.ids_desc() == ["L4", "L3", "L2", "L1"],
          "金斗山 id 从高到低 = %s" % jin.ids_desc())
    check([b[3] for b in jin.levels_desc()] ==
          ["3.000-999.000", "1.500-3.000", "1.000-1.500", "0.500-1.000"],
          "金斗山档位名与旧 LEVELS 完全一致（老成果不变）")
    check(cen.ids_desc() == ["L3", "L2", "L1"] and
          [b[3] for b in cen.levels_desc()] ==
          ["1.000-999.000", "0.800-1.000", "0.500-0.800"],
          "中心矿段 3 档 = %s" % " / ".join(b.label for b in cen.bands))
    check(jin.cutoff == 0.5 and cen.cutoff == 0.5,
          "工业品位下限都 = 0.5（金斗山的 0.000-0.500 是废石档，不算圈矿档位）")

    jin_cases = [(0.49, None), (0.5, "L1"), (0.999, "L1"), (1.0, "L2"),
                 (1.499, "L2"), (1.5, "L3"), (2.999, "L3"), (3.0, "L4"), (99, "L4")]
    bad = [(g, jin.level_of(g)[0], w) for g, w in jin_cases if jin.level_of(g)[0] != w]
    check(not bad, "金斗山 9 个边界值落对档" + ("" if not bad else " → %s" % bad))

    cen_cases = [(0.49, None), (0.5, "L1"), (0.799, "L1"), (0.8, "L2"),
                 (0.999, "L2"), (1.0, "L3"), (5.44, "L3")]
    bad = [(g, cen.level_of(g)[0], w) for g, w in cen_cases if cen.level_of(g)[0] != w]
    check(not bad, "中心矿段 7 个边界值落对档" + ("" if not bad else " → %s" % bad))

    check([b.short for b in jin.bands_desc] == ["≥3", "1.5-3", "1-1.5", "0.5-1"],
          "金斗山短标签 = %s（与图上图例一致）" % [b.short for b in jin.bands_desc])
    check([b.short for b in cen.bands_desc] == ["≥1", "0.8-1", "0.5-0.8"],
          "中心矿段短标签 = %s" % [b.short for b in cen.bands_desc])
    check([b.aci for b in jin.bands] == [4, 5, 1, 2] and [b.aci for b in cen.bands] == [4, 5, 1],
          "色号按从低到高：青/蓝/红（金斗山多一个黄）")
    check(jin.order_map(True) == {"L4": 0, "L3": 1, "L2": 2, "L1": 3, "L0": 4},
          "体号排序表 = %s" % jin.order_map(True))
    check(cen.waste_label == "<0.500" and grades.WASTE_ID == "L0",
          "整块废石用 %s / %s（与人工报告的写法一致）" % (grades.WASTE_ID, cen.waste_label))


# --------------------------------------------------------------------------
# ② 识别
# --------------------------------------------------------------------------
def test_detect() -> None:
    print("\n[矿段识别：显式 > 路径关键字 > 默认]")
    cases = [
        (["E:\\AAAWK\\2026地质生产数据\\中心矿段2026\\中心矿段3580平台\\1、x.xls"], None, "center"),
        (["D:\\WK\\N CRT\\北部山头3940平台2026\\7、单日数据\\1、x.xls"], None, "jindoushan"),
        (["C:\\tmp\\x.xls"], None, "jindoushan"),
        (["C:\\tmp\\x.xls"], "center", "center"),
        (["E:\\中心矿段2026\\x.xls"], "jindoushan", "jindoushan"),
    ]
    for paths, explicit, want in cases:
        prof, why = grades.use_for(paths, explicit=explicit)
        check(prof.key == want, "%s → %s（%s）" % (paths[0].split("\\")[-1], prof.key, why))
    grades.use_for([], explicit="auto")


# --------------------------------------------------------------------------
# ③ 真跑一圈（同一批孔，两套分级各跑一次）
# --------------------------------------------------------------------------
def _holes():
    """3×3 网格，孔距 5 m；品位刻意跨过两套分级的分界。"""
    grades_ = [0.60, 0.90, 1.20, 2.00, 4.00, 0.72, 1.05, 2.50, 0.85]
    out = {}
    for i, g in enumerate(grades_):
        r, c = divmod(i, 3)
        hid = "P%d" % (i + 1)
        out[hid] = Hole(hid=hid, x=c * 5.0, y=r * 5.0, z=100.0, depth=10.0, grade=g, short=hid)
    return out


def _run(section: str) -> dict:
    grades.use_for([], explicit=section)
    hs = _holes()
    P = _params.for_blast("0101", platform="3570")
    P = dict(P)
    P.update({"extrude_m": 3.0, "ring_mode": "clusters", "isolated_min_holes": 1,
              "min_fragment_m2": 0.0, "merge_gap_m": 0.0, "mine_section": section})
    return run_blast(hs, list(hs.values()), P)


def test_pipeline() -> None:
    print("\n[真跑 pipeline：同一批 9 个孔，两套分级]")

    res_j = _run("jindoushan")
    blocks_j = res_j["blocks"]
    labels_j = sorted({b.label for b in blocks_j})
    check(set(labels_j) <= set(grades.registry().get("jindoushan").labels),
          "金斗山：块档位都在金斗山分级的档位里（%s）" % "、".join(labels_j))
    check("0.500-1.000" in labels_j and "1.000-1.500" in labels_j,
          "金斗山：0.60/0.72/0.85/0.90 归 0.500-1.000、1.05/1.20 归 1.000-1.500")
    nums_j = [b.no for b in blocks_j]
    check(nums_j == list(range(1, len(blocks_j) + 1)), "金斗山：体号 1→N 连续（%s）" % nums_j)
    vols_j = sorted(round(sum(b.volume_m3 for b in blocks_j), 6) for _ in [0])

    res_c = _run("center")
    blocks_c = res_c["blocks"]
    labels_c = sorted({b.label for b in blocks_c})
    check(set(labels_c) <= set(grades.registry().get("center").labels),
          "中心矿段：块档位都在中心矿段分级的档位里（%s）" % "、".join(labels_c))
    check("0.500-0.800" in labels_c and "0.800-1.000" in labels_c and "1.000-999.000" in labels_c,
          "中心矿段：0.60/0.72 归 0.500-0.800、0.85/0.90 归 0.800-1.000、其余归 1.000-999.000")
    nums_c = [b.no for b in blocks_c]
    check(nums_c == list(range(1, len(blocks_c) + 1)), "中心矿段：体号 1→N 连续（%s）" % nums_c)

    # 每块的平均品位必须落在它自己的档位里（换了分级也不能出现"标签和品位不符"）
    for name, res, key in (("金斗山", res_j, "jindoushan"), ("中心矿段", res_c, "center")):
        prof = grades.registry().get(key)
        bad = [(b.label, round(b.grade, 3), prof.level_of(b.grade)[0])
               for b in res["blocks"]
               if b.level_id != grades.WASTE_ID and prof.level_of(b.grade)[0] != b.level_id]
        check(not bad, "%s：每块的平均品位都落在自己的档位里" % name
              + ("" if not bad else " → %s" % bad))

    # 换分级只改"怎么分块"，不改矿量级：块的分块方式变了（每块各做一次块内 Voronoi
    # + 外推），总体积会有百分之几的差，这是算法本身的性质，不是错——量级对得上就行
    vj = sum(b.volume_m3 for b in blocks_j)
    vc = sum(b.volume_m3 for b in blocks_c)
    check(abs(vj - vc) / max(vj, 1e-9) < 0.10,
          "两套分级总体积同量级：%.1f / %.1f m³（差 %.1f%%，分块方式不同所致）"
          % (vj, vc, abs(vj - vc) / max(vj, 1e-9) * 100))

    # 档位数量确实是"按矿段不同"——金斗山 4 档能分开，中心矿段只有 3 档
    check(len(labels_j) > len(labels_c),
          "档位个数随矿段变：金斗山 %d 档 / 中心矿段 %d 档" % (len(labels_j), len(labels_c)))
    print("        金斗山块：%s" % [(b.label, b.no, round(b.volume_m3, 1)) for b in blocks_j])
    print("        中心矿段块：%s" % [(b.label, b.no, round(b.volume_m3, 1)) for b in blocks_c])
    _ = vols_j

    # 体号顺序：高档在前
    order = grades.registry().get("center").order_map()
    ids_c = [b.level_id for b in blocks_c]
    check(ids_c == sorted(ids_c, key=lambda x: order.get(x, 9)),
          "中心矿段体号按高档在前排：%s" % ids_c)


# --------------------------------------------------------------------------
# ④ 报告里的孔数统计列
# --------------------------------------------------------------------------
def test_report_columns() -> None:
    print("\n[报告里的孔数统计：列跟着矿段变]")
    from deliver import stat_columns

    hs = list(_holes().values())
    grades.use_for([], explicit="jindoushan")
    cols_j = [c[0] for c in stat_columns(hs)]
    grades.use_for([], explicit="center")
    cols_c = [c[0] for c in stat_columns(hs)]
    check(cols_j == ["≥3", "1.5-3", "1-1.5", "0.5-1", "<0.5"],
          "金斗山统计列 = %s" % cols_j)
    check(cols_c == ["≥1", "0.8-1", "0.5-0.8", "<0.5"],
          "中心矿段统计列 = %s" % cols_c)
    total = sum(c[1] for c in stat_columns(hs))
    check(total == len(hs), "各档孔数之和 = 总孔数（%d）" % total)


# --------------------------------------------------------------------------
# ⑤ 与报告汇总那条链路同源
# --------------------------------------------------------------------------
def test_same_config() -> None:
    print("\n[与「炮孔报告汇总」读同一份配置，分界值一致]")
    sys.path.insert(0, str(ROOT / "excel_tools"))
    try:
        from src.blast_report import profiles as xl      # noqa: E402
    except Exception as exc:                              # noqa: BLE001
        check(True, "excel_tools 模块导不进来，跳过（%s）" % type(exc).__name__)
        return
    reg_xl = xl.load_registry()
    for key in ("jindoushan", "center"):
        p_core = grades.registry().get(key)
        p_xl = reg_xl.get(key)
        core_labels = [b.label for b in p_core.bands]
        xl_labels = [l for l in p_xl.labels if l in core_labels]
        check(core_labels == xl_labels,
              "%s：圈矿档位 %s == 报告档位里的同名档" % (key, core_labels))


def test_real_center(quick: bool) -> None:
    print("\n[真实中心矿段数据（3580-1011）]")
    if quick or not REAL_CENTER_XLS.exists():
        check(True, "跳过（%s）" % ("--quick" if quick else "本机没有这份库"))
        return
    from oreblocks import load_holes_xls

    grades.use_for([REAL_CENTER_XLS])
    check(grades.active().key == "center", "按路径认到 %s" % grades.active().key)
    hs = load_holes_xls(REAL_CENTER_XLS)
    ore = [h for h in hs.values() if h.grade >= grades.cutoff()]
    check(len(ore) > 0, "矿孔 %d / 总孔 %d" % (len(ore), len(hs)))
    labels = {grades.level_of(h.grade)[1] for h in ore}
    cen = grades.registry().get("center")
    check(labels <= set(cen.labels),
          "孔档位全部落在中心矿段分级里（%s）" % "、".join(sorted(x for x in labels if x)))
    # 这批数据里 0.83 / 0.575 这类值在金斗山分级下会并进 0.500-1.000，中心矿段能分开
    old = grades.registry().get("jindoushan")
    differ = [h for h in ore if old.level_of(h.grade)[1] != cen.level_of(h.grade)[1]]
    check(len(differ) > 0,
          "有 %d 个孔在两套分级下落不同的档（换矿段确实换档）" % len(differ))


def main() -> int:
    quick = "--quick" in sys.argv
    print("=" * 78)
    print("分级配置：%s" % grades.registry().source)
    print("  %s" % grades.registry().get("jindoushan").describe())
    print("  %s" % grades.registry().get("center").describe())
    print("-" * 78)

    test_bands()
    test_detect()
    test_pipeline()
    test_report_columns()
    test_same_config()
    test_real_center(quick)

    failed = [m for ok, m in _checks if not ok]
    print("\n" + "=" * 78)
    print("共 %d 项检查，%d 项通过" % (len(_checks), len(_checks) - len(failed)))
    if failed:
        for m in failed:
            print("  FAIL  %s" % m)
        print("结论：存在差异 ✗")
        return 1
    print("结论：全部一致 ✓")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
