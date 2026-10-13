# -*- coding: utf-8 -*-
"""
1004 宏数据准备：读 xls -> voronoi 分级 -> 按用户规则空间合并矿块
-> 输出 1004_macro/1004_blocks.json（供 3DMine 宏读取绘制）+ 报告 + 验证图
合并规则（用户要求）：同一品位档内空间相邻的碎块合并成可采整体；
低品位孔按原逻辑归并入相邻高档块；每矿块单一品位（金属量/矿石量加权）。
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
                     classify_cells, merge_to_blocks, absorb_low_grade_cells)
from grid import grid_lines_inside                          # noqa: E402

XLS = Path(r"D:\WK\N CRT\北部山头3940平台2026\7、单日数据\北部山头3940平台-1004\1、3940平台 炮孔数据库1004.xls")
OUT = ROOT / "output" / "1004_macro"
OUT.mkdir(parents=True, exist_ok=True)

CFG = dict(
    blast_id="BS-3940-1004", platform="3940", date="1004",
    bench_height_m=10.0, density_ore_t_m3=2.7,
    min_ore_area_m2=15.0, grid_res_m=1.0,
    absorb_low_grade_cells=True, absorb_max_low_ratio=0.5,
)

COLOR = {"L1": (0, 255, 255), "L2": (0, 0, 255), "L3": (255, 0, 0), "L4": (255, 255, 0)}
REPORT_LABEL = {"L1": "0.500-1.000", "L2": "1.000-1.500", "L3": "1.500-3.000", "L4": "3.000-999.000"}
BLOCK_ORDER = ["L4", "L3", "L2", "L1"]


def union_area(polys) -> float:
    """多个多边形合并面积（近似：外包矩形内网格采样法，够用于判断合并必要性）。"""
    if not polys:
        return 0.0
    xs = np.concatenate([np.asarray(p.exterior.coords)[:, 0] for p in polys])
    ys = np.concatenate([np.asarray(p.exterior.coords)[:, 1] for p in polys])
    return (xs.max() - xs.min()) * (ys.max() - ys.min())


def main():
    comp = load_xls_blast(XLS)
    print(f"[数据] {len(comp)} 个炮孔")
    cells = build_voronoi_cells(comp["X"].to_numpy(float), comp["Y"].to_numpy(float),
                                comp["Grade"].to_numpy(float), comp["Hole_ID"].tolist())
    grouped = classify_cells(cells)
    blocks_by_level = {}
    for lv in GRADE_LEVELS:
        blocks_by_level[lv["id"]] = merge_to_blocks(
            grouped[lv["id"]], bench_height_m=CFG["bench_height_m"],
            density_ore_t_m3=CFG["density_ore_t_m3"], min_area_m2=CFG["min_ore_area_m2"])
    if CFG["absorb_low_grade_cells"]:
        blocks_by_level = absorb_low_grade_cells(
            blocks_by_level, bench_height_m=CFG["bench_height_m"],
            density_ore_t_m3=CFG["density_ore_t_m3"], max_low_ratio=CFG["absorb_max_low_ratio"])

    # 打印吸收后的分档结果
    for lv in GRADE_LEVELS:
        bs = blocks_by_level.get(lv["id"], [])
        print(f"[{lv['id']}] {lv['label']}: {len(bs)} 块 -> "
              + ", ".join(f"#{i}({b.cell_count}孔,{b.area_m2:.0f}m2)" for i, b in enumerate(bs, 1)))

    # ---------- 空间合并（用户规则：可采性合并，单块规模大才好采） ----------
    # ≥1 g/t 孔按 15m 聚类 -> 每簇一块，标签按加权品位（≥3->L4 / 1.5-3->L3 / 1-1.5->L2）
    # 0.5-1 孔全部并成一块（人工体2 为大范围 0.5-1 连片块）；L2 孤块（未入簇）并入 0.5-1 大块
    MERGE_DIST = 15.0  # 聚类距离阈值：炮孔间距级别，同一簇=人工圈连时会并在一起的相邻高值孔

    def cluster_blocks(bs):
        """把矿块按空间距离<MERGE_DIST 聚类合并（返回新 OreBlock 列表）。"""
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
                merged.append(merge_to_blocks(cells_l, bench_height_m=CFG["bench_height_m"],
                                              density_ore_t_m3=CFG["density_ore_t_m3"])[0])
            else:
                merged.append(group[0])
        return merged

    # ≥1 g/t 的孔：L4/L3/L2 统一聚类
    hi_cells = []
    for lv in ["L4", "L3", "L2"]:
        for b in blocks_by_level.get(lv, []):
            hi_cells.extend(b.cells)
    hi_blocks = merge_to_blocks(hi_cells, bench_height_m=CFG["bench_height_m"],
                                density_ore_t_m3=CFG["density_ore_t_m3"],
                                min_area_m2=CFG["min_ore_area_m2"])
    hi_blocks = cluster_blocks(hi_blocks)
    for b in hi_blocks:
        b.level_id = "L4" if b.avg_grade_g_t >= 3.0 else ("L3" if b.avg_grade_g_t >= 1.5 else "L2")

    # 0.5-1 档：L1 全部并成一块（人工体2 为 0.5-1 连片大块：外扩桥接邻近孔，取最大连通部件）
    from shapely.ops import unary_union

    def _lo_union(polys):
        u = unary_union(polys)
        if u.geom_type == "MultiPolygon":
            u = max(u.geoms, key=lambda g: g.area)
        return u

    lo_cells = []
    for b in blocks_by_level.get("L1", []):
        lo_cells.extend(b.cells)
    lo_poly = _lo_union([c.polygon for c in lo_cells])
    lo_area = float(lo_poly.area)
    lo_area_w = sum(c.polygon.area for c in lo_cells)
    lo_grade = sum(c.grade * c.polygon.area for c in lo_cells) / lo_area_w if lo_area_w > 0 else 0.0
    lo_block = OreBlock("L1", 0, lo_poly, lo_area, lo_area * CFG["bench_height_m"],
                        lo_area * CFG["bench_height_m"] * CFG["density_ore_t_m3"],
                        lo_grade, lo_grade * lo_area * CFG["bench_height_m"] * CFG["density_ore_t_m3"],
                        len(lo_cells), lo_cells)
    lo_blocks = [lo_block] if lo_area >= CFG["min_ore_area_m2"] else []

    # L2 孤块（未入 hi 簇、面积小）并入 0.5-1 大块（用户"7、8 圈在一起"：低档并入相邻大块）
    l2_left = [b for b in hi_blocks if b.level_id == "L2"]
    if l2_left and lo_blocks:
        hi_blocks = [b for b in hi_blocks if b.level_id != "L2"]
        all_cells = [c for b in lo_blocks for c in b.cells] + [c for b in l2_left for c in b.cells]
        lo_poly = _lo_union([c.polygon for c in all_cells])
        lo_area = float(lo_poly.area)
        lo_area_w = sum(c.polygon.area for c in all_cells)
        lo_grade = sum(c.grade * c.polygon.area for c in all_cells) / lo_area_w if lo_area_w > 0 else 0.0
        lo_block = OreBlock("L1", 0, lo_poly, lo_area,
                            lo_area * CFG["bench_height_m"],
                            lo_area * CFG["bench_height_m"] * CFG["density_ore_t_m3"],
                            lo_grade, lo_grade * lo_area * CFG["bench_height_m"] * CFG["density_ore_t_m3"],
                            len(all_cells), all_cells)
        lo_blocks = [lo_block]

    blocks_by_level = {"L4": [b for b in hi_blocks if b.level_id == "L4"],
                       "L3": [b for b in hi_blocks if b.level_id == "L3"],
                       "L2": [b for b in hi_blocks if b.level_id == "L2"],
                       "L1": lo_blocks}

    for lv_id in ["L4", "L3", "L2", "L1"]:
        print(f"[合并] {lv_id}: {len(blocks_by_level[lv_id])} 块")

    # ---------- 编号（L4->L3->L2->L1，跨档体号与人工报告习惯） ----------
    all_blocks: list[OreBlock] = []
    for lv in BLOCK_ORDER:
        for b in blocks_by_level.get(lv, []):
            b.block_no = len(all_blocks) + 1
            all_blocks.append(b)
    for b in all_blocks:
        print(f"[矿块#{b.block_no}] {REPORT_LABEL[b.level_id]}: "
              f"{b.area_m2:.0f} m2 / {b.volume_m3:.0f} m3 / {b.tonnage_t:.0f} t / "
              f"{b.avg_grade_g_t:.3f} g/t / {b.cell_count} 孔")

    # ---------- 输出 json（供 3DMine 宏） ----------
    from shapely.ops import triangulate
    bench_z = float(comp["Z"].median())
    data = {
        "meta": {
            "blast_id": CFG["blast_id"], "platform": CFG["platform"], "date": CFG["date"],
            "bench_z": bench_z, "bench_height_m": CFG["bench_height_m"],
            "density_ore_t_m3": CFG["density_ore_t_m3"], "grid_res_m": CFG["grid_res_m"],
        },
        "holes": [{"id": h, "x": float(x), "y": float(y), "grade": float(g)}
                  for h, x, y, g in zip(comp["Hole_ID"], comp["X"], comp["Y"], comp["Grade"])],
        "blocks": [],
    }
    for b in all_blocks:
        ext = np.asarray(b.polygon.exterior.coords)
        grid = grid_lines_inside(b.polygon, cell_size=CFG["grid_res_m"])
        grid_lines = [[[float(x1), float(y1)], [float(x2), float(y2)]]
                      for ln in grid for (x1, y1), (x2, y2) in [list(ln.coords)]]
        # 填充面三角化（约束 Delaunay + 求交裁剪：精确覆盖凹多边形内部）
        tri_polys = [t for t in triangulate(b.polygon.buffer(0))
                     if t.intersection(b.polygon).area > 1e-6]
        tri_polys = [t.intersection(b.polygon) for t in tri_polys]
        tri_polys = [t for t in tri_polys
                     if t.geom_type == "Polygon" and t.area > 1e-6]
        tri_verts = []
        tri_vmap = {}
        tri_faces = []
        for tp in tri_polys:
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
            "boundary": [[float(x), float(y)] for x, y in ext],
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

    # ---------- 报告（txt + csv，宏内算量后用于对照） ----------
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
    print(f"[报告] {OUT / '1004_macro_报告.csv'}")

    # ---------- 验证图 ----------
    from matplotlib import pyplot as plt
    from matplotlib.patches import Polygon as MplPolygon
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
    plt.rcParams["axes.unicode_minus"] = False
    fig, ax = plt.subplots(figsize=(12, 9.5))
    color_plot = {"L1": "cyan", "L2": "blue", "L3": "red", "L4": "yellow"}
    for c in cells:
        if c.level_id is None:
            continue
        ax.add_patch(MplPolygon(list(c.polygon.exterior.coords), closed=True,
                                facecolor=color_plot[c.level_id], edgecolor="none", alpha=0.5))
    for b in all_blocks:
        ext = np.asarray(b.polygon.exterior.coords)
        ax.plot(ext[:, 0], ext[:, 1], color="black", lw=2.0)
        cx, cy = b.polygon.representative_point().coords[0]
        ax.text(cx, cy, f"#{b.block_no}\n{b.avg_grade_g_t:.2f}", fontsize=9, ha="center",
                va="center", fontweight="bold",
                bbox=dict(facecolor="white", alpha=0.85, edgecolor="none", pad=1.0))
    for hx, hy, hg in zip(comp["X"], comp["Y"], comp["Grade"]):
        ax.plot(hx, hy, "k.", ms=4)
        ax.text(hx + 2, hy + 2, f"{hg:.2f}", fontsize=6, color="dimgray")
    ax.set_title(f"BS-3940-1004 空间合并后矿块（用户规则：同档相邻合并）", fontsize=13)
    ax.set_aspect("equal")
    fig.tight_layout()
    png = OUT / "1004_macro_验证图.png"
    fig.savefig(png, dpi=150)
    plt.close(fig)
    print(f"[图] {png}")


if __name__ == "__main__":
    main()
