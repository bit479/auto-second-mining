# -*- coding: utf-8 -*-
"""报告对账：把我们生成的报告 xlsx 与人工报告 xlsx 逐项比，并自检内部一致性。

用法: python report_check.py <平台> <日期> [我们的报告.xlsx]
  没给我们的报告路径时，默认找 sample_data/output/GUI跑通_<日期>/<平台>平台 <日期>炮孔数据报告.xlsx
检查项：
  ① 版式：标题 / 表头（类型,体号,体积,重量,平均品位(Au),金属量（百克））/ 每块一行+小计 / 合计 / 品位统计行；
  ② 口径自检：重量 = 体积×容重（块内按单元档 2.65/2.7 加权，这里用 2.65~2.70 区间夹逼）；
              金属量 = 重量×平均品位/100（3 位小数）；平均品位 = 金属量÷重量；
  ③ 与人工报告比：合计体积/重量/品位/金属量 的偏差（块数按规则可能不同，只比合计）。
"""
import sys, re
from pathlib import Path
import openpyxl

ROOT = Path(__file__).resolve().parent.parent
DAY = ROOT.parent
HDR = ["类型", "体号", "体积", "重量", "平均品位(Au)", "金属量（百克）"]


def read_report(path: Path):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.worksheets[0]
    rows = [[c for c in r] for r in ws.iter_rows(values_only=True)]
    rows = [r for r in rows if any(x not in (None, "") for x in r)]
    return rows


def fnum(x):
    try:
        return float(x)
    except Exception:
        return None


def main():
    plat, date = sys.argv[1], sys.argv[2]
    cands = ([Path(sys.argv[3])] if len(sys.argv) > 3 else []) + [
        ROOT / "sample_data" / "output" / ("GUI跑通_%s" % date) /
        ("%s平台 %s炮孔数据报告.xlsx" % (plat, date)),
        ROOT / "sample_data" / "output" / ("对账_%s" % date) /
        ("%s平台 %s炮孔数据报告.xlsx" % (plat, date))]
    fresh = "--fresh" in sys.argv
    ours = None if fresh else next((c for c in cands if c.exists()), None)
    if ours is None:
        # 没有现成报告就自己跑一遍（这才是"每次改代码都能盯住报告口径"的用法）
        import subprocess
        out = ROOT / "sample_data" / "output" / ("对账_%s" % date)
        xls = next(iter(sorted((DAY / ("北部山头%s平台2026" % plat) / "7、单日数据" /
                                ("北部山头%s平台-%s" % (plat, date))).glob("1、*.xls"))), None)
        comp = next(iter(sorted((DAY / ("北部山头%s平台2026" % plat)).glob("*综合*.dwg"))), None)
        if xls is None or comp is None:
            print("找不到数据库或综合图，无法生成报告。")
            return 2
        print("[报告对账] 先跑一遍流水线生成报告 -> %s" % out)
        subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "core" / "run_strip.py"),
                        str(xls), plat, date, str(out), str(comp)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, check=False)
        ours = out / ("%s平台 %s炮孔数据报告.xlsx" % (plat, date))
    man = DAY / ("北部山头%s平台2026" % plat) / "7、单日数据" / \
        ("北部山头%s平台-%s" % (plat, date)) / ("%s平台 %s炮孔数据报告.xlsx" % (plat, date))
    if ours is None or not ours.exists():
        print("我们的报告不存在（生成失败）")
        return 2
    print("我们的报告：%s  (%s)" % (ours.name, "存在"))
    print("人工报告  ：%s  (%s)" % (man.name, "存在" if man.exists() else "**不存在**"))
    if not ours.exists():
        return 2
    A = read_report(ours)
    bad = []
    # ① 版式
    if len(A) < 3:
        bad.append("行数太少")
    else:
        print("标题      ：%r" % (A[0][0],))
        hdr = [str(x) if x is not None else "" for x in A[1][:6]]
        ok_hdr = all(h and h.strip() in HDR[i] or HDR[i] in h for i, h in enumerate(hdr))
        print("表头      ：%s  %s" % (hdr, "✓" if ok_hdr else "✗（人工表头 %s）" % HDR))
        if not ok_hdr:
            bad.append("表头不符")
    has_sub = any(str(r[0]).startswith("小计") for r in A)
    has_tot = any(str(r[0]).startswith("合计") for r in A)
    has_stat = any("炮孔品位统计" in str(r[0]) or "孔数" in str(r[0]) or "≥3" in str(r[0]) for r in A)
    print("小计/合计/品位统计行：%s / %s / %s" % (has_sub, has_tot, has_stat))
    if not (has_sub and has_tot):
        bad.append("缺小计或合计")
    # ② 口径自检（每块：重量 = 体积×容重；金属量 = 重量×品位/100）
    print("--- 口径自检（每块） ---")
    for r in A[2:]:
        if r[0] is None or str(r[0]).startswith(("小计", "合计")) or "统计" in str(r[0]):
            continue
        v, w, g, m = fnum(r[2]), fnum(r[3]), fnum(r[4]), fnum(r[5])
        if None in (v, w, g, m):
            continue
        dens = w / v if v else 0
        m_calc = w * g / 100.0
        ok1 = 2.63 <= dens <= 2.72
        # 表里"平均品位"只留 3 位小数，所以金属量的自洽容差要按 0.0005 的品位误差放宽
        ok2 = abs(m_calc - m) <= 0.002 + w * 5e-4 / 100.0 * 1.05
        g_calc = (m * 100.0 / w) if w else 0
        ok3 = abs(g_calc - g) <= 5e-4
        flag = "✓" if (ok1 and ok2 and ok3) else "✗"
        print("  %-6s 体号%-3s 体积%9.3f 重量%10.3f 容重%.4f 品位%.6f 金属量%8.3f  算得%.3f %s"
              % (str(r[0]), str(r[1]), v, w, dens, g, m, m_calc, flag))
        if not (ok1 and ok2 and ok3):
            bad.append("块%s 口径不自洽" % r[1])
    # ③ 与人工报告比合计
    if man.exists():
        B = read_report(man)
        def totals(R):
            for r in R:
                if str(r[0]).startswith("合计"):
                    return [fnum(x) for x in r[2:6]]
            return None
        ta, tb = totals(A), totals(B)
        if ta and tb:
            print("--- 合计对账（我们 / 人工 / 偏差） ---")
            for name, a, b in zip(("体积", "重量", "品位", "金属量"), ta, tb):
                dev = (a - b) / b * 100 if b else 0
                print("  %-4s %12.3f / %12.3f  (%+.2f%%)" % (name, a, b, dev))
        # 品位统计行的孔数合计 vs 数据库孔数
        for r in A:
            if "孔数" in str(r[0]):
                print("  报告品位统计行：%s" % [x for x in r if x is not None])
    print()
    if bad:
        print("结论：有 %d 处问题：%s" % (len(bad), "；".join(bad)))
        return 1
    print("结论：版式与口径自检通过 ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
