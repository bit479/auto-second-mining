# -*- coding: utf-8 -*-
"""一个炮区的完整圈矿流程（单一入口，命令行/GUI/评审脚本都走这里）。

流程：
  ① 分档 → 主矿化带 + 孤立小组（连接半径 zone_link_m）
  ② 孤立小组：孔数 ≥ isolated_min_holes 的**单独圈成自己的矿块**
     （孔数更少的才列"缺工程，待取样"——1008 的 P43、P47 是 2 孔组，列待取样；
       0922 的 P9/P15/P16/P17 是 4 孔组，人工图是单独圈成一块的）
  ③ 每个带各自生成外围矿界（链式外推 + 端部闭合 + 南端接综合图 + 自检修补）
  ④ 每带内分块定档（同档连通块 → 小块并入 → 按块平均品位定档）
  ⑤ 体号全局重排，高档在前
"""
from __future__ import annotations

import math

from oreblocks import load_holes_xls
from strip import (LAST_RING, average_blocks, block_of_cluster, class_clusters,
                   isolated_ring, join_to_composite, zone_outline)


def pick_zone(holes, gap: float = 1.0, adjacent_max: float = 15.0):
    """返回 (主矿化带矿孔, 待定孤立孔组)。同孔位先去重，再按邻接距离分组。"""
    ore = [h for h in holes.values() if h.grade >= 0.5]
    kept = []
    for h in ore:
        if any(abs(h.x - k.x) < gap and abs(h.y - k.y) < gap for k in kept):
            continue
        kept.append(h)
    groups, used = [], [False] * len(kept)
    for i in range(len(kept)):
        if used[i]:
            continue
        g = [kept[i]]
        used[i] = True
        changed = True
        while changed:
            changed = False
            for j in range(len(kept)):
                if used[j]:
                    continue
                if any(math.hypot(a.x - kept[j].x, a.y - kept[j].y) <= adjacent_max
                       for a in g):
                    g.append(kept[j])
                    used[j] = True
                    changed = True
        groups.append(g)
    groups.sort(key=len, reverse=True)
    return (groups[0] if groups else []), groups[1:]


def run_blast(holes, allh, P: dict, comp_blocks=None, blast: str = ""):
    """按参数 P 跑一个炮区，返回 dict（矿孔/待取样/各带矿界/矿块/自检警告）。"""
    ore, groups = pick_zone(holes, adjacent_max=P["zone_link_m"])
    min_holes = int(P.get("isolated_min_holes", 3) or 0)
    zones, pending = [ore] if len(ore) >= 2 else [], []
    for g in groups:
        if min_holes and len(g) >= min_holes:
            zones.append(g)
        else:
            pending.append(g)

    blocks, rings, warns = [], [], []
    seam = float(P.get("seam_join_m", 0.0) or 0.0)
    # ---- 分块模式 ----
    # "clusters"（3960 用）：**每个"同档+相邻"的孔簇各取自己的领地当矿界**，
    #   簇与簇之间留空白——3960 人工图就是这种一段段互不相连的窄条带。
    # "chain"（3940 用，缺省）：整条矿化带生成一条外围矿界，界内再分块。
    if P.get("ring_mode") == "clusters":
        for zn in zones:
            for grp in class_clusters(zn, allh,
                                      min_fragment=float(P.get("cluster_merge_m2", 0.0) or 0),
                                      same=P.get("cluster_same"),
                                      solo=P.get("cluster_solo"),
                                      exclude=P.get("cluster_exclude"),
                                      exact=P.get("cluster_exact")):
                ring = isolated_ring(grp, allh, P["extrude_m"], P["simplify_m"])
                if P.get("cluster_strip_mode") == "hull":
                    ring = isolated_ring(grp, allh, P["extrude_m"], P["simplify_m"],
                                         method="hull")
                if ring is None or ring.is_empty:
                    continue
                ring = join_to_composite(ring, comp_blocks, seam)
                rings.append(ring)
                warns += list(LAST_RING.get("warn") or [])
                # 一个簇 = 一块（不再簇内二次分组）
                b1 = block_of_cluster(grp, ring, allh,
                                      density_waste=P.get("density_waste", 2.65),
                                      density_ore=P.get("density_ore", 2.7))
                if b1 is not None:
                    blocks.append(b1)
        order = {"L4": 0, "L3": 1, "L2": 2, "L1": 3}
        blocks.sort(key=lambda b: (order.get(b.level_id, 9), -b.volume_m3))
        for i, b in enumerate(blocks, 1):
            b.no = i
        return {"ore": ore, "pending": pending, "zones": zones, "rings": rings,
                "blocks": blocks, "warn": warns, "holes": allh}
    for zi, zn in enumerate(zones):
        if zi > 0:
            # 孤立小组：用"领地 + 凸包外扩上限"这条规则（邻孔分界线天然挡住）
            ring = isolated_ring(zn, allh, P["extrude_m"], P["simplify_m"])
        else:
            ring = zone_outline(zn, allh, P["extrude_m"], comp_blocks=comp_blocks,
                                merge_gap=P["merge_gap_m"], blast=blast,
                                simplify=P["simplify_m"],
                                alpha_k=P.get("ring_alpha_k", 0.0),
                                chain_left=P.get("chain_left") or (),
                                chain_right=P.get("chain_right") or (),
                                chain_exclude=P.get("chain_exclude"),
                                chain_smooth_m=P.get("chain_smooth_m", 0.0),
                                repair_tip_m=P.get("repair_tip_m"),
                                end_pair_beyond=P.get("end_pair_beyond", True))
        if ring is None:
            continue
        ring = join_to_composite(ring, comp_blocks, seam)
        rings.append(ring)
        warns += list(LAST_RING.get("warn") or [])
        blocks += average_blocks(zn, ring, P.get("density_ore", 2.7),
                                 min_fragment=P["min_fragment_m2"],
                                 merge_gap=P.get("block_merge_gap", 0.0),
                                 same_block=P.get("same_block") or [],
                                 all_holes=allh,
                                 density_waste=P.get("density_waste", 2.65),
                                 density_ore=P.get("density_ore", 2.7))
    order = {"L4": 0, "L3": 1, "L2": 2, "L1": 3}
    blocks.sort(key=lambda b: (order.get(b.level_id, 9), -b.volume_m3))
    for i, b in enumerate(blocks, 1):
        b.no = i
    return {"ore": ore, "pending": pending, "zones": zones, "rings": rings,
            "blocks": blocks, "warn": warns, "holes": allh}


def run_blast_from_xls(xls, P: dict, comp_blocks=None, blast: str = ""):
    holes = load_holes_xls(xls)
    return run_blast(holes, list(holes.values()), P, comp_blocks, blast)
