# -*- coding: utf-8 -*-
"""
grid：矿块内 1m × 1m 正方形网格生成
-------------------------------------
对每个矿块多边形生成边长为 1 m 的规则网格线（裁剪至矿块内部）。
用于 CAD 出图的铲装/验收网格。
"""
from __future__ import annotations

import numpy as np
from shapely.geometry import LineString, MultiLineString, Polygon


def grid_lines_inside(polygon: Polygon, cell_size: float = 1.0) -> list[LineString]:
    """生成覆盖多边形范围的 1m（可配）网格线，并裁剪到多边形内部。

    返回网格线段列表（仅多边形内的线段）。
    """
    minx, miny, maxx, maxy = polygon.bounds
    xs = np.arange(np.floor(minx / cell_size) * cell_size, maxx + 1e-9, cell_size)
    ys = np.arange(np.floor(miny / cell_size) * cell_size, maxy + 1e-9, cell_size)

    lines: list[LineString] = []
    # 垂直线 x = const
    for x in xs:
        if x <= minx + 1e-9 or x >= maxx - 1e-9:
            continue
        line = LineString([(x, miny - cell_size), (x, maxy + cell_size)])
        clipped = line.intersection(polygon)
        lines.extend(_to_segments(clipped))
    # 水平线 y = const
    for y in ys:
        if y <= miny + 1e-9 or y >= maxy - 1e-9:
            continue
        line = LineString([(minx - cell_size, y), (maxx + cell_size, y)])
        clipped = line.intersection(polygon)
        lines.extend(_to_segments(clipped))
    return lines


def _to_segments(geom) -> list[LineString]:
    """把 intersection 结果规范为线段列表。"""
    segs = []
    if geom is None or geom.is_empty:
        return segs
    if isinstance(geom, LineString):
        segs.append(geom)
    elif isinstance(geom, MultiLineString):
        segs.extend(list(geom.geoms))
    else:
        # 极少见：线交点为点或多边形等，忽略
        pass
    return [s for s in segs if s.length > 1e-6]


__all__ = ["grid_lines_inside"]
