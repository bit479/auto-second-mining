# -*- coding: utf-8 -*-
"""
str_writer：3DMine .str 线文件写出器
-------------------------------------
对应项目计划书 6.3 节 / 附录B 的 .str 文件格式规范：
  文件头两行（标识 + 列名），数据区每行一个点；
  同一边界线 StringID 相同；闭合段末尾重复首点坐标。
"""
from __future__ import annotations

from pathlib import Path

import numpy as np


def write_str(
    polygons: list[np.ndarray],
    output_filepath: str | Path,
    bench_z: float,
    code: str = "ORE_BODY",
) -> int:
    """将闭合多边形列表写入 3DMine .str 文件。

    polygons：每个元素为 (N, 2) 的平面坐标数组（X, Y）。
    bench_z：台阶高程（Z 统一取该值）。
    返回写入的点数。
    """
    out = Path(output_filepath)
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = ["3DMine String File", "PointID,X,Y,Z,StringID,Code"]
    point_id = 1
    total = 0
    for string_id, poly in enumerate(polygons, start=1):
        poly = np.asarray(poly, dtype=float)
        if not np.allclose(poly[0], poly[-1]):  # 保证闭合
            poly = np.vstack([poly, poly[0]])
        for x, y in poly:
            lines.append(f"{point_id},{x:.3f},{y:.3f},{bench_z:.3f},{string_id},{code}")
            point_id += 1
            total += 1
    # UTF-8 无 BOM（计划书附录B：3DMine 加载兼容性）
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return total


__all__ = ["write_str"]
