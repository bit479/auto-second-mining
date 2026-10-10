# -*- coding: utf-8 -*-
"""品位界限的**通用自动生成**（不依赖任何炮区孔号）。

人工画法（用户 1008 逐点口述并验算）：
  品位界限 = "相邻但品位档不同"的两孔的中点，依次连成折线；两端沿该孔对的
  垂直平分线方向（＝Voronoi 脊线方向）延伸到外围矿界。

自动做法：
  ① 对矿孔做 Voronoi 剖分（四周加 4 个远点，保证边界上的脊线也是有限的）；
  ② 取所有"两侧炮孔分属不同品位档"的 Voronoi 脊线段（＝那两个孔的中点所在直线）；
  ③ 这些脊线段按"共用端点"连成折线，在分叉点断开，每条折线就是一条品位界限；
     折线上的每一段用它对应孔对的中点代表（人工就是这么画的，比原始 Voronoi
     锯齿更直）；
  ④ 折线两端沿端点孔对的垂直平分线方向延伸到外围矿界，再截取矿界以内的部分。

1008 验证：自动得到的 2 号界限 7 个中点与人工逐点吻合，
1 号界限（孤立脊）方向与人工线夹角 1.0°。
"""
from __future__ import annotations

import math
from collections import defaultdict

import numpy as np
from shapely.geometry import LineString
from scipy.spatial import Voronoi

from oreblocks import level_of


def _key_of(li, lj):
    return "-".join(sorted((li, lj)))


def _pk(pt, nd=3):
    return (round(pt[0], nd), round(pt[1], nd))


def _mid(ha, hb):
    return ((ha.x + hb.x) / 2.0, (ha.y + hb.y) / 2.0)


def _paths(segs):
    """segs = [(key, i, j, LineString)]；按共用端点连成折线，分叉处断开。"""
    bypt = defaultdict(list)
    for k, i, j, s in segs:
        c = list(s.coords)
        bypt[_pk(c[0])].append((k, i, j, s))
        bypt[_pk(c[-1])].append((k, i, j, s))
    used, paths = set(), []
    for k, i, j, s in segs:
        if id(s) in used:
            continue
        used.add(id(s))
        chain = [(k, i, j, s)]
        for forward in (True, False):
            cur_pt = list(s.coords)[-1] if forward else list(s.coords)[0]
            while True:
                here = bypt[_pk(cur_pt)]
                cand = [t for t in here if id(t[3]) not in used]
                if len(here) != 2 or len(cand) != 1:
                    break
                t = cand[0]
                used.add(id(t[3]))
                c = list(t[3].coords)
                nxt = c[-1] if _pk(c[0]) == _pk(cur_pt) else c[0]
                if forward:
                    chain.append(t)
                else:
                    chain.insert(0, t)
                cur_pt = nxt
        paths.append(chain)
    return paths


