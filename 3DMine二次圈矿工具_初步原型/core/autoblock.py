# -*- coding: utf-8 -*-
"""全自动圈连（不需要 3DMine 导出）。

已实测确认的 3DMine 机制：
  ① 矿孔按品位档（左闭右开）分类，同档且相邻的孔并成一个矿块；
  ② 矿界（矿块范围）由人工圈定，规则上≈"各孔在爆区 Voronoi 里的单元 ∩ 以孔为心的
     影响半径圆"；本模块用 INFLUENCE_R 作该半径，全自动生成矿界；
  ③ 矿块内部：用**该块自己的孔**做 Voronoi，裁剪到矿界 → 单元；
  ④ 体积 = Σ(单元面积 × 该孔 gradeLenght)，gradeLenght = round(孔深)；
     重量 = 体积 × 容重；品位 = Σ(gradeLenght × 孔品位[2位]) / Σ(gradeLenght)。

②是唯一带经验参数的环节，INFLUENCE_R 可按矿区标定（1008 上 3.5 m 最贴近人工图）。
"""
from __future__ import annotations

import math

from shapely.geometry import MultiPoint, Point, Polygon, box
from shapely.ops import unary_union
from scipy.spatial import Voronoi

from oreblocks import Block, Cell, level_of

# 外推距离(m)：人工圈矿按"1/2 工程距离"外推；各平台统一按 3.0 起，可按矿区标定。
# （1008 实测：外推 3.5 m 与人工图最贴，3.0 m 时各块小约 15~20%）
INFLUENCE_R = 3.0
MIN_HOLES_PER_BLOCK = 2   # 孤立单孔不单独圈矿（周围无同档相邻孔时）
MIN_HOLE_GAP = 1.0        # 两个孔距离小于该值时视为同一个孔位（重复孔）
ADJACENT_MAX = 8.8        # 视为"相邻"的最大孔距(m)：2×中位孔距，超过即不并块
HULL_MARGIN = 30.0    # 爆区外扩(m)，用于给边界孔构造有界 Voronoi 单元


def _bounded_voronoi(holes, margin: float = HULL_MARGIN):
    """对全部孔做 Voronoi，并用凸包外扩框裁剪，返回 {hole_id: polygon}。"""
    ids = [h.hid for h in holes]
    xy = [(h.x, h.y) for h in holes]
    hull = MultiPoint(xy).convex_hull.buffer(margin, join_style="mitre")
    far = box(hull.bounds[0] - 1e4, hull.bounds[1] - 1e4,
              hull.bounds[2] + 1e4, hull.bounds[3] + 1e4)
    import numpy as np
    vor = Voronoi(np.array(xy, float).tolist() + far.boundary.coords[:])
    cells = {}
    for i, hid in enumerate(ids):
        reg = vor.regions[vor.point_region[i]]
        if not reg or -1 in reg:
            cells[hid] = None
            continue
        p = Polygon(vor.vertices[reg]).buffer(0)
        cells[hid] = p.intersection(hull) if not p.is_empty else None
    return cells


def _group_by_level(holes, cells):
    """同档且（单元相接 或 孔距很近）的孔并成候选矿块。"""
    ore = [h for h in holes if h.grade >= 0.5]
    out = []
    for lid, _, _, _ in (("L4", 3.0, 9e9, ""), ("L3", 1.5, 3.0, ""),
                         ("L2", 1.0, 1.5, ""), ("L1", 0.5, 1.0, "")):
        todo = [h for h in ore if level_of(h.grade)[0] == lid]
        used = [False] * len(todo)
        for i in range(len(todo)):
            if used[i]:
                continue
            group = [todo[i]]
            used[i] = True
            changed = True
            while changed:
                changed = False
                for j in range(len(todo)):
                    if used[j]:
                        continue
                    if any(_touching(a, todo[j], cells) for a in group):
                        group.append(todo[j])
                        used[j] = True
                        changed = True
            out.append((lid, group))
    return out


def _touching(a, b, cells, tol: float = 0.6):
    """两个孔是否相邻：单元相接（或距离在 tol 内）。"""
    d = math.hypot(a.x - b.x, a.y - b.y)
    if d > ADJACENT_MAX:
        return False
    ca, cb = cells.get(a.hid), cells.get(b.hid)
    if ca is not None and cb is not None and ca.distance(cb) < 1e-6:
        return True
    return d <= tol


def auto_blocks(holes, density: float, influence_r: float = INFLUENCE_R):
    """返回按高档在前编号的 Block 列表（每个块已算好指标）。"""
    holes = list(holes.values()) if isinstance(holes, dict) else list(holes)
    holes = _dedupe(holes)
    cells_all = _bounded_voronoi(holes)
    groups = _group_by_level(holes, cells_all)
    blocks = []
    pending = []          # 不单独圈矿的孤立区（列入"缺工程，待取样验证"）
    for lid, group in groups:
        if _distinct_positions(group) < MIN_HOLES_PER_BLOCK:
            pending.append((lid, group))
            continue
        # ② 自动矿界 = 各孔单元 ∩ 影响半径圆
        parts = []
        for h in group:
            c = cells_all.get(h.hid)
            if c is None:
                parts.append(Point(h.x, h.y).buffer(influence_r, resolution=32))
            else:
                parts.append(c.intersection(
                    Point(h.x, h.y).buffer(influence_r, resolution=32)))
        outline = unary_union(parts).buffer(0)
        # ③ 块内 Voronoi（只用本块的孔），裁剪到矿界
        sub = _voronoi_inside(group, outline)
        b = Block(level_id=lid, label=level_of(group[0].grade)[1],
                  holes=list(group), cells=sub)
        b.compute(density)
        blocks.append(b)
    for i, b in enumerate(blocks, 1):
        b.no = i
    return blocks, pending


def _distinct_positions(group, gap: float = MIN_HOLE_GAP) -> int:
    """按孔位去重（重复孔位只算一个）。"""
    pts = []
    for h in group:
        if not any(math.hypot(h.x - x, h.y - y) < gap for x, y in pts):
            pts.append((h.x, h.y))
    return len(pts)


def _dedupe(holes, gap: float = MIN_HOLE_GAP):
    """去掉重复孔位（距离 < gap 视为同一个孔，保留先出现的）。"""
    kept = []
    for h in holes:
        if any(math.hypot(h.x - k.x, h.y - k.y) < gap for k in kept):
            continue
        kept.append(h)
    return kept


def _voronoi_inside(group, outline: Polygon):
    """块内 Voronoi 单元（用本块自己的孔），裁剪到矿界。"""
    import numpy as np
    xy = np.array([(h.x, h.y) for h in group], float)
    if len(group) == 1:
        return [Cell(hid=group[0].hid, hole=group[0], polygon=outline,
                     area_m2=outline.area)]
    bx = outline.bounds
    extra = np.array([[bx[0] - 1e3, bx[1] - 1e3], [bx[2] + 1e3, bx[1] - 1e3],
                      [bx[0] - 1e3, bx[3] + 1e3], [bx[2] + 1e3, bx[3] + 1e3]], float)
    vor = Voronoi(np.vstack([xy, extra]))
    out = []
    for i, h in enumerate(group):
        reg = vor.regions[vor.point_region[i]]
        poly = None
        if reg and -1 not in reg:
            p = Polygon(vor.vertices[reg]).buffer(0)
            poly = p.intersection(outline)
        if poly is None or poly.is_empty:
            continue
        out.append(Cell(hid=h.hid, hole=h, polygon=poly, area_m2=poly.area))
    return out
