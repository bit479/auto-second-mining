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
from shapely.geometry import LineString, MultiPoint, Point
from shapely.ops import nearest_points
from shapely.ops import unary_union
from scipy.spatial import Delaunay, Voronoi

EXTRUDE_M = 3.0        # 外侧外推距离
SIMPLIFY_M = 0.8       # 矿界抽稀容差(m)：让边界尽量是直线段，拐点不要过多
SOUTH_MERGE_GAP = 8.0  # 南端与综合图历史块"能并在一起"的最大间距(m)
# 南端可并的历史矿块图层白名单。设为 None = 不限图层。
#
# 曾经试过"只并品位图层"（想避开综合图里图层 0 的整片采场轮廓，1004 那张 725 m² 的
# 把整个矿化带都包住了），但配合"走短弧"之后实测**不限图层更好**：
#   1008 IoU 0.93 / 0915 0.91 / 1003 0.85 / 1004 0.77（限图层时 1004 只有 -4% 但 0915 掉到 0.87）
# 真正解决 1004 的是"短弧 + 自检修补"，不是图层过滤。
COMPOSITE_BLOCK_LAYERS = None
# 同档碎片小于这个面积就并入相邻块。用 5 张人工图（0915/0922/1003/1004/1008）标定：
# 40 m² + "并入平均品位最接近的邻块" 时，与人工图的分块一致率最高（0.936）。
MIN_FRAGMENT_M2 = 40.0
CHAIN_WINDOW_FACTOR = 1.0   # 链提取的沿向窗口 = 1.0 × 中位最近孔距
# "同一排"的判定窗口 = 这个系数 × 矿孔最近邻距离中位数（用户 2026-10-14 说
# "不设范围"；实测去掉窗口（设成很大的数）会让几乎所有孔都变成内部孔，
# 1008 的 12 孔归属从"与人工全一致"掉到 4 个孔进不了链，所以窗口先留着，
# 系数做成常量方便标定/回退。
CHAIN_BAND_FACTOR = 0.9
END_SEARCH_R = 12.0    # 端部找邻孔半径
END_LIMIT = 2          # 每端每侧最多取几个邻孔的中点
MIN_HOLES_FOR_INTERIOR = 6   # 少于这么多孔就不做"内部孔"剔除（小组直接分左右）

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


def _safe_union(geoms):
    """合并几何，遇到自相交等非法输入不让它崩（先修一下再并）。

    shapely 的 unary_union 碰到自相交/带洞错位的多边形会抛 GEOSException
    （3960-0908/0914 就撞上了），这里兜底成"逐个 buffer(0) 修复后再并"。
    """
    geoms = [g for g in geoms if g is not None and not g.is_empty]
    if not geoms:
        return None
    if len(geoms) == 1:
        return geoms[0]
    try:
        return unary_union(geoms)
    except Exception:
        fixed = []
        for g in geoms:
            try:
                fixed.append(g.buffer(0))
            except Exception:
                try:
                    fixed.append(g.buffer(0.01).buffer(-0.01))
                except Exception:
                    pass
        try:
            return unary_union(fixed)
        except Exception:
            return max(fixed, key=lambda g: g.area) if fixed else None


def _alpha_shape(xy, k: float):
    """凹包：Delaunay 三角网保留"最长边 < k × 最近邻距离中位数"的三角形。

    只在参数 `ring_alpha_k > 0` 时启用：把"链式外推环"和"外轮廓外推环"并起来，
    用来兜住那种孔列多、走向弯的矿化带（链式外推在那种形状上会夹断）。
    """
    from itertools import combinations
    xy = np.asarray(xy, float)
    if len(xy) < 3:
        return None
    nn = [min(np.hypot(xy[j][0] - xy[i][0], xy[j][1] - xy[i][1])
              for j in range(len(xy)) if j != i) for i in range(len(xy))]
    th = k * float(np.median(nn))
    tri = Delaunay(xy)
    polys = []
    for s in tri.simplices:
        p = xy[s]
        if max(np.hypot(*(p[(i + 1) % 3] - p[i])) for i in range(3)) < th:
            polys.append(Polygon(p))
    if not polys:
        return None
    return unary_union(polys).buffer(0)


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
    if n < MIN_HOLES_FOR_INTERIOR:
        # 孔很少的带（比如 4 孔的孤立小组）本来就两列都占不满，
        # 再按"两侧都有孔"剔内部孔会把该带的孔剔出去，直接按走向中线分左右。
        left = [i for i in range(n)
                if (t[i] <= 0 or ore[i].short in ml) and ore[i].short not in ex
                and ore[i].short not in mr]
        right = [i for i in range(n)
                 if (t[i] > 0 or ore[i].short in mr) and ore[i].short not in ex
                 and ore[i].short not in ml]
        left.sort(key=lambda j: s[j])
        right.sort(key=lambda j: s[j])
        return left, right, c, u, v
    dmin = []
    for i in range(n):
        dmin.append(min(np.hypot(xy[j][0] - xy[i][0], xy[j][1] - xy[i][1])
                        for j in range(n) if j != i) if n > 1 else 0.0)
    band = CHAIN_BAND_FACTOR * float(np.median(dmin)) if n > 1 else 0.0
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


