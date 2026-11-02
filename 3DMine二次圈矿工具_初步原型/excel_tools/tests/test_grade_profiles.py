"""自检：**品位分级按矿段取**（金斗山 / 中心矿段各一套）。

覆盖四件事：

1. 两套分级的档位名与边界归属（下限含、上限不含）；
2. 分界值切出来的档位**既不重叠也不留缝**（逐 0.001 扫一遍，每个品位只落一档）；
3. 自动识别：路径关键字 / 源报告档位 → 认到正确的矿段；
4. 同一批数据在两套分级下的汇总结果 —— 中心矿段的 0.55 / 0.75 / 0.90
   在金斗山分级下会被并成 ``0.500-1.000``（这就是修复前的错），
   在中心矿段分级下才是 ``0.500-0.800`` / ``0.800-1.000``。

用法::

    python tests/test_grade_profiles.py

（真实的中心矿段报告若在本机存在，会额外核对"配置档位与报告档位一致"。）
"""

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from openpyxl import load_workbook  # noqa: E402

from src.blast_report import profiles  # noqa: E402
from src.blast_report.builder import MergeOptions, merge_reports  # noqa: E402
from src.blast_report.parser import SourceReport  # noqa: E402
from src.blast_report.schema import band_of_grade, grade_sort_key  # noqa: E402

OUT_DIR = os.path.join(ROOT, "_out")

# 真实数据（有就顺手核对一下，没有就跳过）
REAL_CENTER = (r"E:\AAAWK\2026地质生产数据\中心矿段2026\中心矿段3580平台"
               r"\3、中心矿段3580平台炮孔数据库报告.xlsx")

_checks: list[tuple[bool, str]] = []


def check(ok: bool, message: str) -> None:
    _checks.append((bool(ok), message))
    print("  %s  %s" % ("OK  " if ok else "FAIL", message))


def _registry():
    return profiles.load_registry(reload=True)


# --------------------------------------------------------------------------
# ① 档位与边界
# --------------------------------------------------------------------------

def test_bands() -> None:
    print("\n[档位定义]")
    reg = _registry()
    jin, cen = reg.get("jindoushan"), reg.get("center")

    check(list(jin.labels) == ["0.000-0.500", "0.500-1.000", "1.000-1.500",
                               "1.500-3.000", "3.000-999.000"],
          "金斗山 5 档：%s" % " / ".join(jin.labels))
    check(list(cen.labels) == ["0.500-0.800", "0.800-1.000", "1.000-999.000"],
          "中心矿段 3 档：%s" % " / ".join(cen.labels))
    check(jin.cutoff == 0.0 and cen.cutoff == 0.5,
          "工业品位下限：金斗山 %.1f / 中心矿段 %.1f" % (jin.cutoff, cen.cutoff))

    print("\n[边界归属：下限含、上限不含]")
    jin_cases = [
        (0.0, "0.000-0.500"), (0.4999, "0.000-0.500"),
        (0.5, "0.500-1.000"), (0.9999, "0.500-1.000"),
        (1.0, "1.000-1.500"), (1.4999, "1.000-1.500"),
        (1.5, "1.500-3.000"), (2.9999, "1.500-3.000"),
        (3.0, "3.000-999.000"), (99.0, "3.000-999.000"),
    ]
    bad = [(v, jin.band_of(v), w) for v, w in jin_cases if jin.band_of(v) != w]
    check(not bad, "金斗山 10 个边界值都落对档" + ("" if not bad else " → %s" % bad))

    cen_cases = [
        (0.5, "0.500-0.800"), (0.7999, "0.500-0.800"),
        (0.8, "0.800-1.000"), (0.9999, "0.800-1.000"),
        (1.0, "1.000-999.000"), (8.8, "1.000-999.000"),
    ]
    bad = [(v, cen.band_of(v), w) for v, w in cen_cases if cen.band_of(v) != w]
    check(not bad, "中心矿段 6 个边界值都落对档" + ("" if not bad else " → %s" % bad))

    check(cen.band_of(0.499) == "<0.500",
          "中心矿段 0.499（低于工业品位）单列 <0.500，不并进最低档（实际 %r）"
          % cen.band_of(0.499))
    check(jin.band_of(0.0) == "0.000-0.500", "金斗山 0.000 仍归最低档（旧行为不变）")


