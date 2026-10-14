# -*- coding: utf-8 -*-
"""参数台账：把 圈矿参数.json 里"谁覆盖了什么、值多少、依据是什么"列出来。

用法: python params_report.py [平台 ...]      # 缺省全部

用途：一眼看出哪些值是**按人工图标定**出来的、哪些是拍的；有没有覆盖了但没写依据的；
有没有写错的键（不在 params.DEFAULTS 里的非 _说明 键）；有没有跟前一层重复的覆盖。
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))
import params as P

try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

cfg = P.load()
D = P.DEFAULTS
GLOBAL_KEYS = [k for k in D if k not in ("platforms", "blasts")]
def _plats_of(c):
    """平台号从两处取：platforms 的键 + blasts 键 "平台-炮区" 的前半段
    （3940 没有平台层覆盖，只出现在 blasts 里，只看 platforms 会漏掉它）。"""
    s = set((c.get("platforms", {}) or {}).keys())
    s |= {k.split("-", 1)[0] for k in (c.get("blasts", {}) or {}) if k[:1].isdigit() and "-" in k}
    return sorted(x for x in s if x)


PLAT = [a for a in sys.argv[1:] if not a.startswith("-")] or _plats_of(cfg)

print("=" * 78)
print("全局默认（= params.DEFAULTS，除非 圈矿参数.json 里覆盖过）")
print("=" * 78)
for k in GLOBAL_KEYS:
    a, b = D.get(k), cfg.get(k, D.get(k))
    mark = "" if a == b else "   ← 被 圈矿参数.json 覆盖成 %s" % json.dumps(b, ensure_ascii=False)
    print("  %-22s %-28s%s" % (k, json.dumps(b, ensure_ascii=False), mark))
extra = [k for k in cfg if k not in D and k not in ("platforms", "blasts")]
if extra:
    print("  ⚠ 圈矿参数.json 里有 DEFAULTS 中不存在的键：%s" % extra)

for plat in PLAT:
    pl = (cfg.get("platforms", {}) or {}).get(plat, {})
    print("")
    print("=" * 78)
    print("平台 %s 覆盖（%d 项）" % (plat, len([k for k in pl if not k.startswith("_")])))
    print("=" * 78)
    for k, v in pl.items():
        if k.startswith("_"):
            print("   说明：%s" % v)
            continue
        print("  %-22s %s" % (k, json.dumps(v, ensure_ascii=False)))
    bl = [k for k in (cfg.get("blasts", {}) or {}) if k.startswith(plat + "-")]
    bl.sort()
    for key in bl:
        d = cfg["blasts"][key]
        vals = {k: v for k, v in d.items() if not k.startswith("_")}
        notes = [v for k, v in d.items() if k.startswith("_")]
        eff = P.for_blast(key.split("-", 1)[1], platform=plat, cfg=cfg)
        print("")
        print("  ── 炮区 %s：覆盖 %d 项" % (key, len(vals)))
        for k, v in vals.items():
            base = pl.get(k, D.get(k))
            tag = "" if base == v else "   (平台层是 %s)" % json.dumps(base, ensure_ascii=False)
            print("       %-20s %s%s" % (k, json.dumps(v, ensure_ascii=False), tag))
        for n in notes:
            print("       · %s" % n)
        print("       生效：外推 %s m / 贴合 %s m / 模式 %s / 孤立组最少 %s / 连接 %s m" %
              (eff.get("extrude_m"), eff.get("seam_join_m"), eff.get("ring_mode"),
               eff.get("isolated_min_holes"), eff.get("zone_link_m")))
        if not notes:
            print("       ⚠ 这炮的覆盖没写依据（_说明）")
