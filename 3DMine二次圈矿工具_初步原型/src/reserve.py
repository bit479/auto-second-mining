# -*- coding: utf-8 -*-
"""
reserve：爆区储量核算
----------------------
对应项目计划书 4.4 节：按矿石区计算面积、体积、吨数、平均品位、金属量。
PoC 采用"多边形内部网格点品位平均 × 面积 × 台阶高度 × 容重"口径。
"""
from __future__ import annotations

import numpy as np
from matplotlib.path import Path


def reserve_for_polygons(
    polygons: list[np.ndarray],
    grid_z: np.ndarray, xg: np.ndarray, yg: np.ndarray,
    bench_height_m: float, density_ore_t_m3: float,
    cutoff_grade: float,
) -> dict:
    """核算每个矿块（多边形）的储量指标。"""
    xx, yy = np.meshgrid(xg, yg)
    pts = np.column_stack([xx.ravel(), yy.ravel()])
    g_flat = grid_z.ravel()

    blocks = []
    total_tonnage = 0.0
    total_metal = 0.0
    weighted_grade_sum = 0.0
    total_area = 0.0
    for i, poly in enumerate(polygons, start=1):
        inside = Path(poly).contains_points(pts)
        grades = g_flat[inside]
        # 只统计品位>=cutoff 的网格（保证与边界一致）
        grades = grades[grades >= cutoff_grade]
        if len(grades) == 0:
            continue
        area_m2 = float(len(grades)) * (xg[1] - xg[0]) * (yg[1] - yg[0])
        avg_grade = float(np.mean(grades))
        volume_m3 = area_m2 * bench_height_m
        tonnage = volume_m3 * density_ore_t_m3
        metal_g = tonnage * avg_grade   # 金属量（g）

        total_tonnage += tonnage
        total_metal += metal_g
        weighted_grade_sum += avg_grade * area_m2
        total_area += area_m2

        blocks.append({
            "Block_No": i,
            "Area_m2": round(area_m2, 1),
            "Volume_m3": round(volume_m3, 1),
            "Tonnage_t": round(tonnage, 1),
            "Avg_Grade_g_t": round(avg_grade, 3),
            "Metal_g": round(metal_g, 0),
        })

    summary = {
        "Block_Count": len(blocks),
        "Total_Area_m2": round(total_area, 1),
        "Total_Tonnage_t": round(total_tonnage, 1),
        "Weighted_Avg_Grade_g_t": round(weighted_grade_sum / total_area, 3) if total_area > 0 else 0.0,
        "Total_Metal_g": round(total_metal, 0),
        "Cutoff_Grade_g_t": cutoff_grade,
    }
    return {"blocks": blocks, "summary": summary}