def zone_chains_alpha(ore, all_holes=None, k: float = 2.0):
    """按**矿孔外轮廓的顺序**分左右链（链式外推的兜底方案）。

    走向中线分法（zone_chains）假设矿化带是"两列"的条带；孔列多、走向弯时
    左右链会交错、外推出来的环会夹断（1004 原来 10/23 个孔被甩到环外）。
    这里改成：先算矿孔的凹包轮廓，把外圈孔按轮廓顺序排成一圈，
    再从"沿走向最南"和"最北"两个孔把圈切两半——西边半圈＝左链、东边半圈＝右链，
    两条链天然首尾相接于南北两端。
    """
    n = len(ore)
    if n < 3:
        return zone_chains(ore, all_holes)
    xy = np.array([(h.x, h.y) for h in ore], float)
    sh = _alpha_shape(xy, k)
    if sh is None or sh.is_empty or sh.geom_type != "Polygon":
        return zone_chains(ore, all_holes)
    ring = sh.exterior
    pos = []
    for i in range(n):
        pos.append(ring.project(Point(xy[i][0], xy[i][1])))
    order = sorted(range(n), key=lambda i: pos[i])
    c, u, v = _pca(xy)
    s = (xy - c) @ u
    t = (xy - c) @ v
    i_south = min(order, key=lambda i: s[i])
    i_north = max(order, key=lambda i: s[i])
    ks = order.index(i_south)
    kn = order.index(i_north)
    lo, hi = sorted((ks, kn))
    arc1 = order[lo:hi + 1]                       # 南→北 的一条半圈
    arc2 = order[hi:] + order[:lo + 1]            # 另一条半圈
    # 哪条是西侧：看该半圈上孔的横向坐标 t 的均值，小的那条是西侧
    m1 = float(np.mean([t[i] for i in arc1]))
    m2 = float(np.mean([t[i] for i in arc2]))
    west_arc, east_arc = (arc1, arc2) if m1 <= m2 else (arc2, arc1)
    left = list(west_arc)
    right = list(east_arc)
    if s[left[0]] > s[left[-1]]:
        left = list(reversed(left))
    if s[right[0]] > s[right[-1]]:
        right = list(reversed(right))
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


def _smooth_chain(pts, tol: float):
    """把链折线先抽稀（道格拉斯-普客）再外推：治那些"孔在横向 zigzag"造成的锯齿尖刺。"""
    if not tol or tol <= 0 or len(pts) < 3:
        return [tuple(p) for p in pts]
    ln = LineString([tuple(p) for p in pts]).simplify(float(tol))
    return [tuple(c[:2]) for c in ln.coords]


def _end_mids(end_hole, waste, ref_dir, radius=END_SEARCH_R, beyond_only=True):
    """端部闭合：端孔与**端部之外**的无品位孔的中点，沿 ref_dir 排序。

    用户规则（2026-10-14）：端部"单排孔"要往**没有炮孔的一侧**推 extrude；
    另一侧（有无品位孔的一侧）用"1/2 工程间距"＝矿孔与无品位孔的中点。
    所以只认**落在端孔之外**（沿 ref_dir 前方）的无品位孔——落在矿化带内侧的
    无品位孔不能拿来当端部闭合点（0915 曾经把内侧的 P21 拿去闭合，端头拧成一团、
    4 个矿孔被甩到界外）。
    """
    mids = []
    r = np.asarray(ref_dir, float)
    for w in waste:
        d = math.hypot(end_hole.x - w.x, end_hole.y - w.y)
        if d > radius:
            continue
        if beyond_only and ((w.x - end_hole.x) * r[0]
                            + (w.y - end_hole.y) * r[1]) <= 0:
            continue                       # 无品位孔在矿化带内侧，不参与端部闭合
        mids.append(((end_hole.x + w.x) / 2.0, (end_hole.y + w.y) / 2.0))
    mids.sort(key=lambda p: (p[0] - end_hole.x) * r[0] + (p[1] - end_hole.y) * r[1])
    return mids


def _arc_through_north(poly: Polygon, a, b, prefer: str = "short"):
    """沿多边形外环取一条从 a 到 b 的弧（返回含端点的坐标表）。

    prefer="short" ：取更短的那条（1004 那种"大轮廓把整条矿化带包住"的情况，
                     按最北顶点选弧会绕地球一圈，必须按长度选）；
    prefer="north" ：取经过最北顶点的那条（1008 的历史行为）。
    """
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
    if prefer == "short":
        len1 = sum(math.hypot(arc1[k + 1][0] - arc1[k][0], arc1[k + 1][1] - arc1[k][1])
                   for k in range(len(arc1) - 1))
        len2 = sum(math.hypot(arc2[k + 1][0] - arc2[k][0], arc2[k + 1][1] - arc2[k][1])
                   for k in range(len(arc2) - 1))
        pick = arc1 if len1 <= len2 else arc2
    else:
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
        layer, poly = item[0], item[2]
        if COMPOSITE_BLOCK_LAYERS is not None and layer not in COMPOSITE_BLOCK_LAYERS:
            # 图层 0 的整片采场轮廓不是历史矿块（并进来会把环拆散）
            continue
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