def test_no_gap_no_overlap() -> None:
    print("\n[不重叠 / 不留缝：0.000~5.000 逐 0.001 扫一遍]")
    for key, profile in _registry().profiles.items():
        hits: dict[float, list[str]] = {}
        value = 0
        while value <= 5000:
            grade = value / 1000.0
            hits[grade] = [b.label for b in profile.bands if b.contains(grade)]
            value += 1
        multi = [g for g, ls in hits.items() if len(ls) > 1]
        empty = [g for g, ls in hits.items() if not ls and g >= profile.cutoff]
        below = [g for g, ls in hits.items() if not ls and g < profile.cutoff]
        check(not multi, "%s：没有品位落进两个档（重复计数）" % profile.name
              + ("" if not multi else " → %s" % multi[:5]))
        check(not empty, "%s：下限以上的品位没有漏档" % profile.name
              + ("" if not empty else " → %s" % empty[:5]))
        check(all(profile.band_of(g) == profile.underflow_label() for g in below),
              "%s：下限以下 %d 个取值统一落在 %s"
              % (profile.name, len(below), profile.underflow_label()))


def test_sort_order() -> None:
    print("\n[档位排序：由高到低，兜底档排最后]")
    cen = _registry().get("center")
    labels = list(cen.labels) + [cen.underflow_label()]
    ordered = sorted(reversed(labels), key=grade_sort_key)
    check(ordered == ["1.000-999.000", "0.800-1.000", "0.500-0.800", "<0.500"],
          "中心矿段排序 = %s" % " → ".join(ordered))


# --------------------------------------------------------------------------
# ② 自动识别
# --------------------------------------------------------------------------

def test_detect() -> None:
    print("\n[矿段自动识别]")
    reg = _registry()
    cases = [
        (r"E:\AAAWK\2026地质生产数据\中心矿段2026\中心矿段3570平台\5、单日数据\3570-1023\x.xlsx",
         "center", "按路径识别"),
        (r"E:\AAAWK\2026地质生产数据\中心矿段2026\中心矿段3580平台\工作簿1.xlsx",
         "center", "按路径识别"),
        (r"E:\AAAWK\2026地质生产数据\3570取样1023.txt", None, "默认"),        # 文件名没有矿段
        (r"D:\WK\N CRT\北部山头3940平台2026\7、单日数据\北部山头3940平台-1008\工作簿1.xlsx",
         "jindoushan", "按路径识别"),
        (r"C:\Users\Administrator\Desktop\3940平台\1011\工作表1.xls", "jindoushan", "默认"),
    ]
    for path, want, why in cases:
        profile, reason = profiles.resolve_profile(None, [path], (), reg)
        if want is None:
            ok = reason.startswith(why)
        else:
            ok = profile.key == want and reason.startswith(why)
        check(ok, "%s → %s（%s）" % (os.path.basename(path), profile.key, reason))

    # 路径没线索时看源报告里的档位名
    rep = SourceReport(path=r"C:\tmp\a.xlsx")
    rep.records = [type("R", (), {"grade_type": label})()
                   for label in ("1.000-999.000", "0.800-1.000", "0.500-0.800")]
    profile, reason = profiles.resolve_profile(None, [rep.path], [rep], reg)
    check(profile.key == "center", "按源报告档位识别 → %s（%s）" % (profile.key, reason))

    rep.records = [type("R", (), {"grade_type": label})()
                   for label in ("3.000-999.000", "1.500-3.000", "0.500-1.000")]
    profile, reason = profiles.resolve_profile(None, [rep.path], [rep], reg)
    check(profile.key == "jindoushan", "按源报告档位识别 → %s（%s）" % (profile.key, reason))

    profile, reason = profiles.resolve_profile("center", [], [], reg)
    check(profile.key == "center" and reason == "手动指定", "手动指定优先：%s" % reason)


def test_title() -> None:
    print("\n[标题里的矿名：平台标签已带矿段名就不再补默认前缀]")
    from src.blast_report import naming

    cases = [
        (r"E:\AAAWK\2026地质生产数据\中心矿段2026\中心矿段3570平台\5、单日数据\3570-1023\x.xlsx",
         "中心矿段3570平台1023炮孔数据报告"),
        (r"D:\WK\N CRT\北部山头3940平台2026\7、单日数据\北部山头3940平台-1008\工作簿1.xlsx",
         "北部山头3940平台1008炮孔数据报告"),
        (r"C:\Users\Administrator\Desktop\3940平台\1011\工作表1.xls",
         "北部山头3940平台1011炮孔数据报告"),
    ]
    for path, want in cases:
        got = naming.guess_title([path], None)
        check(got == want, "%s → %r" % (os.path.basename(path), got))


# --------------------------------------------------------------------------
# ③ 汇总结果（两套分级各跑一遍）
# --------------------------------------------------------------------------

