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
from shapely.geometry import LineString, Point
from shapely.ops import nearest_points
from shapely.ops import unary_union
from scipy.spatial import Voronoi

EXTRUDE_M = 3.0        # 外侧外推距离
SIMPLIFY_M = 0.8       # 矿界抽稀容差(m)：让边界尽量是直线段，拐点不要过多
SOUTH_MERGE_GAP = 8.0  # 南端与综合图历史块"能并在一起"的最大间距(m)
CHAIN_WINDOW_FACTOR = 1.0   # 链提取的沿向窗口 = 1.0 × 中位最近孔距
END_SEARCH_R = 12.0    # 端部找邻孔半径
END_LIMIT = 2          # 每端每侧最多取几个邻孔的中点

# 最近一次 zone_outline 的结果细节（供出图/交付用）
LAST_RING: dict = {}


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


def zone_chains(ore, all_holes=None, manual_left=(), manual_right=(), exclude=None):
    """返回 (左链索引, 右链索引, 中心, 走向 u, 法向 v)；左＝法向负侧。

    方案 2（用户确认）：矿化带画一条走向中线（＝过所有矿孔质心、沿 PCA 主轴的直线），
    中线西侧的孔串成左链、东侧的串成右链；个别孔允许人工指定（manual_left / manual_right）。

    用户补充（单排孔规则）：只按走向分链会把"内部孔"（两侧都有矿孔）也塞进链里
    （1008 的 P8 就是这样），边界会鼓出去。所以再加一层：**只看走向方向 ±band
    范围内的邻孔**——
      两侧都有矿孔 → 内部孔，不进任何链（如 P8）；
      只有西侧有矿孔 → 它是这一排最靠东的孔 → 进右链；
      只有东侧有矿孔 → 它是这一排最靠西的孔 → 进左链；
      范围内没有任何矿孔 → 退回到中线规则（t ≤ 0 进左链）。
    这里 band = 0.8 × 矿孔最近邻距离中位数，1008 上 12 个孔的归属与人工完全一致。
    """
    if exclude is None:
        try:
            from rules import CHAIN_EXCLUDE
            exclude = CHAIN_EXCLUDE
        except Exception:
            exclude = ()
    xy = np.array([(h.x, h.y) for h in ore], float)
    c, u, v = _pca(xy)
    s = (xy - c) @ u
    t = (xy - c) @ v
    ml, mr, ex = set(manual_left), set(manual_right), set(exclude)
    n = len(ore)
    dmin = []
    for i in range(n):
        dmin.append(min(np.hypot(xy[j][0] - xy[i][0], xy[j][1] - xy[i][1])
                        for j in range(n) if j != i) if n > 1 else 0.0)
    band = 0.9 * float(np.median(dmin)) if n > 1 else 0.0
    left, right = [], []
    for i in range(n):
        if ore[i].short in ex:
            continue
        nb = [j for j in range(n) if j != i and abs(s[j] - s[i]) <= band]
        w = [j for j in nb if t[j] < t[i]]
        e = [j for j in nb if t[j] > t[i]]
        want_left = want_right = False
        if w and e:
            want_left = want_right = False            # 内部孔
        elif w:
            want_right = True                          # 该排最靠东
        elif e:
            want_left = True                           # 该排最靠西
        else:
            want_left, want_right = t[i] <= 0, t[i] > 0
        if ore[i].short in mr:
            want_left, want_right = False, True
        elif ore[i].short in ml:
            want_left, want_right = True, False
        if want_left:
            left.append(i)
        if want_right:
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


def _offset_chain(pts, centroid, dist, outward=None):
    """按每个点的局部法向（相邻两段方向的平均的垂线）向**外侧**平移 dist。

    outward：外侧参考方向（一般取 ±矿化带法向 v）。给了它就用它定正负——
    只按"远离质心"判会把链端点的外法向判反（1008 的左链首点就这样被推到了东侧）。
    """
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
        if outward is not None:
            if np.dot(nrm, np.asarray(outward, float)) < 0:
                nrm = -nrm
        elif np.dot(nrm, pts[i] - np.asarray(centroid, float)) < 0:
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