def class_clusters(ore, all_holes=None, min_fragment: float = 0.0,
                   same=None, solo=None, exclude=None, exact=None):
    """把矿孔按"品位档 + 单元相接"分成簇（**每簇一块**，簇之间留空白）。

    3960 平台的人工图就是这么画的：块是一段段互不相连的**窄条带**
    （一块只装 1~3 个孔，条带之间是未圈闭的空白），而不是"整条矿化带外扩一大块"。
    做法：全场孔做 Voronoi（含废孔——邻孔的分界线能把领地挡住），
    同档且单元相接的孔并成一簇。
    """
    from oreblocks import level_of
    ex = set()
    for x in (exclude or []):
        ex.add(str(x))
    ore = [h for h in ore if h.short not in ex]
    if not ore:
        return []
    # exact：这些孔**精确地**构成一个簇（先按它切出来，剩下的再自动分簇）
    fixed = []
    for names in (exact or []):
        want = {str(n) for n in names}
        got = [h for h in ore if h.short in want]
        if len(got) >= 1:
            fixed.append(got)
            ore = [h for h in ore if h.short not in want]
    if not ore:
        return fixed
    box = MultiPoint([(h.x, h.y) for h in ore]).convex_hull.buffer(60.0)
    cells = _cells_within(all_holes or ore, box)
    groups = []
    for lid in ("L4", "L3", "L2", "L1"):
        sub = [h for h in ore if level_of(h.grade)[0] == lid and h.hid in cells]
        for grp in _components_of(cells, sub):
            groups.append(list(grp))
    if min_fragment and min_fragment > 0:
        def area_of(g):
            return sum(cells[h.hid].area for h in g)

        def nb(a, b):
            return any(cells[x.hid].distance(cells[y.hid]) < 1e-6
                       for x in a for y in b)

        def avg(g):
            return sum(h.grade_disp for h in g) / len(g)

        locked = set()
        while True:
            cand = [i for i, g in enumerate(groups)
                    if i not in locked and area_of(g) < min_fragment]
            if not cand:
                break
            i = min(cand, key=lambda k: area_of(groups[k]))
            near = [k for k in range(len(groups)) if k != i and nb(groups[i], groups[k])]
            if not near:
                locked.add(i)
                continue
            k = min(near, key=lambda t: abs(avg(groups[t]) - avg(groups[i])))
            groups[k] = groups[k] + groups[i]
            groups.pop(i)
            locked = {t if t < i else t - 1 for t in locked if t != i}
    # ---- 人工指定（验收时逐个炮区点一下）----
    # solo：这些孔各自单独成簇（从原来的簇里拆出来）
    for names in (solo or []):
        want = {str(n) for n in (names if isinstance(names, (list, tuple)) else [names])}
        got = []
        rest = []
        for g in groups:
            hit = [h for h in g if h.short in want]
            if hit:
                got += hit
                if len(hit) < len(g):
                    rest.append([h for h in g if h.short not in want])
            else:
                rest.append(g)
        if got:
            rest.append(got)
        groups = rest
    # same：这些孔算同一簇（把它们所在的簇并起来）
    for names in (same or []):
        want = {str(n) for n in names}
        hit = [k for k, g in enumerate(groups) if any(h.short in want for h in g)]
        if len(hit) < 2:
            continue
        base = hit[0]
        for k in sorted(hit[1:], reverse=True):
            groups[base] = groups[base] + groups[k]
            groups.pop(k)
    return fixed + groups


def block_of_cluster(grp, ring, all_holes, density_waste: float = 2.65,
                     density_ore: float = 2.7):
    """clusters 模式用：**一个孔簇 = 一块**（不再簇内二次分组）。

    块范围 = 该簇的矿界；块内所有孔的单元（含圈进来的废孔）按用户口径算量：
    体积 = Σ(单元面积×孔长)；重量 = Σ(单元面积×孔长×容重[该孔所在档])；
    品位 = 按**孔心落在块内**的孔做长度加权（<0.5 废孔也参与）。
    """
    from oreblocks import Block, Cell, level_of
    if not grp or ring is None or ring.is_empty:
        return None
    cellmap = _cells_within(all_holes, ring)
    hs = [h for h in all_holes if h.hid in cellmap and ring.buffer(1e-9).contains(Point(h.x, h.y))]
    for h in grp:
        if h not in hs:
            hs.append(h)
    cs = [Cell(hid=h.hid, hole=h, polygon=cellmap[h.hid], area_m2=cellmap[h.hid].area)
          for h in hs if h.hid in cellmap]
    if not cs:
        return None
    lsum = sum(h.grade_lenght for h in hs)
    grade = (sum(h.grade_lenght * h.grade_disp for h in hs) / lsum) if lsum else 0.0
    lid, label = level_of(grade)
    if lid is None:
        return None
    b = Block(level_id=lid, label=label, holes=list(grp), cells=cs)
    b.area_m2 = sum(c.area_m2 for c in cs)
    b.volume_m3 = sum(c.area_m2 * c.hole.grade_lenght for c in cs)
    b.tonnage_t = sum(c.area_m2 * c.hole.grade_lenght *
                      (density_waste if c.hole.grade < 0.5 else density_ore) for c in cs)
    b.grade = grade
    b.metal_hg = b.tonnage_t * grade / 100.0
    b.polygon = _safe_union([c.polygon for c in cs])
    return b


