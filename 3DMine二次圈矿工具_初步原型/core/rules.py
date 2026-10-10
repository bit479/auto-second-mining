# -*- coding: utf-8 -*-
"""规则表驱动的品位界限（复刻人工画法）。

人工流程（用户逐步给出并逐点验算）：
  外围矿界 = 左链外推3m + 右上边界(端部辅助线中点链) + 右链外推3m + 与综合图边界(南端闭合)
  品位界限 = 由**指定孔对的中点**依次连线，两端接到外围矿界：
    1 号线（1-1.5 与 1.5-3 之间）：左矿界 -> mid(P14,P12) -> 右矿界
    2 号线（0.5-1 与 1-1.5 之间）：mid(P8,P13) -> mid(P12,P8) -> mid(P6,P7)
                                   -> mid(P5,P6) -> mid(P5,P4) -> mid(P3,P4) -> mid(P2,P4) -> 外围矿界
"""
from __future__ import annotations

import numpy as np
from shapely.geometry import LineString, Polygon
from shapely.ops import split as shp_split

# 每条品位界限：孔对序列（中点依次连线）
GRADE_LINES = {
    "L1_L2": [("P14", "P12")],
    "L2_L3": [("P8", "P13"), ("P12", "P8"), ("P6", "P7"), ("P5", "P6"),
              ("P5", "P4"), ("P3", "P4"), ("P2", "P4")],
}

# ---- 外围矿界四段（用户人工画法的完整配方，逐点验算吻合） ----
# 北端"右上边界"：从左边界上端点出发，依次连这些孔对的中点，最后接到右边界上端点
NORTH_CLOSURE_PAIRS = [("P35", "P23"), ("P23", "P24"), ("P23", "P22"),
                       ("P22", "P14"), ("P13", "P14"), ("P12", "P13"),
                       ("P11", "P8"), ("P9", "P10")]
# 南端"与综合图边界"：从左边界下端沿左侧走向向下延伸到综合图边界，
# 连综合图上部的拐点，再接到右边界下端（拐点从综合图边界上取）
SOUTH_CLOSURE = "left_end -> extend_along_left -> composite_top_vertices -> right_end"


def north_closure_points(holes, hole_prefix="BS-3940-1008-"):
    """按配方算出右上边界的中点序列（不含两端矿界端点）。"""
    pts = []
    for a, b in NORTH_CLOSURE_PAIRS:
        pa = holes.get(hole_prefix + a) or holes.get(a)
        pb = holes.get(hole_prefix + b) or holes.get(b)
        if pa is None or pb is None:
            continue
        pts.append(((pa.x + pb.x) / 2.0, (pa.y + pb.y) / 2.0))
    return pts


def _mid(holes, a, b):
    ha = holes.get("BS-3940-1008-" + a) or holes.get(a)
    hb = holes.get("BS-3940-1008-" + b) or holes.get(b)
    if ha is None or hb is None:
        return None
    return ((ha.x + hb.x) / 2.0, (ha.y + hb.y) / 2.0)


def grade_lines(holes, outline: Polygon, pairs_map=None, extend: float = 30.0):
    """把规则表里的孔对序列折算成"穿过矿界"的线，返回 {key: [LineString,...]}。"""
    pairs_map = pairs_map or GRADE_LINES
    out = {}
    for key, pairs in pairs_map.items():
        pts = [p for p in (_mid(holes, a, b) for a, b in pairs) if p]
        if len(pts) < 1:
            continue
        if len(pts) == 1:
            # 单点：按矿化带法向拉一条横切线（两端接到矿界）
            x, y = pts[0]
            b = outline.bounds
            line = LineString([(b[0] - extend, y), (b[2] + extend, y)])
        else:
            a = np.array(pts[0], float)
            b = np.array(pts[-1], float)
            d = b - a
            n = np.linalg.norm(d)
            d = d / n if n > 1e-9 else np.array([0.0, 1.0])
            pts = [tuple(a - d * extend)] + pts + [tuple(b + d * extend)]
            line = LineString(pts)
        out[key] = [line.intersection(outline)]
    return out


def split_by_grade_lines(outline: Polygon, lines_map):
    """用品位界限把矿界切开，返回若干子多边形。"""
    pieces = [outline]
    for key, lines in lines_map.items():
        for ln in lines:
            if ln.is_empty or ln.geom_type not in ("LineString", "MultiLineString"):
                continue
            new = []
            for p in pieces:
                try:
                    new.extend(shp_split(p, ln).geoms)
                except Exception:
                    new.append(p)
            pieces = new
    return pieces
