# -*- coding: utf-8 -*-
"""
mining_rules：采矿工程约束规则（多边形层面）
---------------------------------------------
对应项目计划书 4.3 节：边界平滑与简化、平直化（去锯齿）。
依赖最小：仅 numpy，多边形面积用鞋带公式，简化用 Douglas-Peucker。
"""
from __future__ import annotations

import numpy as np


def polygon_area(poly: np.ndarray) -> float:
    """鞋带公式计算多边形有向面积（逆时针为正）。poly: (N,2)。"""
    x = poly[:, 0]
    y = poly[:, 1]
    return float(0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def close_polygon(poly: np.ndarray) -> np.ndarray:
    """返回闭合多边形（首尾点相同），便于写入 3DMine .str。"""
    poly = np.asarray(poly, dtype=float)
    if not np.allclose(poly[0], poly[-1]):
        poly = np.vstack([poly, poly[0]])
    return poly


def _perpendicular_distance(pt: np.ndarray, a: np.ndarray, b: np.ndarray) -> float:
    """点 pt 到线段 ab 的垂直距离。"""
    ab = b - a
    ab_len2 = float(ab @ ab)
    if ab_len2 < 1e-12:
        return float(np.hypot(*(pt - a)))
    t = np.clip(float((pt - a) @ ab) / ab_len2, 0.0, 1.0)
    proj = a + t * ab
    return float(np.hypot(*(pt - proj)))


def simplify_douglas_peucker(poly: np.ndarray, tolerance: float) -> np.ndarray:
    """Douglas-Peucker 边界简化，去除冗余节点（计划书 4.3 边界平滑与简化）。"""
    if len(poly) <= 3:
        return poly

    def dp(points: np.ndarray) -> np.ndarray:
        if len(points) <= 2:
            return points
        dmax, idx = 0.0, 0
        for i in range(1, len(points) - 1):
            d = _perpendicular_distance(points[i], points[0], points[-1])
            if d > dmax:
                dmax, idx = d, i
        if dmax > tolerance:
            left = dp(points[: idx + 1])
            right = dp(points[idx:])
            return np.vstack([left[:-1], right])
        return np.array([points[0], points[-1]])

    closed = np.allclose(poly[0], poly[-1])
    pts = poly[:-1] if closed else poly
    # 环形处理：从最远两点间切开再简化
    n = len(pts)
    if n <= 3:
        return poly
    # 找离质心最远的点作为起点，避免闭合环被首点截断
    centroid = pts.mean(axis=0)
    start = int(np.argmax(np.hypot(*(pts - centroid).T)))
    rotated = np.roll(pts, -start, axis=0)
    rotated = np.vstack([rotated, rotated[0]])
    simplified = dp(rotated)
    if np.allclose(simplified[0], simplified[-1]):
        simplified = simplified[:-1]
    if len(simplified) < 3:
        simplified = pts
    return close_polygon(simplified)


def straighten_edges(poly: np.ndarray, min_edge_len: float) -> np.ndarray:
    """平直化：合并长度小于铲头宽度的短边，去除锯齿拐点（计划书 4.3）。

    迭代合并相邻短边，保留多边形闭合性。
    """
    poly = np.asarray(poly, dtype=float)
    if np.allclose(poly[0], poly[-1]):
        poly = poly[:-1]
    if len(poly) <= 3:
        return close_polygon(poly)

    changed = True
    while changed and len(poly) > 3:
        changed = False
        n = len(poly)
        for i in range(n):
            a = poly[i]
            b = poly[(i + 1) % n]
            if np.hypot(*(b - a)) < min_edge_len:
                # 删除短边端点 b
                poly = np.delete(poly, (i + 1) % n, axis=0)
                changed = True
                break
    return close_polygon(poly)


def filter_by_area(polys: list[np.ndarray], min_area_m2: float) -> list[np.ndarray]:
    """按最小可采块体面积过滤多边形（网格规则已处理，此处兜底复核）。"""
    kept = [p for p in polys if polygon_area(p) >= min_area_m2]
    dropped = len(polys) - len(kept)
    if dropped:
        print(f"[规则-面积复核] 过滤 {dropped} 个面积不足的小多边形。")
    return kept