def isolated_ring(zone, all_holes, extrude: float, simplify: float = None,
                  method: str = "territory"):
    """孤立小组的矿界（规则）：

      「该组的孔在**全场** Voronoi 里的领地，上限是"该组凸包外扩 extrude"」。

    好处：邻孔的分界线天然把领地挡住，所以块里不会圈进邻孔（哪怕它离得近）；
    没有邻孔的方向则一直扩到"凸包外扩 extrude"。
    实证（0922 的 4 孔组，extrude=9 m）：环 372.7 m²（人工 334.3）、体积 3934
    （人工 3503）、**品位 0.8237（人工 0.824）**、**重量/体积 2.7000（人工 2.7000）**、
    块内孔心只有该组 4 个孔——人工那块也是这个特征。
    """
    if not zone:
        return None
    hull = MultiPoint([(h.x, h.y) for h in zone]).convex_hull
    if method == "hull":
        # 直边条带：直接用"孔簇凸包 + 外推"（人工图是一段段直边条带；
        # Voronoi 领地那种锯齿边虽然能挡住邻孔，但形状不像）
        poly = hull.buffer(float(extrude), join_style="mitre").buffer(0)
        simp = SIMPLIFY_M if simplify is None else float(simplify)
        if simp > 0:
            sp = poly.simplify(simp, preserve_topology=True)
            if not sp.is_empty and sp.area > 0.5 * poly.area:
                poly = sp
        LAST_RING["warn"] = []
        return poly
    cap = hull.buffer(float(extrude), join_style="mitre")
    cellmap = _cells_within(all_holes, cap)
    parts = [cellmap[h.hid] for h in zone if h.hid in cellmap]
    if not parts:
        return None
    poly = _safe_union(parts).buffer(0)
    simp = SIMPLIFY_M if simplify is None else float(simplify)
    if simp > 0:
        sp = poly.simplify(simp, preserve_topology=True)
        if not sp.is_empty and sp.area > 0.5 * poly.area:
            poly = sp
    LAST_RING["warn"] = []
    return poly


def _finish_ring(poly, ore, extrude, simplify, repair_tip=None):
    """收尾：抽稀 → 自检（必须整块且包住所有矿孔）→ 修补。"""
    LAST_RING["merged_block"] = LAST_RING.get("merged_block")
    simp = SIMPLIFY_M if simplify is None else float(simplify)
    if simp > 0:
        sp = poly.simplify(simp, preserve_topology=True)
        if not sp.is_empty and sp.area > 0.5 * poly.area:
            poly = sp
    warn = []
    if poly.geom_type == "MultiPolygon":
        warn.append("矿界原本碎成 %d 片" % len(poly.geoms))
        poly = _safe_union(list(poly.geoms))
    out = [h for h in ore if not poly.contains(Point(h.x, h.y))]
    if out:
        warn.append("%d 个矿孔原本落在矿界外（%s）"
                    % (len(out), "、".join(h.short for h in out[:6])))
        # 用"廊道"把外面的孔接回主环：从主环上最近的点拉一条 extrude 粗的带
        for h in out:
            pt = Point(h.x, h.y)
            rings = [poly.exterior] if poly.geom_type == "Polygon" else \
                [g.exterior for g in poly.geoms]
            near = min((nearest_points(r, pt)[0] for r in rings),
                       key=lambda q: q.distance(pt))
            d = np.array([h.x - near.x, h.y - near.y], float)
            n = np.linalg.norm(d)
            d = d / n if n > 1e-9 else np.array([1.0, 0.0])
            # 端头也留足 extrude：修补出来的矿界也要保证"孔到界 ≈ 3 m"，
            # 否则孔会贴着边界（0915 修补后曾只有 0.8 m）
            # 修补廊道别比"3 m 量级"还粗：0915（外推 3 m）要留足余量，
            # 0922（外推 8 m）照 8 m 撑开会把体积顶上去，所以两头都封顶。
            half = min(extrude + 0.2, 4.0)
            # repair_tip<0 = "自动"（extrude+0.8，最多 4 m）；否则用给定值
            if repair_tip is None:
                tip_ext = 0.8
            elif float(repair_tip) < 0:
                tip_ext = min(extrude + 0.8, 4.0)
            else:
                tip_ext = float(repair_tip)
            tip = (h.x + d[0] * tip_ext, h.y + d[1] * tip_ext)
            poly = _safe_union([poly, LineString([near, tip]).buffer(
                half, join_style="mitre", cap_style="flat")])
            poly = poly.buffer(0.1, join_style="mitre").buffer(
                -0.1, join_style="mitre")
        rest = [h.short for h in ore if not poly.contains(Point(h.x, h.y))]
        if rest:
            warn.append("仍在外：%s" % "、".join(rest))
    if poly.geom_type != "Polygon":
        poly = max(poly.geoms, key=lambda g: g.area)
    LAST_RING["warn"] = warn
    return poly


