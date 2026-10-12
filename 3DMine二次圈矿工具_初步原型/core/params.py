# -*- coding: utf-8 -*-
"""圈矿参数（可按平台覆盖）——存 `圈矿参数.json`，GUI 和命令行共用。

标定依据（用 5 张人工图量的"块边界到最近矿孔的距离"）：
  1008 2.97 m / 0915 2.88 m / 1004 2.97 m → 外推 3.0 m
  1003 2.45 m → 那张图画得紧 0.5 m，所以 1003 单独用 2.5 m
  0922 6.86 m → 特殊炮区（用户说不用管）
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / "圈矿参数.json"

DEFAULTS = {
    "extrude_m": 3.0,          # 外围矿界向外推的距离(m)
    "zone_link_m": 15.0,       # 孤立孔连接半径(m)：≤这个距离才算同一条矿化带
    "min_fragment_m2": 40.0,   # 最小块段(m²)：比它小的同档碎片并入邻块
    "merge_gap_m": 8.0,        # 南端接综合图历史块的最大间距(m)
    "grid_res_m": 1.0,         # 方格网边长(m)
    "simplify_m": 0.8,         # 矿界抽稀容差(m)
    "ring_alpha_k": 0.0,       # >0 时把"矿孔外轮廓+外推"并进矿界（宽/弯矿带兜底）
    "density_waste": 2.65,     # 0–0.5 档容重
    "density_ore": 2.7,        # 0.5 以上各档容重
    "platforms": {             # 按平台覆盖（键 = 炮区号，如 "1003"）
        "1003": {"extrude_m": 2.5},
        "1004": {"ring_alpha_k": 1.5},
    },
}


def load(path: Path = None) -> dict:
    path = Path(path) if path else PATH
    cfg = json.loads(json.dumps(DEFAULTS))          # 深拷贝默认值
    if path.exists():
        try:
            user = json.loads(path.read_text(encoding="utf-8"))
            for k, v in user.items():
                if k == "platforms" and isinstance(v, dict):
                    cfg["platforms"].update(v)
                else:
                    cfg[k] = v
        except Exception as exc:
            print("[参数] 读 %s 失败，用默认值：%s" % (path, exc))
    return cfg


def save(cfg: dict, path: Path = None) -> Path:
    path = Path(path) if path else PATH
    path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def for_blast(date: str, cfg: dict = None) -> dict:
    """返回某个炮区实际生效的参数（平台覆盖 + 全局默认）。"""
    cfg = cfg or load()
    out = {k: v for k, v in cfg.items() if k != "platforms"}
    for k, v in (cfg.get("platforms", {}).get(str(date), {}) or {}).items():
        out[k] = v
    out["platform_used"] = str(date)
    return out


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "init":
        p = save(load())
        print("已写出默认参数：", p)
    else:
        c = load()
        for k, v in c.items():
            print("%-18s %s" % (k, v))
        for d in ("1008", "1003", "1004"):
            print("  炮区 %s 生效:" % d, {k: v for k, v in for_blast(d).items()
                                        if k != "platform_used"})
