# -*- coding: utf-8 -*-
"""一次性小工具：把各处读 `manual_<日期>_c.json` 改成走 baseline.scan_path（多平台）。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLAT = 'platform = "3940"\n'
EDITS = [
    ("_probe/compare_manual_auto.py",
     '    j = json.loads((PROBE / ("manual_%s_c.json" % date)).read_text(encoding="utf-8"))',
     '    import baseline as _bl\n'
     '    j = json.loads(_bl.scan_path("3940", date).read_text(encoding="utf-8"))'),
    ("_probe/tune_blocks.py",
     '    j = json.loads((PROBE / ("manual_%s_c.json" % date)).read_text(encoding="utf-8"))',
     '    import baseline as _bl\n'
     '    j = json.loads(_bl.scan_path("3940", date).read_text(encoding="utf-8"))'),
    ("_probe/tune_blocks2.py",
     '    j = json.loads((PROBE / ("manual_%s_c.json" % date)).read_text(encoding="utf-8"))',
     '    import baseline as _bl\n'
     '    j = json.loads(_bl.scan_path("3940", date).read_text(encoding="utf-8"))'),
    ("_probe/tune_chains.py",
     '    j = json.loads((PROBE / ("manual_%s_c.json" % date)).read_text(encoding="utf-8"))',
     '    import baseline as _bl\n'
     '    j = json.loads(_bl.scan_path("3940", date).read_text(encoding="utf-8"))'),
]


def main() -> None:
    for rel, old, new in EDITS:
        p = ROOT / rel
        t = p.read_text(encoding="utf-8")
        if old in t:
            p.write_text(t.replace(old, new, 1), encoding="utf-8")
            print("OK   " + rel)
        else:
            print("跳过 " + rel)


if __name__ == "__main__":
    main()
