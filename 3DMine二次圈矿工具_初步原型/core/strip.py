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
from shapely.ops import unary_union
from scipy.spatial import Voronoi

EXTRUDE_M = 3.0        # 外侧外推距离
SIMPLIFY_M = 0.8       # 矿界抽稀容差(m)：让边界尽量是直线段，拐点不要过多
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


def zone_chains(ore, all_holes=None, manual_left=(), manual_right=(), exclude=()):
    """返回 (左链索引, 右链索引, 中心, 走向 u, 法向 v)；左＝法向负侧。

    方案 2（用户确认）：矿化带画一条走向中线（＝过所有矿孔质心、沿 PCA 主轴的直线），
    中线西侧的孔串成左链、东侧的串成右链；个别孔允许人工指定（manual_left / manual_right）。
    """
    xy = np.array([(h.x, h.y) for h in ore], float)
    c, u, v = _pca(xy)
    s = (xy - c) @ u
    t = (xy - c) @ v
    ml, mr, ex = set(manual_left), set(manual_right), set(exclude)
    left = [i for i in range(len(ore))
            if (t[i] <= 0 or ore[i].short in ml) and ore[i].short not in mr and ore[i].short not in ex]
    right = [i for i in range(len(ore))
             if (t[i] > 0 or ore[i].short in mr) and ore[i].short not in ml and ore[i].short not in ex]
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


def _offset_chain(pts, centroid, dist):
    """按每个点的局部法向（相邻两段方向的平均的垂线）向外平移 dist。"""
    pts = [np.array(p, float) for p in pts]
    n = len(pts)
    out = []
    for i in range(n):
        if n == 1:
            d = np.array([0.0, 0.0])
        elif i == 0:
            d = pts[1] - pts[0]
        elif i == n - 1:
            d = pts[-1] - pts[-2]
        else:
            a = pts[i] - pts[i - 1]
            b = pts[i + 1] - pts[i]
            a = a / (np.linalg.norm(a) + 1e-12)
            b = b / (np.linalg.norm(b) + 1e-12)
            d = a + b
        nd = np.linalg.norm(d)
        if nd < 1e-9:
            d = np.array([0.0, 1.0])
        else:
            d = d / nd
        nrm = np.array([-d[1], d[0]])          # 垂线方向
        if np.dot(nrm, pts[i] - np.asarray(centroid, float)) < 0:
            nrm = -nrm                          # 指向矿化带外侧
        out.append(tuple(pts[i] + nrm * dist))
    return out


def _end_mids(end_hole, waste, ref_dir, radius=END_SEARCH_R):
    """端部闭合：端孔与附近所有无品位孔的中点，沿 ref_dir 排序。"""
    mids = []
    for w in waste:
        d = math.hypot(end_hole.x - w.x, end_hole.y - w.y)
        if d <= radius:
            mids.append(((end_hole.x + w.x) / 2.0, (end_hole.y + w.y) / 2.0))
    r = np.asarray(ref_dir, float)
    mids.sort(key=lambda p: (p[0] - end_hole.x) * r[0] + (p[1] - end_hole.y) * r[1])
    return mids


