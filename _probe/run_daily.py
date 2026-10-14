# -*- coding: utf-8 -*-
import sys, os, io, json
sys.stdout.reconfigure(encoding='utf-8')
ROOT = r"D:/WK/N CRT/Excel处理工具"
sys.path.insert(0, ROOT)
from src.daily_merge.pipeline import DailyMergeOptions, run, resolve_plan, summarize

day = sys.argv[1]
dry = "--dry" in sys.argv
opts = DailyMergeOptions(day_dir=day, dry_run=dry, backup=not dry)
plan = resolve_plan(opts)
print("== 计划 ==")
for l in plan.describe(): print("  ", l)
if plan.missing:
    print("  缺失："); [print("    -", m) for m in plan.missing]
rep = run(opts)
print("== 结果 ==")
for l in summarize(rep): print("  ", l)
print("== 明细 ==")
for k, r in rep["results"].items():
    print("  ", k, json.dumps({kk: vv for kk, vv in r.items() if kk not in ("src","dst")}, ensure_ascii=False))
for k, e in rep["errors"].items():
    print("  ERROR", k, e)