def _report(path: str, grade: float, volume: float, weight: float) -> SourceReport:
    """造一份"只有总计行"的源报告：金属量 = 重量 × 品位 ÷ 100。"""
    rep = SourceReport(path=path, title="3DMine 炮孔数据库报告",
                       header=["类型", "体号", "体积", "重量", "平均品位(Au)", "金属量（百克）"])
    rep.raw_rows = [["总计", "", volume, weight, grade, weight * grade / 100.0]]
    rep.total_values = {
        "体积": volume, "重量": weight,
        "平均品位(Au)": grade, "金属量": weight * grade / 100.0,
    }
    rep.total_index = 0
    return rep


def _blocks() -> list[SourceReport]:
    """中心矿段一天的 4 个矿块（品位 0.55 / 0.75 / 0.90 / 2.40）。"""
    folder = (r"E:\AAAWK\2026地质生产数据\中心矿段2026\中心矿段3580平台"
              r"\5、单日数据\3580平台-1011")
    specs = [("0.55.xlsx", 0.55, 300.0, 810.0),
             ("0.75.xlsx", 0.75, 280.0, 756.0),
             ("0.90.xlsx", 0.90, 120.0, 324.0),
             ("2.40.xlsx", 2.40, 60.0, 162.0)]
    return [_report(os.path.join(folder, name), grade, vol, wgt)
            for name, grade, vol, wgt in specs]


def _rows(ws) -> list[list]:
    out = []
    for r in range(3, ws.max_row + 1):
        row = [ws.cell(r, c).value for c in range(1, 7)]
        if row[0] in ("小计", "合计") or (isinstance(row[0], str) and "-" in row[0]):
            out.append(row)
        elif row[0] is None and row[1] is None:
            break
    return out


def _merge(options: MergeOptions, tag: str) -> tuple[dict, list[list]]:
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, "分级自检_%s.xlsx" % tag)
    result = merge_reports(_blocks(), out, options)
    ws = load_workbook(out, data_only=False).active
    return result, _rows(ws)


def test_merge_center() -> None:
    print("\n[汇总 · 中心矿段分级]")
    result, rows = _merge(MergeOptions(grade_profile="center", with_appendix=False, use_formula=False), "center")
    check(result["grade_profile"] == "center", "用的分级 = %s（%s）"
          % (result["grade_profile"], result["grade_profile_reason"]))
    check(result["tiers"] == ["1.000-999.000", "0.800-1.000", "0.500-0.800"],
          "档位由高到低 = %s" % " / ".join(result["tiers"]))
    check(result["blocks"] == 4, "4 个矿块")

    types = [r[0] for r in rows if r[0] not in ("小计", "合计")]
    bodies = [r[1] for r in rows if r[0] not in ("小计", "合计")]
    check(types == ["1.000-999.000", "0.800-1.000", "0.500-0.800", "0.500-0.800"],
          "落档 = %s" % " / ".join(types))
    check(bodies == [1, 2, 3, 4], "体号按最终顺序重编 1→N（%s）" % bodies)

    # 0.55 与 0.75 同档，同档内保持源文件顺序
    low = [r for r in rows if r[0] == "0.500-0.800"]
    check(len(low) == 2 and abs(low[0][2] - 300.0) < 1e-6 and abs(low[1][2] - 280.0) < 1e-6,
          "同档内保持源文件顺序（体积 %s / %s）" % (low[0][2], low[1][2]))

    total = [r for r in rows if r[0] == "合计"][0]
    check(abs(total[2] - 760.0) < 1e-6 and abs(total[3] - 2052.0) < 1e-6,
          "合计体积/重量 = %.3f / %.3f（= 各矿块之和）" % (total[2], total[3]))
    check(abs(total[5] - 16.929) < 1e-6,
          "合计金属量 = %.3f 百克（= 各矿块金属量之和，重量×品位÷100）" % total[5])
    check(not [w for w in result["warnings"] if "低于" in w], "没有低于下限的告警")


def test_merge_jindoushan() -> None:
    print("\n[汇总 · 金斗山分级（同一批数据，验证确实是按矿段换档）]")
    result, rows = _merge(MergeOptions(grade_profile="jindoushan", with_appendix=False, use_formula=False), "jin")
    check(result["grade_profile"] == "jindoushan", "用的分级 = %s" % result["grade_profile"])
    check(result["tiers"] == ["1.500-3.000", "0.500-1.000"],
          "金斗山分级下 0.55/0.75/0.90 全并进 0.500-1.000：%s" % " / ".join(result["tiers"]))
    low = [r for r in rows if r[0] == "0.500-1.000"]
    check(len(low) == 3, "0.500-1.000 一档装了 3 个矿块（修复前中心矿段就是这样出错的）")
    check(abs(sum(r[5] for r in low) - 13.041) < 1e-6,
          "该档金属量 %.3f 百克 —— 数据没丢，只是档位归错" % sum(r[5] for r in low))