def zone_outline(ore, all_holes, extrude: float = EXTRUDE_M):
    """整条矿化带的外围矿界（复刻人工图的折线结构：11~21 个拐点）。

    人工图的画法（由其 .3ds 逐步还原）：
      西侧 = 左链（西侧那列孔）逐段沿局部法向外推 3 m；
      东侧 = 右链（东侧那列孔）逐段沿局部法向外推 3 m；
      两端 = 端部矿孔与**相邻无品位孔的中点**连成折线（这就是"辅助线中点"）；
      若某端外侧没有炮孔 → 该端沿走向再推 3 m（不横穿炮孔）。
    """
    if len(ore) < 2:
        return None
    left, right, c, u, v = zone_chains(ore, all_holes)
    xy = np.array([(h.x, h.y) for h in ore], float)
    waste = [h for h in all_holes if h.grade < 0.5]
    west = _offset_chain([xy[j] for j in left], c, extrude)
    east = _offset_chain([xy[j] for j in right], c, extrude)
    # 端部闭合：端部一段内的**所有**矿孔都与相邻无品位孔配对取中点（人工图是一串中点）
    s_all = (xy - c) @ u
    t_all = (xy - c) @ v
    span = float(s_all.max() - s_all.min())
    band = max(12.0, 0.35 * span)          # 端部参与配对的长度

    def end_mids(want_north: bool):
        lo, hi = (s_all.max() - band, 1e18) if want_north else (-1e18, s_all.min() + band)
        sel = [j for j in range(len(ore)) if lo <= s_all[j] <= hi]
        mids = []
        for j in sel:
            mids += _end_mids(ore[j], waste, u if want_north else -u, radius=12.0)
        return mids

    # 北端按人工配方（8 个指定孔对的中点，已验证 8/8 与人工 .3ds 吻合）
    north = None
    try:
        from rules import north_closure_points
        from oreblocks import Hole as _H  # noqa: F401
        hmap = {}
        for h in all_holes:
            hmap[h.hid] = h
            hmap.setdefault(h.short, h)
        north = north_closure_points(hmap)
    except Exception:
        north = None
    if not north:
        north = end_mids(True)
    south = end_mids(False)
    if not north:
        north = [tuple(np.array(west[-1]) + u * extrude),
                 tuple(np.array(east[-1]) + u * extrude)]
    if not south:
        south = [tuple(np.array(west[0]) - u * extrude),
                 tuple(np.array(east[0]) - u * extrude)]

    def along(p):
        return (p[0] - c[0]) * u[0] + (p[1] - c[1]) * u[1]

    def across(p):
        return (p[0] - c[0]) * v[0] + (p[1] - c[1]) * v[1]

    # 拼接顺序严格照人工：左边界(北→南) -> 南端闭合 -> 右边界(南→北) -> 北端闭合
    ring = list(reversed(west))              # 左边界：北 → 南
    # 端部闭合按**横向**排序（从东侧走到西侧 / 西侧走到东侧），不要再按走向排序，
    # 否则端点会来回跳、画出锯齿三角形（这是上一版北端出锯齿的原因）。
    ring += sorted(south, key=lambda p: across(p))   # 南端闭合：西 → 东
    ring += list(east)                       # 右边界：南 → 北
    # 北端配方是"左边界上端 → … → 右边界上端"（西→东）；拼环时从东端走回西端，故反转
    ring += list(reversed(north))
    poly = Polygon(ring).buffer(0)
    if poly.is_empty:
        return None
    if SIMPLIFY_M > 0:
        sp = poly.simplify(SIMPLIFY_M, preserve_topology=True)
        if not sp.is_empty and sp.area > 0.5 * poly.area:
            poly = sp
    return poly


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


