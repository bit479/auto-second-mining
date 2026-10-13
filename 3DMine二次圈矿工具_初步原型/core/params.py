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
    "isolated_min_holes": 3,   # 孤立小组孔数 ≥ 这个值就单独圈成矿块，否则列待取样
    # 人工指定链（留空=自动判定）。填了就以人工为准：
    #   chain_left / chain_right = 强制进左/右链的孔号（如 ["P14","P32"]）
    #   chain_exclude            = 强制不进任何链的孔号（内部孔）
    "chain_left": [],
    "chain_right": [],
    "chain_exclude": [],
    "chain_smooth_m": 0.0,     # >0 时先给链做道格拉斯-普客平滑再外推（治锯齿尖刺）
    "repair_tip_m": 0.8,       # 自检修补廊道端头伸出量(m)；-1 = 自动(extrude+0.8，上限 4)
    "block_merge_gap": 0.0,    # >0 时：相邻两块平均品位差小于它 就并成一块
    "same_block": [],          # 人工指定这些孔算同一块，如 [["P1","P2","P3","P4","P6"]]
    "density_waste": 2.65,     # 0–0.5 档容重
    "density_ore": 2.7,        # 0.5 以上各档容重
    # ---- 按平台覆盖（键 = 平台号，如 "3940" / "3970"）----
    # 同一个平台的所有炮区共用这一层（外推距离、容重这类"矿体特性"通常整平台一致）
    "platforms": {},
    # ---- 按炮区覆盖（键 = 炮区号/日期，如 "1003"）----
    # 只对个别炮区生效（链、外推微调这类"这一炮特殊"的东西放这里）
    "blasts": {
        # 下面这些"链"是用人工图贪心标定出来的（_probe/tune_chains.py）：
        # 从自动分链出发，逐个试着把"没进链的孔"放进左/右链，取 IoU 最大的组合。
        # 1008 标定结果是"不用加"——说明自动判定在它上面本来就对。
        "1003": {"extrude_m": 2.5,
                 "chain_left": ["P2", "P3"],
                 # P19 是贪心标定之后补的：加进右链后矿界顶点 29→24（南缘那几根
                 # 自检修补拉出来的尖刺没了），体积只差 0.2%→−0.6%
                 "chain_right": ["P12", "P13", "P16", "P17", "P19", "P21", "P23", "P25"]},
        # 1004 人工图把 {P1,P2,P3}(2.18) 与 {P4,P6}(1.38) 并成一块(1.85)。
        # 试过"相邻块平均品位差 < 0.85 就并"，但它同时会把 {P28,P30}(1.55) 并进
        # 旁边 0.82 的大块——而人工图没并。差值 0.81 并、0.72 不并，阈值解释不通，
        # 所以暂时**不开**这个开关，等用户给规则。
        # 按用户要求：分块**必须走规则自动判**（哪怕跟人工图不一样），
        # 所以这里不用 same_block 硬指定；1004 自动分出 4 块，人工图是 3 块。
        "1004": {"ring_alpha_k": 1.5, "chain_right": ["P8", "P11"]},
        # 0915 修补出来的矿界原来贴着孔（只有 0.8 m 余量），把端头改成"自动留足外推量"
        "0915": {"chain_right": ["P8", "P10"], "repair_tip_m": -1},
        # 0922 人工图的外推量比别的炮区大一倍多：量出来 ~6.9 m，
        # 联搜（_probe/tune_chains.py 0922 --extrude …）在 8.0 m 处 IoU 最高
        # （0.572，体积 −18.7%；6.9 m 时 IoU 0.564 / −24.7%）
        "0922": {"extrude_m": 8.0, "repair_tip_m": -1},
    },
}


def load(path: Path = None) -> dict:
    path = Path(path) if path else PATH
    cfg = json.loads(json.dumps(DEFAULTS))          # 深拷贝默认值
    if path.exists():
        try:
            user = json.loads(path.read_text(encoding="utf-8"))
            for k, v in user.items():
                if k in ("platforms", "blasts") and isinstance(v, dict):
                    cfg.setdefault(k, {}).update(v)
                else:
                    cfg[k] = v
        except Exception as exc:
            print("[参数] 读 %s 失败，用默认值：%s" % (path, exc))
    return cfg


def save(cfg: dict, path: Path = None) -> Path:
    path = Path(path) if path else PATH
    path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def for_blast(date: str, platform: str = None, cfg: dict = None) -> dict:
    """返回某个炮区实际生效的参数：全局默认 → 平台覆盖 → 炮区覆盖。"""
    cfg = cfg or load()
    out = {k: v for k, v in cfg.items() if k not in ("platforms", "blasts")}
    for src in ("platforms", "blasts"):
        # 炮区层：给了平台就只认 "<平台>-<日期>"，**不回退**到只有日期的键
        # （否则 3940-0922 的参数会串到 3960-0922 上——2026-10-13 踩过）
        keys = [str(platform)] if src == "platforms" else \
            [("%s-%s" % (platform, date))] if platform else [str(date)]
        for key in keys:
            for k, v in ((cfg.get(src, {}) or {}).get(key, {}) or {}).items():
                out[k] = v
    out["platform"] = str(platform or "")
    out["blast"] = str(date)
    return out


def for_platform(platform: str, cfg: dict = None) -> dict:
    """只要平台这一层（不含具体炮区）。"""
    cfg = cfg or load()
    out = {k: v for k, v in cfg.items() if k not in ("platforms", "blasts")}
    for k, v in ((cfg.get("platforms", {}) or {}).get(str(platform), {}) or {}).items():
        out[k] = v
    out["platform"] = str(platform)
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
