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

# 基准取哪个：`report` = 人工报告的合计（3940：用户 2026-10-13 定"1004 以报告为准"）；
# `figure` = 按**图**算（人工块轮廓 × 全场孔 Voronoi 单元，跟我们算法同口径）——
# 3960 用户 2026-10-13 定"以图为准"（1008/1009 的报告与图差 4~6 倍）。
SOURCE = {"3940": "report", "3960": "figure"}


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
    """基准体积：(体积, 说明)。按平台取"报告"或"按图算"，见 SOURCE。"""
    src = SOURCE.get(str(platform), "report")
    rep = manual_volume(platform, date)
    if src == "figure":
        try:
            import sys as _sys
            _sys.path.insert(0, str(PROBE.parent / "core"))
            from strip import _cells_within
            cells = _cells_within(ore, man_poly)
            vol = sum(cells[h.hid].area * h.grade_lenght
                      for h in ore if h.hid in cells)
            note = "按图算"
            if rep is not None and vol > 0 and (rep < 0.7 * vol or rep > 1.3 * vol):
                note = "按图算（报告 %.0f 与图对不上，已按图）" % rep
            return vol, note
        except Exception as exc:
            return rep, "报告（按图算失败：%s）" % exc
    if rep is None:
        return None, "无报告数"
    return rep, "报告"
