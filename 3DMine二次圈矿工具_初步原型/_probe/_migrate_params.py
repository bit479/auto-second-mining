# -*- coding: utf-8 -*-
"""一次性小工具：把各处 `for_blast(日期)` 的调用补上平台参数（平台档案机制）。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EDITS = [
    ("_probe/compare_manual_auto.py", "P = _params.for_blast(date)",
     'P = _params.for_blast(date, platform="3940")'),
    ("_probe/review_batch.py", "P = _params.for_blast(date)",
     'P = _params.for_blast(date, platform="3940")'),
    ("_probe/review_1008.py", 'P = _params.for_blast("1008")',
     'P = _params.for_blast("1008", platform="3940")'),
    ("_probe/selftest.py", "P = _params.for_blast(d)",
     'P = _params.for_blast(d, platform="3940")'),
    ("_probe/tune_blocks2.py", "P = dict(_params.for_blast(d))",
     'P = dict(_params.for_blast(d, platform="3940"))'),
    ("_probe/tune_chains.py", "P0 = _params.for_blast(date)",
     'P0 = _params.for_blast(date, platform="3940")'),
    ("core/run_batch.py", "P = _params.for_blast(date)",
     "P = _params.for_blast(date, platform=plat)"),
    ("core/merge_status.py", "res = run_blast(holes, list(holes.values()), _params.for_blast(date), comp, blast=date)",
     'res = run_blast(holes, list(holes.values()),\n                    _params.for_blast(date, platform=plat), comp, blast=date)'),
]


def main() -> None:
    for rel, old, new in EDITS:
        p = ROOT / rel
        t = p.read_text(encoding="utf-8")
        if old in t:
            p.write_text(t.replace(old, new, 1), encoding="utf-8")
            print("OK   " + rel)
        else:
            print("跳过 " + rel + "（没找到目标行）")


if __name__ == "__main__":
    main()