def _alpha_ring(ore, all_holes, extrude: float, comp_blocks, merge_gap: float,
                blast: str, k: float, end_pair_beyond: bool = True):
    """外轮廓环：矿孔凹包 + 外推，再把北端闭合与南端接综合图的"走廊"补进来。

    专治"孔列多、走向弯"的矿带——那时按走向中线分左右链会把外圈孔判成内部孔，
    链式外推就少包一块（0915 的 P14、P32 就是这样）。
    """
    xy = np.array([(h.x, h.y) for h in ore], float)
    sh = _alpha_shape(xy, k)
    if sh is None or sh.is_empty:
        return None
    if sh.geom_type != "Polygon":
        sh = max(sh.geoms, key=lambda g: g.area)
    poly = sh.buffer(extrude, join_style="mitre").buffer(0)
    c, u, v = _pca(xy)
    s_all = (xy - c) @ u
    waste = [h for h in all_holes if h.grade < 0.5]
    span = float(s_all.max() - s_all.min())
    band = max(12.0, 0.35 * span)

    def end_mids(want_north: bool):
        lo, hi = (s_all.max() - band, 1e18) if want_north else (-1e18, s_all.min() + band)
        sel = [j for j in range(len(ore)) if lo <= s_all[j] <= hi]
        mids = []
        for j in sel:
            mids += _end_mids(ore[j], waste, u if want_north else -u, radius=12.0,
                              beyond_only=end_pair_beyond)
        return mids

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
    if north and len(north) >= 2:
        poly = _safe_union([poly, LineString([tuple(p) for p in north]).buffer(
            max(1.5, extrude * 0.8), join_style="mitre")]).buffer(0)

    left, right, c2, u2, v2 = zone_chains(ore, all_holes)
    xy_l = np.array([(ore[j].x, ore[j].y) for j in left], float)
    xy_r = np.array([(ore[j].x, ore[j].y) for j in right], float)
    if len(xy_l) and len(xy_r):
        le = tuple(_offset_chain([xy_l[0]], c, extrude, outward=-v)[0])
        re_ = tuple(_offset_chain([xy_r[0]], c, extrude, outward=v)[0])
        south, merged_block = south_closure(le, re_, comp_blocks, merge_gap)
        LAST_RING["merged_block"] = merged_block
        if south and len(south) >= 2:
            poly = _safe_union([poly, LineString([tuple(p) for p in south]).buffer(
                max(1.5, extrude * 0.8), join_style="mitre")]).buffer(0)
    return poly


def zone_outline(ore, all_holes, extrude: float = EXTRUDE_M,
                 comp_blocks=None, merge_gap: float = SOUTH_MERGE_GAP,
                 blast: str = None, simplify: float = None,
                 alpha_k: float = 0.0, chain_mode: str = "pca",
                 ring_mode: str = "chain", chain_left=(), chain_right=(),
                 chain_exclude=None, chain_smooth_m: float = 0.0,
                 repair_tip_m: float = None, end_pair_beyond: bool = True):
    """整条矿化带的外围矿界（复刻人工图的折线结构：11~21 个拐点）。

    人工图的画法（由其 .3ds 逐步还原）：
      西侧 = 左链（西侧那列孔）逐段沿局部法向外推 3 m；
      东侧 = 右链（东侧那列孔）逐段沿局部法向外推 3 m；
      两端 = 端部矿孔与**相邻无品位孔的中点**连成折线（这就是"辅助线中点"）；
      若某端外侧没有炮孔 → 该端沿走向再推 3 m（不横穿炮孔）。
    """
    if len(ore) < 2:
        return None
    if ring_mode == "alpha":
        poly = _alpha_ring(ore, all_holes, extrude, comp_blocks, merge_gap,
                           blast, alpha_k or 2.0, end_pair_beyond=end_pair_beyond)
        if poly is not None and not poly.is_empty:
            poly = _finish_ring(poly, ore, extrude, simplify, repair_tip_m)
            LAST_RING["merged_block"] = LAST_RING.get("merged_block")
            return poly
    if chain_mode == "alpha":
        left, right, c, u, v = zone_chains_alpha(
            ore, all_holes, k=(alpha_k if alpha_k and alpha_k > 0 else 2.0))
    else:
        left, right, c, u, v = zone_chains(
            ore, all_holes, manual_left=chain_left or (),
            manual_right=chain_right or (),
            exclude=(None if chain_exclude is None else tuple(chain_exclude)))
    xy = np.array([(h.x, h.y) for h in ore], float)
    waste = [h for h in all_holes if h.grade < 0.5]
    csm = float(chain_smooth_m or 0.0)
    west = _offset_chain(_smooth_chain([xy[j] for j in left], csm), c, extrude,
                         outward=-v)
    east = _offset_chain(_smooth_chain([xy[j] for j in right], csm), c, extrude,
                         outward=v)
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
            mids += _end_mids(ore[j], waste, u if want_north else -u, radius=12.0,
                              beyond_only=end_pair_beyond)
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
    if alpha_k and alpha_k > 0:
        # 宽/弯矿化带的兜底：并上"矿孔外轮廓 + extrude"的外推环
        sh = _alpha_shape(xy, float(alpha_k))
        if sh is not None and not sh.is_empty:
            poly = _safe_union([poly, sh.buffer(extrude, join_style="mitre")]).buffer(0)
    LAST_RING["merged_block"] = merged_block
    LAST_RING["ring"] = ring
    return _finish_ring(poly, ore, extrude, simplify, repair_tip_m)


def _voronoi_cells(ore, clip: Polygon):
    """矿孔 Voronoi 单元裁剪到 clip。"""
    return _cells_within(ore, clip)


