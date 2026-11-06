# -*- coding: utf-8 -*-
"""v1.16 UI 多分辨率 / 多 DPI 截图矩阵（仅截图，不改业务数据）。"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "client" / "ui_v2" / "app.py"
OUT = ROOT / "_probe" / "ui_shots_v116" / "matrix"
PY = sys.executable

CONFIGS = [
    ("1920x1080@100", "1920x1080", "0.8"),
    ("1600x900@125", "1600x900", "1.0"),
    ("1366x768@150", "1366x768", "1.2"),
    ("1366x768@100", "1366x768", "0.8"),
]
PAGES = ["dashboard", "single", "batch", "manual", "composite", "excel",
         "database", "params", "diagnostics", "settings"]

OUT.mkdir(parents=True, exist_ok=True)
log = []
fails = 0
for tag, size, scale in CONFIGS:
    for page in PAGES:
        target = OUT / ("%s_%s.png" % (tag, page))
        env = dict(os.environ)
        env["QT_SCALE_FACTOR"] = scale
        env["PYTHONIOENCODING"] = "utf-8"
        cmd = [PY, "-X", "utf8", str(APP), "--shot", str(target),
               "--page", page, "--size", size]
        p = subprocess.run(cmd, cwd=str(ROOT), env=env, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=120)
        ok = target.exists() and p.returncode == 0
        if not ok:
            fails += 1
        err = (p.stderr or "").strip().splitlines()
        log.append("%-16s %-12s %s %s" % (tag, page, "OK" if ok else "FAIL",
                                          err[-1] if err else ""))
        print(log[-1], flush=True)

(OUT / "_log.txt").write_text("\n".join(log), encoding="utf-8")
print("FAILS =", fails)
