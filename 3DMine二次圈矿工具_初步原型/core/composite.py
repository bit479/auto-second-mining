# -*- coding: utf-8 -*-
"""读取平台"综合图"里的历史矿块边界，并与当日自动圈矿结果比对合并。

综合图（.dwg）用 AutoCAD 只读方式扫描；扫一次结果缓存成 json，DWG 没变就复用。
矿块边界的识别规则：闭合折线、面积 ≥ MIN_BLOCK_AREA、且不在 爆区方格网/点/钻孔/线条 图层。
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from shapely.geometry import Polygon
from shapely.ops import unary_union

MIN_BLOCK_AREA = 5.0
SKIP_LAYERS = {"爆区方格网", "点", "钻孔", "线条"}


def _scan_with_autocad(dwg: Path, out_json: Path) -> dict:
    """用 AutoCAD COM 只读扫描 DWG（附加到已运行的 AutoCAD，不启动、不关闭）。"""
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    acad = win32com.client.GetActiveObject("AutoCAD.Application")
    doc = None
    opened = False
    for d in acad.Documents:
        try:
            if Path(str(d.FullName)).name.lower() == dwg.name.lower():
                doc = d
                break
        except Exception:
            continue
    if doc is None:
        doc = acad.Documents.Open(str(dwg), True)
        opened = True
    polys = []
    for ent in doc.ModelSpace:
        try:
            if ent.ObjectName not in ("AcDbPolyline", "AcDb2dPolyline", "AcDb3dPolyline"):
                continue
            if ent.Layer in SKIP_LAYERS:
                continue
            coords = list(ent.Coordinates)
            pts = [[round(coords[i], 3), round(coords[i + 1], 3)]
                   for i in range(0, len(coords) - 1, 2)]
            if len(pts) >= 3:
                polys.append({"layer": ent.Layer, "color": int(ent.Color), "pts": pts})
        except Exception:
            continue
    if opened:
        try:
            doc.Close(False)
        except Exception:
            pass
    data = {"dwg": str(dwg), "polylines": polys}
    out_json.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def load_composite_blocks(dwg, cache_dir=None):
    """返回综合图里的历史矿块多边形列表 [(layer, color, polygon), ...]。"""
    dwg = Path(dwg)
    cache = (Path(cache_dir) if cache_dir else dwg.parent) / (dwg.stem + "_scan.json")
    if cache.exists() and cache.stat().st_mtime >= dwg.stat().st_mtime:
        data = json.loads(cache.read_text(encoding="utf-8"))
    else:
        print("[综合图] 扫描 %s ..." % dwg.name)
        data = _scan_with_autocad(dwg, cache)
    out = []
    for p in data.get("polylines", []):
        pts = p["pts"]
        if len(pts) < 3:
            continue
        if pts[0] != pts[-1]:
            pts = pts + [pts[0]]
        poly = Polygon(pts).buffer(0)
        if poly.area >= MIN_BLOCK_AREA:
            out.append((p.get("layer", ""), p.get("color", 7), poly))
    return out


def merge_outline(block_poly: Polygon, comp_blocks, max_gap: float = 4.5):
    """当日矿块与综合图历史矿块：间距 ≤ max_gap 的并成一块。返回 (合并后多边形, 并入的历史块数)。"""
    if block_poly is None:
        return None, 0
    group = [block_poly]
    n = 0
    changed = True
    while changed:
        changed = False
        cur = unary_union(group)
        for item in comp_blocks:
            p = item[2]
            if any(p is g for g in group):
                continue
            if cur.distance(p) <= max_gap:
                group.append(p)
                n += 1
                changed = True
    merged = unary_union(group)
    # 合并后把"断口"补上：先外扩 gap/2 再收回来，使几块连成一条闭合轮廓
    if merged.geom_type == "MultiPolygon":
        d = max_gap / 2.0 + 0.1
        closed = merged.buffer(d, join_style="mitre").buffer(
            -d, join_style="mitre")
        if not closed.is_empty:
            merged = closed
    return merged, n