def read_3ds_polylines(path):
    """读 3DMine 导出的 .3ds 字符串文件，返回若干条折线的 (E, N) 坐标表。

    文件里顶点行形如 `1,<N>,<E>,<Z>,[附加属性...]`；表头行也是 `1,7,0,1.00,...`
    开头（早期版本把它当顶点会多出一个 (0,7) 假点），所以这里要求第 2、3 段
    解析成"像坐标"的数（量级 ≥ 1e4）才算顶点。
    """
    from pathlib import Path
    txt = Path(path).read_bytes().decode("gbk", "replace")
    out, cur = [], []
    for line in txt.splitlines():
        s = line.strip()
        if not s:
            continue
        parts = [x.strip() for x in s.split(",")]
        if parts and parts[0] == "1" and len(parts) >= 4:
            try:
                n = float(parts[1])
                e = float(parts[2])
            except ValueError:
                n = e = 0.0
            if abs(n) >= 1e4 and abs(e) >= 1e4:
                cur.append((e, n))                  # X = E, Y = N
                continue
        if cur:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return [c for c in out if len(c) >= 2]


def ring_from_outline_files(paths, tol: float = 0.35):
    """精确模式：把人工在 3DMine 里画好的几段线拼成一个闭合矿界。

    用户 2026-10-08 就是这么给 1008 的（左边界已外推 / 与综合图边界 /
    右边界已外推 / 右上边界），拼接顺序按"端点最近"自动串起来（首尾相接），
    不需要人工排序；串好后若首尾不重合，再回到起点闭合。
    """
    segs = []
    for p in paths:
        segs += [list(map(tuple, s)) for s in read_3ds_polylines(p)]
    if not segs:
        return None
    if len(segs) == 1:
        pts = segs[0]
        if math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) > 0.01:
            pts = pts + [pts[0]]
        poly = Polygon(pts).buffer(0)
        return poly if not poly.is_empty else None
    # 贪心串线：每次找端点离当前末端最近的一段（两端都试）
    cur = list(segs.pop(0))
    while segs:
        best = None
        for i, s in enumerate(segs):
            for rev in (False, True):
                pts = list(reversed(s)) if rev else list(s)
                d = math.hypot(pts[0][0] - cur[-1][0], pts[0][1] - cur[-1][1])
                if best is None or d < best[0]:
                    best = (d, i, rev, pts)
        d, i, rev, pts = best
        if d > max(tol, 5.0):
            break
        segs.pop(i)
        cur += pts[1:] if d < 1e-9 else pts
    if math.hypot(cur[0][0] - cur[-1][0], cur[0][1] - cur[-1][1]) > 0.01:
        cur.append(cur[0])
    poly = Polygon(cur).buffer(0)
    if poly.is_empty:
        return None
    if poly.geom_type == "MultiPolygon":
        poly = max(poly.geoms, key=lambda g: g.area)
    return poly


def join_to_composite(ring, comp_blocks, gap: float = 0.5):
    """把"贴着综合图历史矿块"的那条窄边吸收进来（用户规则：能并在一起就并在一起）。

    只吸收**本来就贴着**的部分：历史矿块在矿界外侧、且两条边界的间距 ≤ gap。
    离得远的历史矿块（> gap）一点不动——那属于用户说的"不能并在一起"。
    这样等于把矿界在那一段**改走历史矿块的边界**（人工图北缘就是这么画的：
    0915 的北边界压在 1003 那块 626.9 m² 的边上，比外推 3 m 再往外 1.5~2 m）。
    吸收进来的面积照常参与算量（用户 2026-10-14：体积必须与自己实际圈的矿一致）。
    """
    if ring is None or ring.is_empty or not comp_blocks or gap <= 0:
        return ring
    collar = ring.buffer(gap, join_style="mitre").difference(ring)
    parts = []
    for item in comp_blocks:
        blk = item[2] if isinstance(item, (tuple, list)) and len(item) >= 3 else item
        if blk is None or blk.is_empty:
            continue
        if blk.distance(ring) > gap:
            continue
        part = blk.difference(ring).intersection(collar)
        if part.is_empty:
            continue
        parts.append(part)
    if not parts:
        return ring
    out = _safe_union([ring] + parts)
    if out is None or out.is_empty:
        return ring
    if out.geom_type == "MultiPolygon":
        d = gap + 0.1
        closed = out.buffer(d, join_style="mitre").buffer(-d, join_style="mitre")
        if not closed.is_empty:
            out = closed
    return out


