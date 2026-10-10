# -*- coding: utf-8 -*-
"""按人工流程重构的圈矿核心（条带法）。

人工流程（由用户 10 个 .3ds 逐步验算还原）：
  ① 把矿孔按走向分成左右两列，分别连成两条链（3、4 列时取第 1 列与最后一列，
     目的是把所有矿孔包在里面）；
  ② 两条链各自向**外侧法向**平移 3 m（逐点位移实测正好 3.000 m）；
  ③ 两端：链端孔与**同侧最近的无品位孔**连线，取中点，用中点折线闭合；
  ④ 闭合顺序：西链外推线 → 端部中点折线 → 东链外推线 → 端部中点折线 → 闭合；
  ⑤ 品位分界：不同品位档的相邻孔之间取中点连线（＝Voronoi 边界）；
  ⑥ 矿块 = 外围矿界 ∩ 该档孔的 Voronoi 单元并集。
"""
from __future__ import annotations

import math

import numpy as np
from shapely.geometry import Polygon
from scipy.spatial import Voronoi

EXTRUDE_M = 3.0        # 外侧外推距离
CHAIN_WINDOW_FACTOR = 1.0   # 链提取的沿向窗口 = 1.0 × 中位最近孔距
END_SEARCH_R = 12.0    # 端部找邻孔半径
END_LIMIT = 2          # 每端每侧最多取几个邻孔的中点


def _pca(xy):
    c = xy.mean(axis=0)
    _, _, vt = np.linalg.svd(xy - c, full_matrices=False)
    u = vt[0]
    v = np.array([-u[1], u[0]])
    if v[0] < 0:                     # 法向大致指向东(+x)
        v = -v
    return c, u, v


def _rows(s, gap):
    order = np.argsort(s)
    rows, cur = [], []
    for i in order:
        if cur and s[i] - s[cur[-1]] > gap:
            rows.append(cur)
            cur = []
        cur.append(int(i))
    if cur:
        rows.append(cur)
    return rows


def zone_chains(ore, all_holes=None):
    """返回 (左链索引, 右链索引, 中心, 走向 u, 法向 v)；左＝法向负侧。

    规则（人工流程）：以走向为轴把矿孔分东西两半（t 的中位数为界）；
    西半侧中，在 ±W 沿向窗口内最西的孔进左链；东半侧中，窗口内最东的孔进右链。
    """
    xy = np.array([(h.x, h.y) for h in ore], float)
    c, u, v = _pca(xy)
    s = (xy - c) @ u
    t = (xy - c) @ v
    d = np.hypot(xy[:, None, 0] - xy[None, :, 0], xy[:, None, 1] - xy[None, :, 1])
    np.fill_diagonal(d, 1e9)
    win = CHAIN_WINDOW_FACTOR * float(np.median(d.min(axis=1)))
    # 判"这一侧有没有炮孔"时要把**无品位孔**也算进去（用户的规则）
    others = []
    for h in (all_holes or []):
        if any(h.hid == o.hid for o in ore):
            continue
        p = np.array([h.x, h.y]) - c
        others.append((float(p @ u), float(p @ v)))
    left, right = [], []
    for i in range(len(ore)):
        cand = [(s[j], t[j]) for j in range(len(ore)) if j != i and abs(s[j] - s[i]) <= win]
        cand += [p for p in others if abs(p[0] - s[i]) <= win]
        # 西侧无孔 → 该孔是西边界（左链，向西外推 3 m）
        if all(t[i] <= p[1] + 1e-9 for p in cand):
            left.append(i)
        # 东侧无孔 → 该孔是东边界（右链，向东外推 3 m）
        if all(t[i] >= p[1] - 1e-9 for p in cand):
            right.append(i)
    left.sort(key=lambda j: s[j])
    right.sort(key=lambda j: s[j])
    return left, right, c, u, v


def _mids_to_waste(hole, waste, radius=END_SEARCH_R, limit=END_LIMIT):
    cand = sorted(waste, key=lambda w: math.hypot(hole.x - w.x, hole.y - w.y))
    out = []
    for w in cand[:limit]:
        if math.hypot(hole.x - w.x, hole.y - w.y) <= radius:
            out.append(((hole.x + w.x) / 2.0, (hole.y + w.y) / 2.0))
    return out


def zone_outline(ore, all_holes, extrude: float = EXTRUDE_M):
    """整条矿化带的外围矿界（闭合多边形）。"""
    if len(ore) < 2:
        return None
    left, right, c, u, v = zone_chains(ore, all_holes)
    xy = np.array([(h.x, h.y) for h in ore], float)
    waste = [h for h in all_holes if h.grade < 0.5]
    west = [tuple(xy[j] - v * extrude) for j in left]
    east = [tuple(xy[j] + v * extrude) for j in right]
    north = _mids_to_waste(ore[left[-1]], waste) + _mids_to_waste(ore[right[-1]], waste)
    south = _mids_to_waste(ore[left[0]], waste) + _mids_to_waste(ore[right[0]], waste)

    def along(p):
        return (p[0] - c[0]) * u[0] + (p[1] - c[1]) * u[1]

    ring = list(west)
    ring += sorted(north, key=lambda p: -along(p))
    ring += list(reversed(east))
    ring += sorted(south, key=lambda p: along(p))
    poly = Polygon(ring).buffer(0)
    return poly if not poly.is_empty else None


def _voronoi_cells(ore, clip: Polygon):
    xy = np.array([(h.x, h.y) for h in ore], float)
    b = clip.bounds
    extra = np.array([[b[0] - 1e3, b[1] - 1e3], [b[2] + 1e3, b[1] - 1e3],
                      [b[0] - 1e3, b[3] + 1e3], [b[2] + 1e3, b[3] + 1e3]], float)
    vor = Voronoi(np.vstack([xy, extra]))
    out = {}
    for i, h in enumerate(ore):
        reg = vor.regions[vor.point_region[i]]
        if not reg or -1 in reg:
            continue
        p = Polygon(vor.vertices[reg]).buffer(0).intersection(clip)
        if not p.is_empty and p.area > 1e-9:
            out[h.hid] = p
    return out


def degree_blocks(ore, outline, density: float):
    """矿界内按品位档分块（同档且相接的孔并成一块）。"""
    from oreblocks import Block, Cell

    if outline is None or not ore:
        return []
    cells = _voronoi_cells(ore, outline)
    blocks = []
    for lid, lo, hi, label in (("L4", 3.0, 9e9, "3.000-999.000"),
                               ("L3", 1.5, 3.0, "1.500-3.000"),
                               ("L2", 1.0, 1.5, "1.000-1.500"),
                               ("L1", 0.5, 1.0, "0.500-1.000")):
        hs = [h for h in ore if lo <= h.grade < hi and h.hid in cells]
        used = [False] * len(hs)
        groups = []
        for i in range(len(hs)):
            if used[i]:
                continue
            grp = [hs[i]]
            used[i] = True
            changed = True
            while changed:
                changed = False
                for j in range(len(hs)):
                    if used[j]:
                        continue
                    if any(cells[a.hid].distance(cells[hs[j].hid]) < 1e-6 for a in grp):
                        grp.append(hs[j])
                        used[j] = True
                        changed = True
            groups.append(grp)
        for grp in groups:
            cs = [Cell(hid=h.hid, hole=h, polygon=cells[h.hid],
                       area_m2=cells[h.hid].area) for h in grp]
            b = Block(level_id=lid, label=label, holes=list(grp), cells=cs)
            b.compute(density)
            blocks.append(b)
    for i, b in enumerate(blocks, 1):
        b.no = i
    return blocks