def _arc_through_north(poly: Polygon, a, b):
    """沿多边形外环取一条从 a 到 b、经过最北顶点的弧（返回含端点的坐标表）。"""
    coords = list(poly.exterior.coords)[:-1]
    for p in (a, b):
        best = None
        n = len(coords)
        for i in range(n):
            seg = LineString([coords[i], coords[(i + 1) % n]])
            d = seg.distance(Point(p))
            if best is None or d < best[0]:
                best = (d, i)
        i = best[1]
        coords = coords[:i + 1] + [tuple(p)] + coords[i + 1:]
    ia = min(range(len(coords)),
             key=lambda k: (coords[k][0] - a[0]) ** 2 + (coords[k][1] - a[1]) ** 2)
    ib = min(range(len(coords)),
             key=lambda k: (coords[k][0] - b[0]) ** 2 + (coords[k][1] - b[1]) ** 2)
    lo, hi = sorted((ia, ib))
    arc1 = coords[lo:hi + 1]                       # a..b 或 b..a
    arc2 = coords[hi:] + coords[:lo + 1]
    if ia > ib:
        arc1 = list(reversed(arc1))
        arc2 = list(reversed(arc2))
    pick = arc1 if max(p[1] for p in arc1) >= max(p[1] for p in arc2) else arc2
    return [tuple(p) for p in pick]


def south_closure(le, re, comp_blocks, gap: float = SOUTH_MERGE_GAP):
    """南端"与综合图边界"：左边界下端 -> 综合图历史块 -> 右边界下端。

    规则（用户 1008 口述）：从左边界最下端沿左侧走向向下延伸到综合图的边界，
    再连接综合图上部的拐点，最后接右边界下端。
    实现：取离左右下端最近、且间距 ≤ gap 的历史块；落到该块边界上（最近点），
    沿"经过最北顶点"的那条弧走到右边界下端。返回 (折线点表, 并入的历史块)。
    """
    best, bestd = None, 1e18
    for item in (comp_blocks or []):
        poly = item[2]
        if poly is None or poly.is_empty:
            continue
        d = min(Point(le).distance(poly), Point(re).distance(poly))
        if d <= gap and d < bestd:
            best, bestd = poly, d
    if best is None:
        return None, None
    entry = nearest_points(Point(le), best.exterior)[1]
    exit_ = nearest_points(Point(re), best.exterior)[1]
    if entry.distance(exit_) < 1e-9:
        return None, None
    arc = _arc_through_north(best, (entry.x, entry.y), (exit_.x, exit_.y))
    seq = [tuple(le)] + arc + [tuple(re)]
    out = [seq[0]]
    for p in seq[1:]:
        if math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > 1e-6:
            out.append(p)
    return out, best


def zone_outline(ore, all_holes, extrude: float = EXTRUDE_M,
                 comp_blocks=None, merge_gap: float = SOUTH_MERGE_GAP,
                 blast: str = None):
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
    west = _offset_chain([xy[j] for j in left], c, extrude, outward=-v)
    east = _offset_chain([xy[j] for j in right], c, extrude, outward=v)
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

    # 北端：只有"配方所属炮区"才用人工配方（8 个指定孔对的中点，1008 上 8/8 吻合）。
    # 别的炮区孔号虽然同名但位置不同，必须走通用的"邻孔中点"闭合。
    north = None
    try:
        from rules import north_closure_points, NORTH_RECIPE_BLAST
        if blast and blast == NORTH_RECIPE_BLAST:
            hmap = {}
            for h in all_holes:
                hmap[h.hid] = h
                hmap.setdefault(h.short, h)
            north = north_closure_points(hmap)
    except Exception:
        north = None
    if not north:
        north = end_mids(True)
    # 南端：优先接综合图历史块（用户规则）；没有综合图时才退回"邻孔中点"闭合
    south, merged_block = south_closure(tuple(west[0]), tuple(east[0]),
                                        comp_blocks, merge_gap)
    if south is None:
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
    ring = list(reversed(west))              # 左边界：北 → 南（末点 = 左边界下端）
    # 南端闭合：已按"左边界下端 → … → 右边界下端"排好序（接综合图历史块）
    ring += [p for p in south if p != ring[-1]]      # 南端闭合：西 → 东
    ring += list(east)                       # 右边界：南 → 北
    # 北端配方是"左边界上端 → … → 右边界上端"（西→东）；拼环时从东端走回西端，故反转
    ring += list(reversed(north))
    poly = Polygon(ring).buffer(0)
    if poly.is_empty:
        return None
    LAST_RING["merged_block"] = merged_block
    LAST_RING["ring"] = ring
    if SIMPLIFY_M > 0:
        sp = poly.simplify(SIMPLIFY_M, preserve_topology=True)
        if not sp.is_empty and sp.area > 0.5 * poly.area:
            poly = sp
    return poly


def _voronoi_cells(ore, clip: Polygon):
    """矿孔 Voronoi 单元裁剪到 clip。"""
    return _cells_within(ore, clip)


