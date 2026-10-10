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

# 每条品位界限：孔对序列（中点依次连线）。已逐点对齐用户 1008 的
# 「1号品位界限.3ds」「2号品位界限.3ds」：
#   1 号：mid(P14,P12) 单点，方向取矿化带法向（与人工线夹角 1.0°）
#   2 号：8 个中点，逐点吻合（上一版漏了 mid(P7,P8)）
GRADE_LINES = {
    "1号": [("P14", "P12")],
    "2号": [("P8", "P13"), ("P12", "P8"), ("P7", "P8"), ("P6", "P7"),
            ("P5", "P6"), ("P5", "P4"), ("P3", "P4"), ("P2", "P4")],
}

# 人工指定"不进左右链"的孔（兜底用）：现在内部孔已由 strip.zone_chains 自动识别
#（走向 ±0.9×最近邻中位数 范围内两侧都有矿孔 → 内部孔），1008 的 P8 自动就被排除了，
# 所以这里留空；只有当自动判断跟你的人工图不一致时，才把孔号写进来强制排除。
# 注意：被排除的孔仍然属于矿块、照常参与算量，只是不参与"画边界的两条链"。
CHAIN_EXCLUDE: list = []

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


def extend_ends(core, span=100.0):
    """把折线两端沿**各自那一端的分段方向**向外延伸（切割线必须贯穿矿界）。

    这一步是 1008 上反复试出来的关键：不能沿整条线的平均方向延伸，
    否则端点会偏到矿界内侧、切不断。
    """
    import numpy as np

    p = np.array(core[0], float)
    q = np.array(core[1], float)
    d = p - q
    d = d / (np.linalg.norm(d) + 1e-12)
    r = np.array(core[-1], float)
    s = np.array(core[-2], float)
    e = r - s
    e = e / (np.linalg.norm(e) + 1e-12)
    return [tuple(p + d * span)] + [tuple(x) for x in core] + [tuple(r + e * span)]


def grade_cut_lines(holes, span=100.0, prefix="BS-3940-1008-"):
    """把规则表折算成两条"贯穿矿界"的切割线坐标序列。"""
    out = {}
    for key, pairs in GRADE_LINES.items():
        core = []
        for a, b in pairs:
            ha = holes.get(prefix + a) or holes.get(a)
            hb = holes.get(prefix + b) or holes.get(b)
            if ha is None or hb is None:
                continue
            core.append(((ha.x + hb.x) / 2.0, (ha.y + hb.y) / 2.0))
        if len(core) >= 2:
            out[key] = extend_ends(core, span)
        elif len(core) == 1:
            out[key] = core
    return out


def cut_lines(holes, normal, span=100.0, prefix="BS-3940-1008-"):
    """把规则表折算成"穿过矿界"的切割线（LineString 列表）。

    多中点线：两端沿**各自那一端的分段方向**外延（1008 上验证的关键）；
    单中点线：沿矿化带法向 normal 向两侧外延（人工 1 号线就是这么画的）。
    """
    lines = []
    for key, pairs in GRADE_LINES.items():
        pts = [p for p in (_mid(holes, a, b) for a, b in pairs) if p]
        if len(pts) == 1:
            x, y = pts[0]
            nx, ny = float(normal[0]), float(normal[1])
            pts = [(x - nx * span, y - ny * span),
                   (x + nx * span, y + ny * span)]
        elif len(pts) >= 2:
            pts = extend_ends(pts, span)
        if len(pts) >= 2:
            lines.append((key, LineString(pts)))
    return lines


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