def auto_cut_lines(ore, ring, span: float = 120.0, min_ridge: float = 0.25,
                   pair_factor: float = 2.0):
    """返回 [(key, LineString), ...]：自动生成的品位界限（已截到矿界以内）。"""
    if len(ore) < 3 or ring is None or ring.is_empty:
        return []
    xy = np.array([(h.x, h.y) for h in ore], float)
    b = ring.bounds
    pad = 1e4
    extra = np.array([[b[0] - pad, b[1] - pad], [b[2] + pad, b[1] - pad],
                      [b[0] - pad, b[3] + pad], [b[2] + pad, b[3] + pad]], float)
    vor = Voronoi(np.vstack([xy, extra]))
    # 相邻判定：两孔间距不能超过 2 × 最近邻距离中位数（挡掉退化三角剖分里
    # 那种"跨过好几个孔"的长边，1008 上就是 P2-P9 那条 18.8 m 的假边）
    nn = [min(np.hypot(xy[k][0] - xy[m][0], xy[k][1] - xy[m][1])
              for m in range(len(xy)) if m != k) for k in range(len(xy))]
    max_pair = pair_factor * float(np.median(nn))
    # 同档矿孔按"相邻"分连通块：一条品位界限 = 一个"某档连通块"与"另一档"之间的
    # 整条 Voronoi 分界（人工图里 0.5-1 档分成两块，界线也就画了两条）
    same = defaultdict(set)
    for a in range(len(xy)):
        for b in range(a + 1, len(xy)):
            if math.hypot(xy[a][0] - xy[b][0], xy[a][1] - xy[b][1]) > max_pair:
                continue
            la = level_of(ore[a].grade)[0]
            lb = level_of(ore[b].grade)[0]
            if la is not None and la == lb:
                same[a].add(b)
                same[b].add(a)
    comp = {}
    cid = 0
    for a in range(len(xy)):
        if a in comp:
            continue
        stack, cid = [a], cid + 1
        while stack:
            k = stack.pop()
            if k in comp:
                continue
            comp[k] = cid
            stack += [t for t in same[k] if t not in comp]

    segs = []
    for (i, j), rv in zip(vor.ridge_points, vor.ridge_vertices):
        if i >= len(ore) or j >= len(ore):      # 与补点相连的脊，不用
            continue
        if rv[0] < 0 or rv[1] < 0:
            continue
        li = level_of(ore[i].grade)[0]
        lj = level_of(ore[j].grade)[0]
        if li is None or lj is None or li == lj:
            continue
        if math.hypot(xy[i][0] - xy[j][0], xy[i][1] - xy[j][1]) > max_pair:
            continue
        p, q = vor.vertices[rv[0]], vor.vertices[rv[1]]
        if math.hypot(p[0] - q[0], p[1] - q[1]) < min_ridge:
            continue
        group = tuple(sorted(("c%d" % comp[i], "c%d" % comp[j])))
        segs.append((group, min(i, j), max(i, j),
                     LineString([tuple(p), tuple(q)])))
    segs.sort(key=lambda t: t[0])
    out = []
    by_group = defaultdict(list)
    for s in segs:
        by_group[s[0]].append(s)
    chains = []
    for g in by_group:
        chains += _paths(by_group[g])      # 只在同一"档间分界"内部接链
    for chain in chains:
        pairs = [(i, j) for _, i, j, _ in chain]
        pts = [_mid(ore[i], ore[j]) for i, j in pairs]
        if len(pts) < 1:
            continue

        def outward_dir(idx):
            i, j = pairs[idx]
            d = np.array([ore[i].x - ore[j].x, ore[i].y - ore[j].y], float)
            n = np.linalg.norm(d)
            if n < 1e-9:
                return np.array([1.0, 0.0])
            return np.array([-d[1] / n, d[0] / n])       # 垂直平分线方向

        if len(pts) == 1:
            d = outward_dir(0)
            p0 = np.array(pts[0], float)
            line_pts = [tuple(p0 - d * span), tuple(p0 + d * span)]
        else:
            d0 = outward_dir(0)
            n0 = np.array(pts[1], float)
            if np.dot(np.array(pts[0], float) - n0, d0) < 0:
                d0 = -d0
            d1 = outward_dir(len(pts) - 1)
            n1 = np.array(pts[-2], float)
            if np.dot(np.array(pts[-1], float) - n1, d1) < 0:
                d1 = -d1
            line_pts = ([tuple(np.array(pts[0], float) + d0 * span)]
                        + [tuple(p) for p in pts]
                        + [tuple(np.array(pts[-1], float) + d1 * span)])
        ln = LineString(line_pts)
        inside = ln.intersection(ring)
        if inside.is_empty:
            continue
        geoms = [inside] if inside.geom_type == "LineString" else \
            [g for g in getattr(inside, "geoms", []) if g.geom_type == "LineString"]
        if not geoms:
            continue
        best = max(geoms, key=lambda g: g.length)
        if best.length > 0.5:
            li = level_of(ore[pairs[0][0]].grade)[0]
            lj = level_of(ore[pairs[0][1]].grade)[0]
            # 两端各往外探 0.05 m：shapely 的 split 要求切割线"穿过"边界，
            # 端点正好落在界上时它切不开
            c = list(best.coords)
            d0 = np.array(c[0], float) - np.array(c[1], float)
            d0 = d0 / (np.linalg.norm(d0) + 1e-12)
            d1 = np.array(c[-1], float) - np.array(c[-2], float)
            d1 = d1 / (np.linalg.norm(d1) + 1e-12)
            cut = LineString([tuple(np.array(c[0], float) + d0 * 0.05)]
                             + c[1:-1]
                             + [tuple(np.array(c[-1], float) + d1 * 0.05)])
            out.append((_key_of(li, lj), cut))
    return out
