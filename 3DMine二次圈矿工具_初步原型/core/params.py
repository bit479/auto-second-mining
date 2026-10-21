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
    "block_simplify_m": 0.3,   # 矿块轮廓抽稀容差(m)：去 Voronoi 锯齿，面积变化≤2%
    "ring_alpha_k": 0.0,       # >0 时把"矿孔外轮廓+外推"并进矿界（宽/弯矿带兜底）
    # 分块模式：chain = 整条矿化带一条外围矿界，界内再按品位分块（3940 用）；
    #           clusters = 每个"同档+相邻"孔簇各取领地当矿界，簇间留空白（3960 用）。
    "ring_mode": "chain",
    "isolated_min_holes": 3,   # 孤立小组孔数 ≥ 这个值就单独圈成矿块，否则列待取样
    # 人工指定链（留空=自动判定）。填了就以人工为准：
    #   chain_left / chain_right = 强制进左/右链的孔号（如 ["P14","P32"]）
    #   chain_exclude            = 强制不进任何链的孔号（内部孔）
    "chain_left": [],
    "chain_right": [],
    "chain_exclude": [],
    "chain_smooth_m": 0.0,     # >0 时先给链做道格拉斯-普客平滑再外推（治锯齿尖刺）
    "repair_tip_m": 0.8,       # 自检修补廊道端头伸出量(m)；-1 = 自动(extrude+0.8，上限 4)
    # 端部闭合时只认"落在端孔之外"的无品位孔（用户 2026-10-14 规则：单排端头往
    # 没有炮孔的一侧推 extrude，另一侧用 1/2 工程间距＝与无品位孔的中点）。
    # 置 False = 旧的宽松行为（半径内任何无品位孔都拿来取中点），只给标定时
    # 发现"紧凑孔簇端头"更贴人工图的个别炮区用（如 3960-0919）。
    "end_pair_beyond": True,
    # 与综合图历史矿块"贴合对齐"（用户 2026-10-14：首先要像人工图）：
    # 综合图边界与矿界间距 ≤ 这个值的地方，把矿界改走历史矿块的边界；
    # 离得远的（> 这个值）不动。0 = 关闭。
    "seam_join_m": 0.5,
    # 精确模式（用户 2026-10-08 认可保留）：填了就在这个炮区**直接用人工画好的
    # 外推矿界**，不再自动算矿界。给多个 3DMine 导出的 .3ds 字符串文件路径，
    # 拼接顺序自动按端点最近串起来（1008 就是左边界/与综合图边界/右边界/右上边界四段）。
    # 留空 = 走自动圈矿。
    "outline_files": [],
    # 人工圈矿模式（用户 2026-10-15）：填了就把这些 .3ds 里**每条闭合线当成一块**，
    # 程序不再自己圈矿，只按 口径确认记录 的算量口径算量、出图、出报告。
    # 与 outline_files 的区别：outline_files 是"整条当矿界，界内程序按品位再分块"（精确模式）；
    # manual_blocks 是"你画好的每一块就是一块"（人工圈矿模式）。
    "manual_blocks": [],
    "block_merge_gap": 0.0,    # >0 时：相邻两块平均品位差小于它 就并成一块
    "same_block": [],          # 人工指定这些孔算同一块，如 [["P1","P2","P3","P4","P6"]]
    "density_waste": 2.65,     # 0–0.5 档容重
    "density_ore": 2.7,        # 0.5 以上各档容重
    # ---- 按平台覆盖（键 = 平台号，如 "3940" / "3970"）----
    # 同一个平台的所有炮区共用这一层（外推距离、容重这类"矿体特性"通常整平台一致）
    "platforms": {},
    # ---- 按炮区覆盖（键 = "<平台号>-<炮区号>"，如 "3940-1003"）----
    # 这里**故意留空**：实际覆盖值都写在 圈矿参数.json 里（那是唯一生效来源，
    # GUI 的"存为该炮区"、calibrate.py --write 都写它）。
    # 2026-10-14 清理：以前这里还留着 "1003"/"0915" 这种**只有日期的旧键**，
    # 它们从来不生效（for_blast 只认 "<平台>-<日期>"），却会被台账/统计脚本
    # 当成"一个叫 0915 的平台"，看着像是有覆盖其实没有。
    "blasts": {},
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
