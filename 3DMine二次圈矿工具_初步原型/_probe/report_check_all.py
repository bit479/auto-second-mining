# -*- coding: utf-8 -*-
"""报告口径回归（一条命令）：对每个有"人工报告"的炮区，重跑流水线生成报告，
再逐项对账（版式 + 每块口径自洽 + 合计与人工报告偏差）。

用法: python report_check_all.py [平台 ...]     缺省 3940
退出码 0 = 全部通过（版式/口径自洽 + |合计体积偏差| ≤ 门槛；3940 门槛 10%）
"""
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAY = ROOT.parent
PLATS = [a for a in sys.argv[1:] if not a.startswith("-")] or ["3940"]
GATE = {"3940": 0.10, "3960": 0.30}


def blasts(plat):
    base = DAY / ("北部山头%s平台2026" % plat) / "7、单日数据"
    out = []
    for d in sorted(x for x in base.iterdir() if x.is_dir()):
        date = d.name.split("-")[-1].strip()
        reps = sorted(d.glob("*炮孔数据报告.xlsx"))
        if not reps:
            continue
        # 文件夹里可能混着别的日期的报告（1004 目录里就有一份"…1003炮孔数据报告"），
        # 只认文件名里带本炮区号的；一个都没有就跳过并提示。
        mine = [r for r in reps if date in r.name]
        if not mine:
            print("%s-%s 跳过：目录里的报告都不是本炮区的（%s）"
                  % (plat, date, "、".join(r.name for r in reps)))
            continue
        out.append((date, mine[0]))
    return out


rows = []
for plat in PLATS:
    for date, man in blasts(plat):
        p = subprocess.run([sys.executable, "-X", "utf8",
                            str(Path(__file__).parent / "report_check.py"), plat, date, "--fresh"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        txt = p.stdout or ""
        dev = None
        for line in txt.splitlines():
            if line.strip().startswith("体积") and "/" in line and "(" in line:
                try:
                    dev = float(line.rsplit("(", 1)[1].split("%")[0])
                except Exception:
                    pass
        ok = (p.returncode == 0)
        rows.append((plat, date, "通过" if ok else "有出入", dev))
        print("%-11s 报告口径 %s%s" % ("%s-%s" % (plat, date), rows[-1][2],
                                       "" if dev is None else "   合计体积偏差 %+.2f%%" % dev))
print()
bad = [r for r in rows if r[2] != "通过" or (r[3] is not None and abs(r[3]) > GATE.get(r[0], 0.30) * 100)]
if bad:
    print("需要看的：%s" % "、".join("%s-%s" % (b[0], b[1]) for b in bad))
    sys.exit(1)
print("报告口径回归全部通过 ✓（共 %d 个炮区）" % len(rows))
