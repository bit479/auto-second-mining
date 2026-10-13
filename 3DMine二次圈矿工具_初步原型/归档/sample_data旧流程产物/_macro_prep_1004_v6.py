# -*- coding: utf-8 -*-
"""
1004 宏数据准备 v6：修复边界漏圈
- Voronoi 只对 ≥0.5 g/t 的孔计算（废孔不参与 → 不再隔断矿块单元，矿块覆盖废孔区域，贴近人工圈矿）
- 所有部件保留（不丢弃枝杈孔：P20/P21/P23/P26/P27/P29/P31 全部圈入）
- 聚类合并后多部件并为一块（MultiPolygon，一个块号）
- json 输出 parts（多环边界）
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型")
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from mdb_loader import load_xls_blast                       # noqa: E402
from voronoi import (GRADE_LEVELS, OreBlock, build_voronoi_cells,  # noqa: E402
                     classify_cells, merge_to_blocks)
from grid import grid_lines_inside                          # noqa: E402

XLS = Path(r"D:\WK\N CRT\北部山头3940平台2026\7、单日数据\北部山头3940平台-1004\1、3940平台 炮孔数据库1004.xls")
OUT = ROOT / "output" / "1004_macro"
OUT.mkdir(parents=True, exist_ok=True)

CFG = dict(
    blast_id="BS-3940-1004", platform="3940", date="1004",
    bench_height_m=10.0, density_ore_t_m3=2.7,
    min_ore_area_m2=15.0, grid_res_m=1.0,
)

COLOR = {"L1": (0, 255, 255), "L2": (0, 0, 255), "L3": (255, 0, 0), "L4": (255, 255, 0)}
REPORT_LABEL = {"L1": "0.500-1.000", "L2": "1.000-1.500", "L3": "1.500-3.000", "L4": "3.000-999.000"}
BLOCK_ORDER = ["L4", "L3", "L2", "L1"]


def rebuild_block(level_id, cells, poly, H, D):
    """按全部单元（面积权重品位）重建 OreBlock（poly 可为 MultiPolygon）。"""
    poly = poly.buffer(0)
    area = float(poly.area)
    area_w = sum(c.polygon.area for c in cells)
    grade = sum(c.grade * c.polygon.area for c in cells) / area_w if area_w > 0 else 0.0
    vol = area * H
    ton = vol * D
    return OreBlock(level_id, 0, poly, round(area, 1), round(vol, 1), round(ton, 1),
                    round(grade, 3), round(ton * grade, 0), len(cells), cells)


def _union_all(polys):
    """全部件 union（MultiPolygon 保留所有部件，不丢弃）。"""
    from shapely.ops import unary_union
    return unary_union([p.buffer(0) for p in polys]).buffer(0)


def main():
    comp = load_xls_blast(XLS)
    print(f"[数据] {len(comp)} 个炮孔")

    # v6: 只对 ≥0.5 的孔构建 Voronoi（废孔剔除）
    ore_mask = comp["Grade"].to_numpy(float) >= 0.5
    comp_ore = comp[ore_mask].reset_index(drop=True)
    print(f"[数据] ≥0.5g/t 参与圈矿孔数 = {len(comp_ore)}（剔除 <0.5 废孔 {int((~ore_mask).sum())} 个）")

    cells = build_voronoi_cells(comp_ore["X"].to_numpy(float), comp_ore["Y"].to_numpy(float),
                                comp_ore["Grade"].to_numpy(float), comp_ore["Hole_ID"].tolist())
    grouped = classify_cells(cells)
    blocks_by_level = {}
    for lv in GRADE_LEVELS:
        blocks_by_level[lv["id"]] = merge_to_blocks(
            grouped[lv["id"]], bench_height_m=CFG["bench_height_m"],
            density_ore_t_m3=CFG["density_ore_t_m3"], min_area_m2=CFG["min_ore_area_m2"])
    for lv in GRADE_LEVELS:
        bs = blocks_by_level.get(lv["id"], [])
        print(f"[{lv['id']}] {lv['label']}: {len(bs)} 块 -> "
              + ", ".join(f"#{i}({b.cell_count}孔,{b.area_m2:.0f}m2)" for i, b in enumerate(bs, 1)))

    H = CFG["bench_height_m"]
    D = CFG["density_ore_t_m3"]

    # ---------- 空间合并（用户规则） ----------
    MERGE_DIST = 15.0

    def cluster_blocks(bs):
        """按空间距离<MERGE_DIST 聚类；每簇全部件合并为一块（MultiPolygon）。"""
        from shapely.ops import unary_union
        if len(bs) <= 1:
            return bs
        merged = []
        used = [False] * len(bs)
        for i in range(len(bs)):
            if used[i]:
                continue
            group = [bs[i]]
            used[i] = True
            changed = True
            while changed:
                changed = False
                for j in range(len(bs)):
                    if used[j]:
                        continue
                    gi = unary_union([b.polygon for b in group])
                    if gi.distance(bs[j].polygon) < MERGE_DIST:
                        group.append(bs[j])
                        used[j] = True
                        changed = True
            if len(group) > 1:
                cells_l = [c for b in group for c in b.cells]
                poly = _union_all([b.polygon for b in group])
                merged.append(rebuild_block(cells_l[0].level_id, cells_l, poly, H, D))
            else:
                merged.append(group[0])
        return merged

    # ≥1 g/t 孔：L4/L3/L2 统一聚类
    hi_cells = []
    for lv in ["L4", "L3", "L2"]:
        for b in blocks_by_level.get(lv, []):
            hi_cells.extend(b.cells)
    hi_blocks = merge_to_blocks(hi_cells, bench_height_m=H, density_ore_t_m3=D,
                                min_area_m2=CFG["min_ore_area_m2"])
    hi_blocks = cluster_blocks(hi_blocks)
    for b in hi_blocks:
        b.level_id = "L4" if b.avg_grade_g_t >= 3.0 else ("L3" if b.avg_grade_g_t >= 1.5 else "L2")

    # 0.5-1 档：L1 全部并成一块（保留全部件——枝杈孔全部圈入）
    lo_cells = []
    for b in blocks_by_level.get("L1", []):
        lo_cells.extend(b.cells)
    lo_poly = _union_all([c.polygon for c in lo_cells])
    lo_block = rebuild_block("L1", lo_cells, lo_poly, H, D)
    lo_blocks = [lo_block] if lo_block.area_m2 >= CFG["min_ore_area_m2"] else []

    # L2 孤块并入 0.5-1 大块
    l2_left = [b for b in hi_blocks if b.level_id == "L2"]
    if l2_left and lo_blocks:
        hi_blocks = [b for b in hi_blocks if b.level_id != "L2"]
        all_cells = [c for b in lo_blocks for c in b.cells] + [c for b in l2_left for c in b.cells]
        lo_block = rebuild_block("L1", all_cells, _union_all([c.polygon for c in all_cells]), H, D)
        lo_blocks = [lo_block]

    blocks_by_level = {"L4": [b for b in hi_blocks if b.level_id == "L4"],
                       "L3": [b for b in hi_blocks if b.level_id == "L3"],
                       "L2": [b for b in hi_blocks if b.level_id == "L2"],
                       "L1": lo_blocks}

    for lv_id in ["L4", "L3", "L2", "L1"]:
        print(f"[合并] {lv_id}: {len(blocks_by_level[lv_id])} 块")

    # ---------- 编号 ----------
    all_blocks: list[OreBlock] = []
    for lv in BLOCK_ORDER:
        for b in blocks_by_level.get(lv, []):
            b.block_no = len(all_blocks) + 1
            all_blocks.append(b)
    for b in all_blocks:
        parts_n = len(list(b.polygon.geoms)) if b.polygon.geom_type == "MultiPolygon" else 1
        print(f"[矿块#{b.block_no}] {REPORT_LABEL[b.level_id]}: "
              f"{b.area_m2:.0f} m2 / {b.volume_m3:.0f} m3 / {b.tonnage_t:.0f} t / "
              f"{b.avg_grade_g_t:.3f} g/t / {b.cell_count} 孔 / {parts_n}部件")

    # ---------- 输出 json（parts 多环） ----------
    from shapely.ops import triangulate
    bench_z = float(comp["Z"].median())
    data = {
        "meta": {
            "blast_id": CFG["blast_id"], "platform": CFG["platform"], "date": CFG["date"],
            "bench_z": bench_z, "bench_height_m": H,
            "density_ore_t_m3": D, "grid_res_m": CFG["grid_res_m"],
        },
        "holes": [{"id": h, "x": float(x), "y": float(y), "grade": float(g)}
                  for h, x, y, g in zip(comp["Hole_ID"], comp["X"], comp["Y"], comp["Grade"])],
        "blocks": [],
    }
    for b in all_blocks:
        polys = list(b.polygon.geoms) if b.polygon.geom_type == "MultiPolygon" else [b.polygon]
        polys = [p.buffer(0) for p in polys if p.area > 1e-6]
        parts = [[[float(x), float(y)] for x, y in np.asarray(p.exterior.coords)] for p in polys]
        # 网格（逐部件）
        grid_lines = []
        for pp in polys:
            for ln in grid_lines_inside(pp, cell_size=CFG["grid_res_m"]):
                for (x1, y1), (x2, y2) in [list(ln.coords)]:
                    grid_lines.append([[float(x1), float(y1)], [float(x2), float(y2)]])
        # 填充面三角化（逐部件）
        tri_verts, tri_vmap, tri_faces = [], {}, []
        for pp in polys:
            tri_polys = [t for t in triangulate(pp.buffer(0))
                         if t.intersection(pp).area > 1e-6]
            tri_polys = [t.intersection(pp) for t in tri_polys]
            for tp in tri_polys:
                if tp.geom_type != "Polygon" or tp.area <= 1e-6:
                    continue
                cs = list(tp.exterior.coords)[:3]
                f = []
                for cx, cy in cs:
                    key = (round(cx, 2), round(cy, 2))
                    if key not in tri_vmap:
                        tri_vmap[key] = len(tri_verts)
                        tri_verts.append([float(cx), float(cy)])
                    f.append(tri_vmap[key])
                tri_faces.append(f)
        data["blocks"].append({
            "no": b.block_no, "level": b.level_id,
            "grade_label": REPORT_LABEL[b.level_id],
            "color": COLOR[b.level_id],
            "parts": parts,
            "boundary": parts[0] if parts else [],
            "centroid": [float(b.polygon.representative_point().x),
                         float(b.polygon.representative_point().y)],
            "holes": [c.hole_id for c in b.cells],
            "cell_count": b.cell_count,
            "area_m2": round(b.area_m2, 3), "volume_m3": round(b.volume_m3, 3),
            "tonnage_t": round(b.tonnage_t, 3), "avg_grade_g_t": round(b.avg_grade_g_t, 3),
            "metal_g": round(b.metal_g, 3),
            "grid_lines": grid_lines,
            "tri_verts": tri_verts, "tri_faces": tri_faces,
        })
    json_path = OUT / "1004_blocks.json"
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[JSON] {json_path}")

    # ---------- 报告 ----------
    lines = [f"{'体号':<5}{'品位类型':<14}{'面积m2':>9}{'体积m3':>10}{'重量t':>11}"
             f"{'平均品位g/t':>12}{'金属量g':>10}  炮孔数  炮孔号"]
    for b in all_blocks:
        holes_s = "、".join(c.hole_id.split("-")[-1] for c in b.cells)
        lines.append(f"#{b.block_no:<4}{REPORT_LABEL[b.level_id]:<14}{b.area_m2:>9.1f}"
                     f"{b.volume_m3:>10.1f}{b.tonnage_t:>11.1f}{b.avg_grade_g_t:>12.3f}"
                     f"{b.metal_g:>10.0f}  {b.cell_count:<5}{holes_s}")
    (OUT / "1004_macro_报告.txt").write_text("\n".join(lines), encoding="utf-8")

    rows = []
    for lv in BLOCK_ORDER:
        bs = [b for b in all_blocks if b.level_id == lv]
        if not bs:
            continue
        for b in bs:
            rows.append({"类型": REPORT_LABEL[lv], "体号": b.block_no, "体积": round(b.volume_m3, 3),
                         "重量（t）": round(b.tonnage_t, 3), "平均品位(Au)": round(b.avg_grade_g_t, 3),
                         "金属量（百克）": round(b.metal_g / 100.0, 3)})
        st = sum(b.tonnage_t for b in bs)
        sm = sum(b.metal_g for b in bs)
        rows.append({"类型": "小计", "体号": None, "体积": round(sum(b.volume_m3 for b in bs), 3),
                     "重量（t）": round(st, 3), "平均品位(Au)": round(sm / st, 3),
                     "金属量（百克）": round(sm / 100.0, 3)})
    t_all = sum(b.tonnage_t for b in all_blocks)
    m_all = sum(b.metal_g for b in all_blocks)
    rows.append({"类型": "合计", "体号": None, "体积": round(sum(b.volume_m3 for b in all_blocks), 3),
                 "重量（t）": round(t_all, 3), "平均品位(Au)": round(m_all / t_all, 3),
                 "金属量（百克）": round(m_all / 100.0, 3)})
    pd.DataFrame(rows).to_csv(OUT / "1004_macro_报告.csv", index=False, encoding="utf-8-sig")
    print("[报告] 1004_macro_报告.txt / .csv")


if __name__ == "__main__":
    main()