def _cells_within(holes_sub, clip: Polygon):
    """只给 holes_sub 这一组孔做 Voronoi，再裁剪到 clip（块内 Voronoi）。"""
    if not holes_sub or clip is None or clip.is_empty:
        return {}
    xy = np.array([(h.x, h.y) for h in holes_sub], float)
    b = clip.bounds
    extra = np.array([[b[0] - 1e3, b[1] - 1e3], [b[2] + 1e3, b[1] - 1e3],
                      [b[0] - 1e3, b[3] + 1e3], [b[2] + 1e3, b[3] + 1e3]], float)
    vor = Voronoi(np.vstack([xy, extra]))
    out = {}
    for i, h in enumerate(holes_sub):
        reg = vor.regions[vor.point_region[i]]
        if not reg or -1 in reg:
            continue
        p = Polygon(vor.vertices[reg]).buffer(0).intersection(clip)
        if not p.is_empty and p.area > 1e-9:
            out[h.hid] = p
    return out


def degree_blocks(ore, outline, density: float, split_mode: str = "rules",
                  rules_holes=None, use_recipe: bool = False):
    """矿界内按品位档分块（同档且相接的孔并成一块）。

    split_mode="rules"  ：用规则表里的**指定孔对中点折线**当品位界限（人工配方，
                          1008 已逐点验证），再用"块内 Voronoi"分配体积；
    split_mode="voronoi"：用矿孔 Voronoi 单元并集作为各档范围（早期做法）；
    split_mode="midline"：用自动识别的"跨档邻孔中点折线"切分（无配方时的兜底）。
    """
    from oreblocks import Block, Cell
    from oreblocks import level_of
    from shapely.geometry import LineString
    from shapely.ops import split as shp_split

    if outline is None or not ore:
        return []
    # ---- 品位界限：优先用规则表（人工配方）----
    if split_mode == "rules":
        from rules import cut_lines
        if isinstance(rules_holes, dict):
            hmap = dict(rules_holes)
        else:
            hmap = {h.hid: h for h in (rules_holes or ore)}
        for h in ore:
            hmap.setdefault(h.short, h)
        _, _, _, _, vv = zone_chains(ore, None)
        pieces = [outline]
        # 默认走**通用自动识别**（对任何炮区都适用）；只有显式要求时才用人工配方
        if use_recipe:
            lines = cut_lines(hmap, vv)
        else:
            from gradecuts import auto_cut_lines
            lines = auto_cut_lines(ore, outline)
        for key, ln in lines:
            new = []
            for p in pieces:
                try:
                    new.extend(shp_split(p, ln).geoms)
                except Exception:
                    new.append(p)
            pieces = [q for q in new if q.geom_type == "Polygon" and q.area > 0.5]
            if not pieces:
                pieces = [outline]
                break
        buckets = {}
        for p in pieces:
            rp = p.representative_point()
            best = min(ore, key=lambda h: (h.x - rp.x) ** 2 + (h.y - rp.y) ** 2)
            buckets.setdefault(level_of(best.grade)[0], []).append(p)
        blocks = []
        for lid, lo, hi, label in (("L4", 3.0, 9e9, "3.000-999.000"),
                                   ("L3", 1.5, 3.0, "1.500-3.000"),
                                   ("L2", 1.0, 1.5, "1.000-1.500"),
                                   ("L1", 0.5, 1.0, "0.500-1.000")):
            plist = buckets.get(lid, [])
            if not plist:
                continue
            region = plist[0]
            for p in plist[1:]:
                region = region.union(p)
            hs = [h for h in ore if lo <= h.grade < hi]
            if not hs:
                continue
            cellmap = _cells_within(hs, region)     # 块内 Voronoi
            used = [False] * len(hs)
            for i in range(len(hs)):
                if used[i] or hs[i].hid not in cellmap:
                    continue
                grp = [hs[i]]
                used[i] = True
                changed = True
                while changed:
                    changed = False
                    for j in range(len(hs)):
                        if used[j] or hs[j].hid not in cellmap:
                            continue
                        if any(cellmap[a.hid].distance(cellmap[hs[j].hid]) < 1e-6
                               for a in grp):
                            grp.append(hs[j])
                            used[j] = True
                            changed = True
                cs = [Cell(hid=h.hid, hole=h, polygon=cellmap[h.hid],
                           area_m2=cellmap[h.hid].area) for h in grp]
                b = Block(level_id=lid, label=label, holes=list(grp), cells=cs)
                b.compute(density)
                blocks.append(b)
        for i, b in enumerate(blocks, 1):
            b.no = i
        return blocks
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