def degree_blocks(ore, outline, density: float, split_mode: str = "voronoi"):
    """矿界内按品位档分块（同档且相接的孔并成一块）。

    split_mode="voronoi"：用矿孔 Voronoi 单元并集作为各档范围（当前更贴近人工）；
    split_mode="midline"：用"跨档邻孔中点折线"切分（人工的品位界限做法，仍在标定）。
    """
    from oreblocks import Block, Cell
    from oreblocks import level_of
    from shapely.geometry import LineString
    from shapely.ops import split as shp_split

    if outline is None or not ore:
        return []
    # ---- 分档：用"跨档邻孔中点折线"把矿界切开（对应人工的"品位界限"）----
    xy = np.array([(h.x, h.y) for h in ore], float)
    d = np.hypot(xy[:, None, 0] - xy[None, :, 0], xy[:, None, 1] - xy[None, :, 1])
    np.fill_diagonal(d, 1e9)
    adj = 1.6 * float(np.median(d.min(axis=1)))
    pairs = {}
    for i in range(len(ore)):
        for j in range(i + 1, len(ore)):
            if d[i][j] > adj:
                continue
            li = level_of(ore[i].grade)[0]
            lj = level_of(ore[j].grade)[0]
            if li == lj:
                continue
            key = tuple(sorted((li, lj)))
            mid = ((ore[i].x + ore[j].x) / 2.0, (ore[i].y + ore[j].y) / 2.0)
            pairs.setdefault(key, []).append((mid, li, lj))

    pieces = [outline]
    if split_mode == "midline":
        # 品位界限是一棵"树"：先连主界线，再挂分支。做法：
        # 把跨档中点建成图（近邻连边），再拆成极大路径（端点/分支点处断开）。
        for key, mids in pairs.items():
            pts_all = [m[0] for m in mids]
            n = len(pts_all)
            if n < 2:
                continue
            lim = max(1.6 * adj, 4.0)
            nb = {i: set() for i in range(n)}
            for i in range(n):
                for j in range(i + 1, n):
                    if math.hypot(pts_all[i][0] - pts_all[j][0],
                                  pts_all[i][1] - pts_all[j][1]) <= lim:
                        nb[i].add(j)
                        nb[j].add(i)
            # 从"端点或分支点"出发走极大路径
            visited_edges = set()
            paths = []
            starts = [i for i in range(n) if len(nb[i]) != 2] or [0]
            for s in starts:
                for nx in nb[s]:
                    e = (min(s, nx), max(s, nx))
                    if e in visited_edges:
                        continue
                    path = [s, nx]
                    visited_edges.add(e)
                    prev, cur = s, nx
                    while len(nb[cur]) == 2:
                        nxt = [t for t in nb[cur] if t != prev]
                        if not nxt:
                            break
                        nxt = nxt[0]
                        ee = (min(cur, nxt), max(cur, nxt))
                        if ee in visited_edges:
                            break
                        visited_edges.add(ee)
                        path.append(nxt)
                        prev, cur = cur, nxt
                    paths.append([pts_all[i] for i in path])
            for pts in paths:
                if len(pts) < 2:
                    continue
                a = np.array(pts[0], float)
                b = np.array(pts[-1], float)
                dirv = b - a
                n = np.linalg.norm(dirv)
                if n < 1e-9:
                    continue
                dirv = dirv / n
                ext = 200.0      # 人工的品位界限是横切整条矿化带
                pts = [tuple(a - dirv * ext)] + pts + [tuple(b + dirv * ext)]
                line = LineString(pts)
                new = []
                for p in pieces:
                    try:
                        new.extend(shp_split(p, line).geoms)
                    except Exception:
                        new.append(p)
                pieces = new

    # ---- 每个子片按"离哪个矿孔最近"归属品位档，再同档合并 ----
    buckets = {}
    if split_mode == "midline":
        for p in pieces:
            if p.area < 0.5:
                continue
            rp = p.representative_point()
            best = min(ore, key=lambda h: (h.x - rp.x) ** 2 + (h.y - rp.y) ** 2)
            buckets.setdefault(level_of(best.grade)[0], []).append(p)

    cells_all = _voronoi_cells(ore, outline)
    blocks = []
    for lid, lo, hi, label in (("L4", 3.0, 9e9, "3.000-999.000"),
                               ("L3", 1.5, 3.0, "1.500-3.000"),
                               ("L2", 1.0, 1.5, "1.000-1.500"),
                               ("L1", 0.5, 1.0, "0.500-1.000")):
        region = None
        if split_mode == "midline":
            for p in buckets.get(lid, []):
                region = p if region is None else region.union(p)
        else:
            hs0 = [h for h in ore if lo <= h.grade < hi and h.hid in cells_all]
            if hs0:
                region = unary_union([cells_all[h.hid] for h in hs0])
        if region is None:
            continue
        hs = [h for h in ore if lo <= h.grade < hi and h.hid in cells_all]
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
                    if any(cells_all[a.hid].distance(cells_all[hs[j].hid]) < 1e-6 for a in grp):
                        grp.append(hs[j])
                        used[j] = True
                        changed = True
            groups.append(grp)
        for grp in groups:
            sub = unary_union([cells_all[h.hid] for h in grp]).intersection(region)
            if sub.is_empty or sub.area < 0.5:
                continue
            cs = [Cell(hid=h.hid, hole=h,
                       polygon=cells_all[h.hid].intersection(sub),
                       area_m2=cells_all[h.hid].intersection(sub).area) for h in grp]
            b = Block(level_id=lid, label=label, holes=list(grp), cells=cs)
            b.compute(density)
            blocks.append(b)
    for i, b in enumerate(blocks, 1):
        b.no = i
    return blocks
