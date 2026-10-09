# -*- coding: utf-8 -*-
"""
voronoi：Voronoi（泰森多边形）分级圈矿
---------------------------------------
对应项目计划书 4.2 / 5.2 节：

  - 以炮孔平面坐标为种子点构建 Voronoi 图（每个炮孔一个泰森单元）
  - 按品位等级（0.5-1 / 1-1.5 / 1.5-3 / ≥3 g/t）对单元分类
  - 合并相邻同等级单元 → 生成各等级矿块（含矿量、品位、金属量）
  - 等级边界 = 矿块外边界（闭合多边形，供 .str / DXF 输出）

依赖：scipy.spatial.Voronoi + shapely（多边形合并/面积/网格裁剪）。
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.spatial import Voronoi
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union

# 品位等级定义（g/t），用户指定边界：0.5-1 / 1-1.5 / 1.5-3 / ≥3
GRADE_LEVELS = [
    {"id": "L1", "lo": 0.5, "hi": 1.0, "label": "0.5-1.0 g/t", "code": "LOW_GRADE_0_5_1"},
    {"id": "L2", "lo": 1.0, "hi": 1.5, "label": "1.0-1.5 g/t", "code": "GRADE_1_1_5"},
    {"id": "L3", "lo": 1.5, "hi": 3.0, "label": "1.5-3.0 g/t", "code": "GRADE_1_5_3"},
    {"id": "L4", "lo": 3.0, "hi": np.inf, "label": ">=3.0 g/t", "code": "HIGH_GRADE_3UP"},
]


@dataclass
class VoronoiCell:
    """单个炮孔控制的泰森单元。"""
    hole_id: str
    x: float
    y: float
    grade: float
    polygon: Polygon
    level_id: str | None = None   # 品位等级（<0.5 为 None，属废石）


@dataclass
class OreBlock:
    """一个等级的连续矿块（相邻同等级单元合并而成）。"""
    level_id: str
    block_no: int
    polygon: Polygon
    area_m2: float
    volume_m3: float
    tonnage_t: float
    avg_grade_g_t: float
    metal_g: float
    cell_count: int = 0
    cells: list[VoronoiCell] = field(default_factory=list)


def build_voronoi_cells(x: np.ndarray, y: np.ndarray, grades: np.ndarray,
                        hole_ids: list[str]) -> list[VoronoiCell]:
    """构建爆区 Voronoi 图并裁剪为有限单元。

    返回与输入孔一一对应的 VoronoiCell 列表。
    """
    points = np.column_stack([x, y])
    vor = Voronoi(points)
    # 裁剪半径：覆盖整个点集范围
    radius = float(np.max(np.ptp(points, axis=0)) * 2.0)
    regions, vertices = _finite_voronoi(vor, radius)

    # 爆区裁剪边界：点集凸包外扩 3 m（对应 3DMine 圈矿边界，边缘单元面积更贴合人工圈连范围）
    clip = MultiPolygon([Polygon(points).convex_hull.buffer(3.0)])

    cells = []
    for i, region_idx in enumerate(vor.point_region):
        region = regions[i]
        poly = Polygon(vertices[region])
        if not poly.is_valid:
            # Voronoi 单元必为凸多边形：顶点顺序错乱导致的蝴蝶结自交
            # 用凸包恢复正确形状（buffer(0) 可能保留错误一侧）
            poly = poly.convex_hull
        poly = poly.buffer(0).intersection(clip)
        if poly.is_valid and not poly.is_empty and poly.area > 1e-6:
            cells.append(VoronoiCell(
                hole_id=hole_ids[i],
                x=float(x[i]),
                y=float(y[i]),
                grade=float(grades[i]),
                polygon=poly,
            ))
    return cells


def _finite_voronoi(vor: Voronoi, radius: float):
    """把 Voronoi 图的无限区域裁剪为有限多边形（matplotlib 经典实现）。

    返回 (regions, vertices)：每个点的有限区域顶点索引 + 扩展后的顶点集。
    """
    if vor.points.shape[1] != 2:
        raise ValueError("仅支持 2D 输入")
    center = vor.points.mean(axis=0)
    new_vertices = vor.vertices.tolist()
    new_regions = []

    all_ridges: dict[int, list] = {}
    for (p1, p2), (v1, v2) in zip(vor.ridge_points, vor.ridge_vertices):
        all_ridges.setdefault(p1, []).append((p2, v1, v2))
        all_ridges.setdefault(p2, []).append((p1, v1, v2))

    for p1, region_idx in enumerate(vor.point_region):
        vertices = vor.regions[region_idx]
        if all(v >= 0 for v in vertices):
            new_regions.append(vertices)
            continue
        ridges = all_ridges[p1]
        new_region = [v for v in vertices if v >= 0]
        for p2, v1, v2 in ridges:
            if v2 < 0:
                v1, v2 = v2, v1
            if v1 >= 0:
                continue
            t = vor.points[p2] - vor.points[p1]
            t /= np.linalg.norm(t)
            n = np.array([-t[1], t[0]])
            midpoint = vor.points[[p1, p2]].mean(axis=0)
            d = float(np.dot(midpoint - center, n))
            direction = n if d >= 0 else -n   # 避免 np.sign(0)=0 导致退化
            far_point = vor.vertices[v2] + direction * radius
            new_vertices.append(far_point.tolist())
            new_region.append(len(new_vertices) - 1)
        new_regions.append(new_region)
    return new_regions, np.asarray(new_vertices)


def classify_cells(cells: list[VoronoiCell]) -> dict[str, list[VoronoiCell]]:
    """按品位等级给单元分类（<0.5 g/t 归废石，不进入任何等级）。"""
    grouped: dict[str, list[VoronoiCell]] = {lv["id"]: [] for lv in GRADE_LEVELS}
    for c in cells:
        for lv in GRADE_LEVELS:
            if lv["lo"] <= c.grade < lv["hi"]:
                c.level_id = lv["id"]
                grouped[lv["id"]].append(c)
                break
    return grouped


def merge_to_blocks(cells: list[VoronoiCell], bench_height_m: float,
                    density_ore_t_m3: float, min_area_m2: float = 0.0) -> list[OreBlock]:
    """合并相邻同等级单元为矿块，并计算矿量、品位、金属量。

    品位口径（按用户要求"通过 Voronoi 图计算矿量、品位"）：
      矿块品位 = Σ(单元品位 × 单元面积) / Σ单元面积（单元面积权重）。
    矿量 = 矿块面积 × 台阶高度 × 容重。
    """
    if not cells:
        return []
    union = unary_union([c.polygon for c in cells])
    parts = list(union.geoms) if isinstance(union, MultiPolygon) else [union]

    blocks: list[OreBlock] = []
    level_id = cells[0].level_id
    for i, part in enumerate(parts, start=1):
        part = part.buffer(0)  # 修复细碎几何
        # 矿块内部单元：质心落在矿块内
        inside = [c for c in cells if part.covers(c.polygon.representative_point())]
        if not inside:
            inside = [c for c in cells if part.intersection(c.polygon).area > 0.5 * c.polygon.area]
        area_w = sum(c.polygon.area for c in inside)
        grade_w = sum(c.grade * c.polygon.area for c in inside) / area_w if area_w > 0 else 0.0
        area_m2 = float(part.area)
        if area_m2 < min_area_m2:
            continue
        volume = area_m2 * bench_height_m
        tonnage = volume * density_ore_t_m3
        blocks.append(OreBlock(
            level_id=level_id,
            block_no=i,
            polygon=part,
            area_m2=round(area_m2, 1),
            volume_m3=round(volume, 1),
            tonnage_t=round(tonnage, 1),
            avg_grade_g_t=round(grade_w, 3),
            metal_g=round(tonnage * grade_w, 0),
            cell_count=len(inside),
            cells=inside,
        ))
    return blocks


def absorb_low_grade_cells(
    blocks_by_level: dict[str, list[OreBlock]],
    bench_height_m: float,
    density_ore_t_m3: float,
    max_low_ratio: float = 0.5,
) -> dict[str, list[OreBlock]]:
    """跨档品位归并：低档矿块并入邻接高档矿块（保证每个矿块最终单一品位）。

    用户规则（人工流程）：
      圈连出的一个矿块内可能包含不同品位类型的炮孔（如 5 个 1-1.5 g/t
      孔 + 1 个 0.89 g/t 孔），此时把低品位孔纳入高档矿块，不同品位数据
      累加后用"金属量 / 矿石量"计算平均品位（= 品位×面积面积加权）。

    归并条件（保守，避免低品位主体反向吞并高档块）：
      1. 低档矿块与高档矿块共享边界（空间相邻）；
      2. 低档面积 ≤ max_low_ratio × 高档面积（低品位属少数）；
      3. 并入后矿块加权平均品位仍 ≥ 高档档位下限（矿块档位不变）。
    从低档到高档迭代，直至无吸收发生；返回归并后的各等级矿块。
    """
    blocks_by_level = {k: list(v) for k, v in blocks_by_level.items()}
    levels = [lv["id"] for lv in GRADE_LEVELS]
    lo_of = {lv["id"]: lv["lo"] for lv in GRADE_LEVELS}

    changed = True
    while changed:
        changed = False
        for i in range(len(levels) - 1):
            li = levels[i]
            low_blocks = blocks_by_level[li]
            if not low_blocks:
                continue
            high_candidates = []
            for j in range(i + 1, len(levels)):
                high_candidates.extend(blocks_by_level[levels[j]])
            for lb in list(low_blocks):
                best = None
                best_grade = -1.0
                for hb in high_candidates:
                    if lb.area_m2 > max_low_ratio * hb.area_m2:
                        continue
                    # 低档矿块质心须落在高档矿块内部（"矿块内混入的低品位孔"），
                    # 仅贴边（共享边界）的低档块保持独立成块（与人工圈连一致）
                    if not hb.polygon.covers(lb.polygon.representative_point()):
                        continue
                    a_l, a_h = lb.polygon.area, hb.polygon.area
                    new_grade = (lb.avg_grade_g_t * a_l + hb.avg_grade_g_t * a_h) / (a_l + a_h)
                    if new_grade >= lo_of[hb.level_id] and new_grade > best_grade:
                        best = hb
                        best_grade = new_grade
                if best is not None:
                    poly = unary_union([lb.polygon, best.polygon]).buffer(0)
                    best.polygon = poly
                    best.area_m2 = round(float(poly.area), 1)
                    best.volume_m3 = round(poly.area * bench_height_m, 1)
                    best.tonnage_t = round(poly.area * bench_height_m * density_ore_t_m3, 1)
                    best.avg_grade_g_t = round(best_grade, 3)
                    best.metal_g = round(best.tonnage_t * best_grade, 0)
                    best.cell_count += lb.cell_count
                    best.cells.extend(lb.cells)
                    low_blocks.remove(lb)
                    changed = True
    return {k: v for k, v in blocks_by_level.items() if v}


def extract_block_boundaries(blocks: list[OreBlock]) -> list[tuple[int, np.ndarray]]:
    """提取每个矿块的外边界闭合多边形（含洞信息已简化：仅外环）。

    返回 [(block_no, (N,2) 闭合坐标)]。
    """
    out = []
    for b in blocks:
        ext = b.polygon.exterior
        coords = np.asarray(ext.coords)
        out.append((b.block_no, coords))
    return out


__all__ = ["GRADE_LEVELS", "VoronoiCell", "OreBlock", "build_voronoi_cells",
           "classify_cells", "merge_to_blocks", "absorb_low_grade_cells",
           "extract_block_boundaries"]