def blocks_from_outline_files(paths, all_holes, density_waste: float = 2.65,
                             density_ore: float = 2.7, min_area: float = 1.0):
    """人工圈矿模式：**每条闭合折线 = 一块**，程序只算量、不再自己圈。

    用户 2026-10-15 的用法：他在 3DMine 里自己画好矿块（导出成 .3ds，一条闭合线一块），
    丢给程序算量出图。这里的口径跟自动模式保持一致（`口径确认记录.md` A/C2 节）：

      * 块范围 = 那条闭合线围出来的多边形（原样用，不抽稀、不外推）；
      * 体积   = Σ(全场孔 Voronoi 单元 ∩ 块范围 的面积 × 该孔 gradeLenght)；
      * 重量   = 同样求和，但每个单元按**该孔所在档**取容重（<0.5 取 2.65，其余 2.7）；
      * 品位   = **孔心落在块内**的孔做长度加权（<0.5 废孔也参与）；
                块内一个孔心都没有时，退化成"单元面积×孔长"加权，免得算不出品位；
      * 金属量 = 重量 × 品位 ÷ 100（百克，3 位小数）；
      * 体号   = 按品位档从高到低、同档按体积从大到小重排（与人工报告版式一致）。

    返回 (rings, blocks)：rings 是这些块的多边形（出图用），blocks 是 Block 列表。
    """
    from oreblocks import Block, Cell, level_of
    polys = []
    for p in paths:
        for pts in read_3ds_polylines(p):
            if len(pts) < 3:
                continue
            if math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) > 0.01:
                pts = list(pts) + [pts[0]]          # 没闭合就补上
            poly = Polygon(pts).buffer(0)
            if poly.is_empty:
                continue
            if poly.geom_type == "MultiPolygon":
                poly = max(poly.geoms, key=lambda g: g.area)
            if poly.area < float(min_area):
                continue
            polys.append(poly)
    if not polys:
        return [], []
    out_blocks = []
    for poly in polys:
        cellmap = _cells_within(all_holes, poly)
        byh = {h.hid: h for h in all_holes}
        cs = [Cell(hid=k, hole=byh[k], polygon=c, area_m2=c.area)
              for k, c in cellmap.items() if byh[k].hid in byh]
        if not cs:
            continue
        hs_in = [h for h in all_holes
                 if poly.buffer(1e-9).contains(Point(h.x, h.y))]
        if hs_in:
            lsum = sum(h.grade_lenght for h in hs_in)
            grade = (sum(h.grade_lenght * h.grade_disp for h in hs_in) / lsum
                     if lsum else 0.0)
        else:                                   # 块里没有孔心 → 用单元加权兜底
            w = sum(c.area_m2 * c.hole.grade_lenght for c in cs)
            grade = (sum(c.area_m2 * c.hole.grade_lenght * c.hole.grade_disp for c in cs) / w
                     if w else 0.0)
        lid, label = level_of(grade)
        if lid is None:
            # 平均品位 <0.5 的整块（人工圈进来的废石区）：列成 0.5-1 以下的一块，
            # 让报告里也能看到它，而不是悄悄丢掉。
            lid, label = "L0", "<0.500"
        b = Block(level_id=lid, label=label, holes=list(hs_in), cells=cs)
        b.area_m2 = sum(c.area_m2 for c in cs)
        b.volume_m3 = sum(c.area_m2 * c.hole.grade_lenght for c in cs)
        b.tonnage_t = sum(c.area_m2 * c.hole.grade_lenght *
                          (density_waste if c.hole.grade < 0.5 else density_ore)
                          for c in cs)
        b.grade = grade
        b.metal_hg = b.tonnage_t * grade / 100.0
        b.polygon = poly                        # 出图用人工画的那条线
        out_blocks.append(b)
    order = {"L4": 0, "L3": 1, "L2": 2, "L1": 3, "L0": 4}
    out_blocks.sort(key=lambda b: (order.get(b.level_id, 9), -b.volume_m3))
    for i, b in enumerate(out_blocks, 1):
        b.no = i
    rings = [b.polygon for b in out_blocks]
    return rings, out_blocks


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


def _components_of(cellmap, hs):
    """按单元相接把 hs 分成若干连通组。"""
    used = [False] * len(hs)
    comps = []
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
                if any(cellmap[a.hid].distance(cellmap[hs[j].hid]) < 1e-6 for a in grp):
                    grp.append(hs[j])
                    used[j] = True
                    changed = True
        comps.append(grp)
    return comps


