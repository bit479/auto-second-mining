# -*- coding: utf-8 -*-
"""
interpolation：品位插值与矿/废边界提取
---------------------------------------
对应项目计划书 4.2 / 5.1 节：
  - IDW（距离幂次反比）规则网格插值
  - 网格连通域修正（孤立小矿体剔除 / 夹石包体剔除）
  - 等值线（边界）提取与多边形输出
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import distance_transform_edt, label

import mining_rules


def build_grid(x: np.ndarray, y: np.ndarray, resolution: float):
    """构建台阶平面规则网格（分辨率可配置，默认 1.0 m）。"""
    xg = np.arange(np.floor(x.min()), np.ceil(x.max()) + 1e-9, resolution)
    yg = np.arange(np.floor(y.min()), np.ceil(y.max()) + 1e-9, resolution)
    return xg, yg


def idw_interpolate(
    x: np.ndarray, y: np.ndarray, values: np.ndarray,
    xg: np.ndarray, yg: np.ndarray,
    power: float = 2.0, search_radius: float | None = None,
) -> np.ndarray:
    """IDW（Inverse Distance Weighting）网格插值。

    每个网格节点取其搜索半径内的邻近孔，按距离幂次反比加权估值；
    搜索半径内无孔的边缘节点用最近邻孔品位外推，保证边界闭合。
    """
    xx, yy = np.meshgrid(xg, yg)
    pts_x = x[:, None, None]
    pts_y = y[:, None, None]
    dist = np.sqrt((xx[None] - pts_x) ** 2 + (yy[None] - pts_y) ** 2)  # (n_holes, ny, nx)

    if search_radius is None:
        spacing = np.median(np.diff(xg))
        search_radius = spacing * 2.0

    w = np.where(dist <= search_radius, 1.0 / (dist + 1e-9) ** power, 0.0)
    w = np.where(np.isclose(dist, 0.0), 1e6, w)  # 孔位节点取孔品位本身
    num = np.sum(w * values[:, None, None], axis=0)
    den = np.sum(w, axis=0)
    with np.errstate(divide="ignore", invalid="ignore"):
        grid_z = np.where(den > 0, num / den, np.nan)

    # 边缘外推：最近邻孔品位
    if np.isnan(grid_z).any():
        fill_idx = distance_transform_edt(
            np.isnan(grid_z), return_distances=False, return_indices=True
        )
        grid_z = grid_z[tuple(fill_idx)]
    return grid_z


def apply_mining_rules(
    grid_z: np.ndarray, cutoff_grade: float,
    min_ore_area_m2: float, min_waste_area_m2: float, resolution: float,
) -> np.ndarray:
    """采矿工程约束规则（网格层面，计划书 4.3 节）。

      - 夹石剔除/合并：矿体内部废石包体面积 < 最小夹石剔除面积 → 合并为矿石
      - 孤立小矿体剔除：矿体连通域面积 < 最小可采块体面积 → 归为废石
    返回修正后的品位网格。
    """
    cell_area = resolution * resolution
    ore_mask = grid_z >= cutoff_grade

    # 1) 夹石剔除：被矿体完全包围（不接触爆区边界）的小面积废石连通域 → 归并为矿石。
    #    与外部废石相连的域视为正常废石，不处理。
    labels_w, n_w = label(~ore_mask)
    if n_w > 0:
        sizes = np.bincount(labels_w.ravel())[1:]
        ny, nx = labels_w.shape
        for lab in range(1, n_w + 1):
            if sizes[lab - 1] * cell_area >= min_waste_area_m2:
                continue
            ys, xs = np.where(labels_w == lab)
            touches_boundary = (
                xs.min() == 0 or xs.max() == nx - 1
                or ys.min() == 0 or ys.max() == ny - 1
            )
            if not touches_boundary:
                ore_mask[labels_w == lab] = True
                print(f"[规则-夹石剔除] 夹石包体 {sizes[lab - 1] * cell_area:.0f} m² 归并至矿石")

    # 2) 孤立小矿体剔除
    labels_o, n_o = label(ore_mask)
    if n_o > 0:
        sizes = np.bincount(labels_o.ravel())[1:]
        for lab in np.where(sizes * cell_area < min_ore_area_m2)[0] + 1:
            ore_mask[labels_o == lab] = False
            print(f"[规则-孤立矿体剔除] 小矿块 {sizes[lab - 1] * cell_area:.0f} m² 归为废石")

    # 同步修正品位网格（保证边界与掩码一致）
    grid_z = np.where(ore_mask, np.maximum(grid_z, cutoff_grade), grid_z)
    grid_z = np.where(~ore_mask, np.minimum(grid_z, cutoff_grade - 0.01), grid_z)
    return grid_z


def extract_ore_boundaries(
    grid_z: np.ndarray, xg: np.ndarray, yg: np.ndarray,
    cutoff_grade: float,
    simplify_tol: float,
) -> list[np.ndarray]:
    """从修正后的品位网格提取矿体闭合边界多边形（2D 平面坐标）。

    返回多边形列表，每个多边形为 (N, 2) 的 numpy 数组（闭合，首尾点相同）。
    """
    from matplotlib import pyplot as plt

    ore_mask = grid_z >= cutoff_grade
    # 在掩码二值图上提取 level=0.5 等值线，等价于矿/废边界
    fig = plt.figure()
    try:
        cs = plt.contour(xg, yg, ore_mask.astype(float), levels=[0.5])
        all_segs = cs.allsegs[0] if cs.allsegs else []
    finally:
        plt.close(fig)

    polys = []
    for verts in all_segs:
        verts = np.asarray(verts, dtype=float)
        if len(verts) < 4:
            continue
        if np.allclose(verts[0], verts[-1]):  # 去掉重复闭合点
            verts = verts[:-1]
        if len(verts) < 3:
            continue
        area = mining_rules.polygon_area(verts)
        if area < 0:  # 统一为逆时针（正面积）
            verts = verts[::-1]
        poly = mining_rules.simplify_douglas_peucker(verts, simplify_tol)
        if len(poly) >= 3 and mining_rules.polygon_area(poly) > 0:
            polys.append(poly)
    return polys


__all__ = ["build_grid", "idw_interpolate", "apply_mining_rules", "extract_ore_boundaries"]