def test_merge_auto() -> None:
    print("\n[汇总 · 自动识别（路径里带「中心矿段」）]")
    result, _ = _merge(MergeOptions(with_appendix=False, use_formula=False), "auto")
    check(result["grade_profile"] == "center",
          "自动识到 %s（%s）" % (result["grade_profile"], result["grade_profile_reason"]))
    check(result["tiers"] == ["1.000-999.000", "0.800-1.000", "0.500-0.800"],
          "自动识别后档位正确：%s" % " / ".join(result["tiers"]))


def test_below_cutoff() -> None:
    print("\n[低于工业品位下限：单列一档并告警]")
    rep = _report(r"E:\AAAWK\2026地质生产数据\中心矿段2026\中心矿段3580平台\a.xlsx",
                  0.42, 50.0, 135.0)
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, "分级自检_below.xlsx")
    result = merge_reports([rep], out, MergeOptions(grade_profile="center", with_appendix=False, use_formula=False))
    check(result["tiers"] == ["<0.500"], "档位 = %s" % result["tiers"])
    check(any("低于" in w for w in result["warnings"]), "有告警：%s" % (result["warnings"][:1],))


# --------------------------------------------------------------------------
# ④ 配置健壮性 & 真实数据核对
# --------------------------------------------------------------------------

def test_config_fallback() -> None:
    print("\n[配置坏了 / 丢了：回落内置分级，不崩]")
    os.makedirs(OUT_DIR, exist_ok=True)
    bad = os.path.join(OUT_DIR, "_bad_grade_profiles.json")
    with open(bad, "w", encoding="utf-8") as fh:
        json.dump({"default": "nope", "profiles": [{"key": "x", "edges": [1, 0.5]}]}, fh)
    reg = profiles.load_registry(bad, reload=True)
    check(reg.default.key == "jindoushan" and reg.warnings,
          "坏配置 → 回落 %s，告警：%s" % (reg.default.key, reg.warnings[0][:40]))

    reg = profiles.load_registry(os.path.join(OUT_DIR, "_nope.json"), reload=True)
    check(reg.default.key == "jindoushan" and reg.warnings, "缺配置文件 → 回落内置分级")


def test_real_report() -> None:
    print("\n[真实中心矿段报告：配置档位与报告里的一致]")
    if not os.path.isfile(REAL_CENTER):
        check(True, "本机没有这份报告，跳过（不影响结论）")
        return
    ws = load_workbook(REAL_CENTER, data_only=True).active
    labels = {str(r[0]).strip() for r in ws.iter_rows(min_row=3, values_only=True)
              if r and r[0] and isinstance(r[2], (int, float))     # 只认有体积的明细行
              and str(r[0]).strip() not in ("小计", "合计", "总计", "类型")}
    cen = _registry().get("center")
    for label in cen.labels:
        check(label in labels, "报告里出现中心矿段档位 %s" % label)
    owned = [x for x in labels if cen.owns_label(x)]
    foreign = [x for x in labels if not cen.owns_label(x)]
    check(len(owned) >= 3, "命中 %d 种中心矿段档位" % len(owned))
    print("        另见：报告里还混着 %s —— 这些是历史遗留（工具按金斗山分级出过一部分），"
          "重跑汇总即可统一" % ("、".join(sorted(foreign)) or "无"))


def main() -> int:
    print("=" * 78)
    reg = _registry()
    print("分级配置：%s" % reg.source)
    for key, name in reg.choices():
        print("  - %-12s %s" % (key, reg.get(key).describe()))
    print("-" * 78)

    test_bands()
    test_no_gap_no_overlap()
    test_sort_order()
    test_detect()
    test_title()
    test_merge_center()
    test_merge_jindoushan()
    test_merge_auto()
    test_below_cutoff()
    test_config_fallback()
    test_real_report()

    failed = [msg for ok, msg in _checks if not ok]
    print("\n" + "=" * 78)
    print("共 %d 项检查，%d 项通过" % (len(_checks), len(_checks) - len(failed)))
    if failed:
        for msg in failed:
            print("  FAIL  %s" % msg)
        print("结论：存在差异 ✗")
        return 1
    print("结论：全部一致 ✓")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
