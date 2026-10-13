# -*- coding: utf-8 -*-
"""验收基准的统一入口（支持多平台）。

* 人工图扫描结果：`_probe/manual_<平台>-<日期>_c.json`；
  为兼容早期，找不到时回退到 `manual_<日期>_c.json`（那是 3940 的）。
* 人工报告合计体积：`_probe/manual_volumes.json`，键 = `<平台>-<日期>`。

接新平台时：用 `scan_manual_retry.py` 只读扫描人工图存成带平台名的 json，
再把人工报告的合计体积填进 manual_volumes.json，就能纳入 selftest 闸门。
"""
from __future__ import annotations

import json
from pathlib import Path

PROBE = Path(__file__).resolve().parent
VOLUMES = PROBE / "manual_volumes.json"


def scan_path(platform: str, date: str) -> Path:
    return PROBE / ("manual_%s-%s_c.json" % (platform, date))


def manual_volumes() -> dict:
    if VOLUMES.exists():
        try:
            return json.loads(VOLUMES.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def manual_volume(platform: str, date: str):
    v = manual_volumes()
    for key in ("%s-%s" % (platform, date), str(date)):
        if key in v:
            return float(v[key])
    return None