def average_blocks(ore, outline, density: float,
                   min_fragment: float = MIN_FRAGMENT_M2,
                   merge_target: str = "avg", merge_gap: float = 0.0,
                   same_block=None, all_holes=None,
                   density_waste: float = 2.65, density_ore: float = 2.7):
    """分块定档（人工口径）：

      ① 每个矿孔一个 Voronoi 单元，裁剪到矿界；
      ② 同品位档且单元相接的孔先并成一组；
      ③ 面积小于 min_fragment 的同档碎片，并入相邻组里**平均品位最接近**的那组
         （人工图里 0.70 的单孔会并进旁边的高品位块，而 44 m² 的 0.61 单孔块保留）；
      ④ 每块最后按**整块平均品位**所在档定档，体号高档在前。
    """
    from oreblocks import Block, Cell, level_of

    if outline is None or not ore:
        return []
    cells = _voronoi_cells(ore, outline)
    hs = [h for h in ore if h.hid in cells]
    if not hs:
        return []
    groups = []
    for lid in ("L4", "L3", "L2", "L1"):
        sub = [h for h in hs if level_of(h.grade)[0] == lid]
        for grp in _components_of(cells, sub):
            groups.append({"holes": list(grp)})
    for g in groups:
        g["area"] = sum(cells[h.hid].area for h in g["holes"])
        g["avg"] = sum(h.grade_disp for h in g["holes"]) / len(g["holes"])
    locked = set()
    while True:
        cand = [i for i, g in enumerate(groups)
                if i not in locked and g["area"] < min_fragment]
        if not cand:
            break
        i = min(cand, key=lambda k: groups[k]["area"])
        g = groups[i]
        nb = [k for k, h in enumerate(groups) if k != i and any(
            cells[x.hid].distance(cells[y.hid]) < 1e-6
            for x in g["holes"] for y in h["holes"])]
        if not nb:
            locked.add(i)
            continue
        def score(t):
            if merge_target == "shared":       # 共用边界最长
                return -sum(cells[x.hid].intersection(cells[y.hid]).length
                            for x in g["holes"] for y in groups[t]["holes"]
                            if cells[x.hid].distance(cells[y.hid]) < 1e-6)
            return abs(groups[t]["avg"] - g["avg"])   # 平均品位最接近

        k = min(nb, key=score)
        groups[k]["holes"] += g["holes"]
        groups[k]["area"] += g["area"]
        groups[k]["avg"] = (sum(h.grade_disp for h in groups[k]["holes"])
                            / len(groups[k]["holes"]))
        groups.pop(i)
        locked = {t if t < i else t - 1 for t in locked if t != i}

    # 相邻块再合并：两块的**平均品位差**小于 merge_gap 就并成一块
    # （1004 人工图把 {P1,P2,P3}(2.18) 和 {P4,P6}(1.38) 并成了一块 1.85，
    #  而 725 那块(0.82) 与它差 1.0，没并——所以这是按炮区标定的开关）
    if merge_gap and float(merge_gap) > 0:
        gap = float(merge_gap)
        changed = True
        while changed and len(groups) > 1:
            changed = False
            for i in range(len(groups)):
                for j in range(len(groups)):
                    if i == j:
                        continue
                    gi, gj = groups[i], groups[j]
                    if abs(gi["avg"] - gj["avg"]) > gap:
                        continue
                    if not any(cells[x.hid].distance(cells[y.hid]) < 1e-6
                               for x in gi["holes"] for y in gj["holes"]):
                        continue
                    lo, hi = sorted((i, j))
                    groups[lo]["holes"] += groups[hi]["holes"]
                    groups[lo]["area"] += groups[hi]["area"]
                    groups[lo]["avg"] = (sum(h.grade_disp for h in groups[lo]["holes"])
                                         / len(groups[lo]["holes"]))
                    groups.pop(hi)
                    changed = True
                    break
                if changed:
                    break

    # 人工指定"这些孔算同一块"：把包含它们的那些组并起来
    # （1004 人工图把 {P1,P2,P3}(2.18) 与 {P4,P6}(1.38) 并成一块 1.85）
    for names in (same_block or []):
        want = set(names)
        hit = [k for k, g in enumerate(groups)
               if any(h.short in want for h in g["holes"])]
        if len(hit) < 2:
            continue
        base = hit[0]
        for k in sorted(hit[1:], reverse=True):
            groups[base]["holes"] += groups[k]["holes"]
            groups[base]["area"] += groups[k]["area"]
            groups.pop(k)
        groups[base]["avg"] = (sum(h.grade_disp for h in groups[base]["holes"])
                               / len(groups[base]["holes"]))

    out = []
    # 全场 Voronoi（含废孔）裁到矿界：3DMine 是"整爆区做 voronoi，再拿块的多边形去裁"
    _allcells = _cells_within(all_holes, outline) if all_holes else {}
    for g in groups:
        grp = sorted(g["holes"], key=lambda h: -h.grade_disp)
        lid, label = level_of(g["avg"])
        if lid is None:
            continue
        region = _safe_union([cells[h.hid] for h in grp])
        # ---- 块内算量（用户口径：<0.5 废孔不圈矿，但参与块内算量）----
        # 体积/重量：拿**全场**孔的 Voronoi 单元去裁块范围——邻孔单元被裁进来的那一块
        #   也算（3DMine 就是这么算的），容重按该单元那个孔的档取（<0.5 → 2.65）。
        # 品位：只按**孔心落在块内**的孔做长度加权。
        #   实证：1004 那块 725 m² 含 8 个废孔心 → 0.684 ≈ 报告 0.6919；
        #         0922 孤立 4 孔组的废孔心在块外 → 0.824 ≈ 报告 0.824。
        if _allcells:
            cs = []
            for h in all_holes:
                c = _allcells.get(h.hid)
                if c is None:
                    continue
                part = c.intersection(region)
                if part.is_empty or part.area <= 1e-9:
                    continue
                cs.append(Cell(hid=h.hid, hole=h, polygon=part, area_m2=part.area))
        else:
            cs = [Cell(hid=h.hid, hole=h, polygon=cells[h.hid],
                       area_m2=cells[h.hid].area) for h in grp]
        pts = [h for h in (all_holes or grp)
               if region.buffer(1e-9).contains(Point(h.x, h.y))]
        for h in grp:
            if h not in pts:
                pts.append(h)
        b = Block(level_id=lid, label=label, holes=grp, cells=cs)
        b.compute(density)
        if len(cs) != len(grp) or len(pts) != len(grp):
            # 含废孔：体积/重量/品位按"所有孔"重算
            vol = sum(c.area_m2 * c.hole.grade_lenght for c in cs)
            ton = sum(c.area_m2 * c.hole.grade_lenght *
                      (density_waste if c.hole.grade < 0.5 else density_ore)
                      for c in cs)
            lsum = sum(h.grade_lenght for h in pts)
            grade = (sum(h.grade_lenght * h.grade_disp for h in pts) / lsum
                     if lsum else 0.0)
            b.area_m2 = sum(c.area_m2 for c in cs)
            b.volume_m3 = vol
            b.tonnage_t = ton
            b.grade = grade
            b.metal_hg = ton * grade / 100.0
            b.acct_holes = [c.hole for c in cs]
        out.append(b)
    order = {"L4": 0, "L3": 1, "L2": 2, "L1": 3}
    out.sort(key=lambda b: (order.get(b.level_id, 9), -b.volume_m3))
    for i, b in enumerate(out, 1):
        b.no = i
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
