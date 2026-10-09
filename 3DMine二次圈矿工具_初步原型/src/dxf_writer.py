# -*- coding: utf-8 -*-
"""
dxf_writer：CAD DXF 输出（AutoCAD 交换格式）
---------------------------------------------
对应项目计划书 13.4 节：
  - 各品位等级矿块边界输出为闭合 LWPOLYLINE，按等级分图层、分颜色
  - 1m 网格线输出为 LINE，单独图层
  - 实体统一闭合、坐标与矿区坐标系一致
"""
from __future__ import annotations

from pathlib import Path

from ezdxf import new
from ezdxf.document import Drawing
from shapely.geometry import LineString, Polygon

from voronoi import GRADE_LEVELS

# 图层规范（对照 3DMine style_table_3dmine 显示样式 + 计划书 13.4 DG_* 命名）
# 3DMine: 0.5-1 青(0,1,1) / 1-1.5 蓝(0,0,1) / 1.5-3 红(1,0,0) / ≥3 黄(1,1,0)
# AutoCAD 标准色号：青=4 蓝=5 红=1 黄=2
LAYER_LEVELS = {
    "L1": ("DG_GRADE_L1", 4),    # 青色（0.5-1）
    "L2": ("DG_GRADE_L2", 5),    # 蓝色（1-1.5）
    "L3": ("DG_GRADE_L3", 1),    # 红色（1.5-3）
    "L4": ("DG_GRADE_L4", 2),    # 黄色（≥3）
}
LAYER_GRID = ("DG_GRID", 8)      # 灰色
LAYER_CUTOFF = ("DG_CUTOFF", 7)  # 白色（界线）


def write_dxf(
    output_filepath: str | Path,
    blocks: list[dict],
    grid_lines: dict[int, list[LineString]],
    title: str = "3DMine 二次圈矿 - 品位等级分区",
    label_blocks: bool = True,
) -> Path:
    """输出 DXF 文件。

    blocks: [{"level_id": "L1", "block_no": 1, "polygon": Polygon,
              "label": "1\nL2 1.0-1.5 g/t"}, ...]
            等级边界按 LAYER_LEVELS 分图层；label_blocks=True 时在
            矿块质心标注矿块号（用户要求：CAD 图上标出矿块号）。
    grid_lines: {block_no: [LineString, ...]}
    """
    out = Path(output_filepath)
    out.parent.mkdir(parents=True, exist_ok=True)

    doc: Drawing = new("R2010")
    doc.header["$INSUNITS"] = 6  # 单位：米
    doc.layers.add("TITLE", color=7)
    doc.layers.add("BLOCK_NO", color=7)

    # 创建图层
    for layer, color in set(LAYER_LEVELS.values()) | {LAYER_GRID, LAYER_CUTOFF}:
        doc.layers.add(layer, color=color)

    msp = doc.modelspace()
    # 计算全部几何范围，用于标题定位
    all_bounds = [b["polygon"].bounds for b in blocks]
    if all_bounds:
        minx = min(b[0] for b in all_bounds)
        maxy = max(b[3] for b in all_bounds)
        msp.add_text(title, dxfattribs={"layer": "TITLE", "height": 5.0}).set_placement((minx, maxy + 15))

    # 等级边界（闭合 LWPOLYLINE）+ 矿块号标注
    for b in blocks:
        layer, _ = LAYER_LEVELS.get(b["level_id"], ("DG_GRADE_L1", 4))
        coords = list(b["polygon"].exterior.coords)
        msp.add_lwpolyline(coords, close=True, dxfattribs={
            "layer": layer, "lineweight": 25,
        })
        if label_blocks:
            cx, cy = b["polygon"].representative_point().coords[0]
            msp.add_text(b["label"], dxfattribs={
                "layer": "BLOCK_NO", "height": 3.0,
            }).set_placement((cx, cy))

    # 网格线（LINE）
    for block_no, lines in grid_lines.items():
        for ln in lines:
            x1, y1 = ln.coords[0]
            x2, y2 = ln.coords[1]
            msp.add_line((x1, y1), (x2, y2), dxfattribs={"layer": LAYER_GRID[0]})

    doc.saveas(out)
    return out


__all__ = ["write_dxf", "LAYER_LEVELS", "LAYER_GRID", "LAYER_CUTOFF"]
