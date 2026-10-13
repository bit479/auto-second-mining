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


def volume_for_gate(platform: str, date: str, man_poly, ore):
    """基准体积 = **人工报告的合计**（用户 2026-10-13 定的：以报告为准）。

    若报告与"图面积×平均孔长"差得太远（<0.7 或 >1.3 倍），在说明里标出来，
    提醒这份报告与图纸对不上（3960 的 1008 报 3287 而图面推算 ~19000、
    1009 报 17581 而图面推算 ~4200，两份都得人工确认以哪份为准）。
    返回 (体积, 说明)。
    """
    rep = manual_volume(platform, date)
    if not ore:
        return rep, "报告"
    mean_len = sum(h.grade_lenght for h in ore) / len(ore)
    implied = man_poly.area * mean_len
    if rep is None:
        return implied, "按图推算（无报告数）"
    note = "报告"
    if implied > 0 and (rep < 0.7 * implied or rep > 1.3 * implied):
        note = "报告（**与图对不上**：图面推算 %.0f）" % implied
    return rep, note
