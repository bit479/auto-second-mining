# -*- coding: utf-8 -*-
"""Step1 通用圈矿算量（参数化）：
用法: python prep_generic.py <xls> [platform] [date] [out_dir]
  xls      : 炮孔数据库 Excel（含 定位/测斜/blast 品位表）
  platform : 平台名（如 3940），缺省从文件名自动解析
  date     : 日期（如 1004），缺省从文件名自动解析
  out_dir  : 输出目录（含 blocks.json / 报告 csv/txt），缺省 = xls 同级 '二次圈矿成果_<platform>_<date>'
产出: <out_dir>/<blast_id>_blocks.json、<blast_id>_报告.txt/.csv
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import Delaunay
from shapely.geometry import MultiPolygon, Point, Polygon
from shapely.ops import unary_union

ROOT = Path(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型")
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from mdb_loader import load_xls_blast                       # noqa: E402
from voronoi import (GRADE_LEVELS, OreBlock, build_voronoi_cells,  # noqa: E402
                     classify_cells, merge_to_blocks)
from grid import grid_lines_inside                          # noqa: E402

COLOR = {"L1": (0, 255, 255), "L2": (0, 0, 255), "L3": (255, 0, 0), "L4": (255, 255, 0)}
REPORT_LABEL = {"L1": "0.500-1.000", "L2": "1.000-1.500", "L3": "1.500-3.000", "L4": "3.000-999.000"}
BLOCK_ORDER = ["L4", "L3", "L2", "L1"]
MERGE_DIST = 25.0
BENCH_HEIGHT_M = 10.0
DENSITY_ORE_T_M3 = 2.7
MIN_ORE_AREA_M2 = 15.0
GRID_RES_M = 1.0
# 圈矿边界参数（贴人工手圈）：Alpha Shape 保留边长 < 2*ALPHA_SHAPE_M 的三角形，
# 外扩 EDGE_BUFFER_M 米作为矿块边界（约半个孔距；外扩过大会吸进相邻档炮孔、稀释品位，
# 过小则矿块过碎，均不贴近人工圈连）。
ALPHA_SHAPE_M = 4.0
EDGE_BUFFER_M = 1.5
MIN_BLOCK_AREA = 80.0    # 面积小于该值的矿块并入最近相邻大块（跨档、数据驱动）


def alpha_shape_poly(xy: np.ndarray, alpha: float):
    """凹包：Delaunay 三角网，保留最长边 < 2*alpha 的三角形后合并。返回 Polygon/MultiPolygon 或 None。"""
    if len(xy) < 3:
        return None
    try:
        tri = Delaunay(xy)
    except Exception:
        return None
    polys = []
    for s in tri.simplices:
        p = xy[s]
        d = [float(np.hypot(*(p[(i + 1) % 3] - p[i]))) for i in range(3)]
        if max(d) < 2.0 * alpha:
            polys.append(Polygon(p))
    if not polys:
        return None
    return unary_union(polys)


def auto_alpha(xy: np.ndarray) -> float:
    """自适应凹包半径：取 Delaunay 边长中位数 × 0.75（保留边长 < 1.5×中位孔距的三角形）。"""
    try:
        tri = Delaunay(xy)
    except Exception:
        return ALPHA_SHAPE_M
    ds = []
    for s in tri.simplices:
        p = xy[s]
        ds += [float(np.hypot(*(p[(i + 1) % 3] - p[i]))) for i in range(3)]
    med = float(np.median(ds)) if ds else ALPHA_SHAPE_M
    return max(3.0, min(12.0, med * 0.75))


def square_around(pt, half):
    """围绕炮孔点的方形矿块（人工手圈单孔为小方框/折线，不用圆形 buffer）。"""
    x, y = float(pt[0]), float(pt[1])
    return Polygon([(x - half, y - half), (x + half, y - half),
                    (x + half, y + half), (x - half, y + half)])


def outline_for(xy: np.ndarray, alpha: float | None = None, edge: float = EDGE_BUFFER_M):
    """由孔点集合生成矿块边界（折线多边形，无圆弧）：
    成片孔 = 自适应凹包 + 尖角外扩（mitre/square，边界保持直线段）；
    孤立孔 = 围绕孔的方形框（半宽 edge+2 米）。"""
    if len(xy) == 0:
        return None
    if len(xy) == 1:
        return square_around(xy[0], edge + 1.0)
    a = alpha if alpha is not None else auto_alpha(xy)
    body = alpha_shape_poly(xy, a)
    polys = []
    if body is not None and body.area > 1e-6:
        polys.append(body.buffer(edge, join_style="mitre", cap_style="square", mitre_limit=3.0))
    for p in xy:
        if body is None or not body.contains(Point(*p)):
            polys.append(square_around(p, edge + 1.0))
    if not polys:
        return None
    # simplify(0.01) 仅移除 buffer 产生的连续重复顶点，边界仍为直线段、无圆弧
    return unary_union(polys).buffer(0).simplify(0.01)


def resolve_overlaps(blocks, H, D, CA, CF):
    """矿块间去重叠：高档优先（L4>L3>L2>L1），低档块扣除高档块已占区域，重新加权。
    CA=矿孔 Voronoi（孔数统计），CF=全孔 Voronoi（品位/矿量算量，对齐 3DMine）。"""
    ordered = sorted(blocks, key=lambda b: BLOCK_ORDER.index(b.level_id))
    kept = []
    for b in ordered:
        poly = b.polygon
        for k in kept:
            poly = poly.difference(k.polygon)
        poly = poly.buffer(0)
        if poly.is_empty or poly.area < MIN_ORE_AREA_M2:
            print(f"[去重叠] {b.level_id} 块({b.cell_count}孔)被高档矿块占满，剔除")
            continue
        parts = list(poly.geoms) if poly.geom_type == "MultiPolygon" else [poly]
        # 碎片（< MIN_BLOCK_AREA）处理：并入同档大 part 或碎片间链式合并，
        # 人工把同一矿化簇圈在一起，方块外扩间隙造成的 MultiPolygon 碎片不应被拆成独立矿块
        big = [p for p in parts if p.area >= MIN_BLOCK_AREA]
        small = [p for p in parts if p.area < MIN_BLOCK_AREA]
        if small:
            if big:
                for sp in small:
                    bp = min(big, key=lambda p: p.distance(sp))
                    big[big.index(bp)] = bp.union(sp)
                parts = big
            else:
                groups = []
                for sp in small:
                    placed = False
                    for g in groups:
                        if any(sp.distance(q) < MERGE_DIST for q in g):
                            g.append(sp)
                            placed = True
                            break
                    if not placed:
                        groups.append([sp])
                parts = [unary_union(g).buffer(0) for g in groups]
        for part in parts:
            if part.area < MIN_ORE_AREA_M2:
                continue
            n_in = sum(1 for c in CA if c.grade >= 0.5 and Point(c.x, c.y).within(part))
            kept.append(rebuild_block(b.level_id, [], part, H, D, CF, n_holes=n_in))
    return kept


def parse_platform_date(fname: str):
    """从文件名解析平台/日期：如 '1、3940平台 炮孔数据库1004.xls' -> (3940, 1004)"""
    s = str(fname)
    m = re.search(r"(\d{3,4})\s*平台", s)
    platform = m.group(1) if m else ""
    rest = s[m.end():] if m else s
    d = re.search(r"(\d{4})(?=\.\w+$|[^0-9]|$)", rest)
    date = d.group(1) if d else ""
    return platform, date


def rebuild_block(level_id, cells, poly, H, D, cells_all=None, n_holes=None):
    poly = poly.buffer(0)
    area = float(poly.area)
    if cells_all is not None:
        # 3DMine Voronoi 算量口径：矿块边界内全部孔（含废孔）的 Voronoi 单元与矿块
        # 交集面积加权；圈矿只圈矿孔（废孔不参与圈矿但参与块内算量，与人工报告一致）
        tot = 0.0
        wsum = 0.0
        n_in = 0
        for c in cells_all:
            inter = c.polygon.intersection(poly).area
            if inter > 1e-6:
                wsum += inter * c.grade
                tot += inter
                if c.grade >= 0.5 and Point(c.x, c.y).within(poly):
                    n_in += 1
        grade = wsum / tot if tot > 0 else 0.0
        n_holes = n_in if n_holes is None else n_holes
    else:
        area_w = sum(c.polygon.area for c in cells)
        grade = sum(c.grade * c.polygon.area for c in cells) / area_w if area_w > 0 else 0.0
    vol = area * H
    ton = vol * D
    return OreBlock(level_id, 0, poly, round(area, 1), round(vol, 1), round(ton, 1),
                    round(grade, 4), round(ton * grade, 0),
                    n_holes if n_holes is not None else len(cells), cells)


def _union_all(polys):
    from shapely.ops import unary_union
    return unary_union([p.buffer(0) for p in polys]).buffer(0)


def main():
    xls = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        r"D:\WK\N CRT\北部山头3940平台2026\7、单日数据\北部山头3940平台-1004\1、3940平台 炮孔数据库1004.xls")
    platform = sys.argv[2] if len(sys.argv) > 2 else ""
    date = sys.argv[3] if len(sys.argv) > 3 else ""
    if not platform or not date:
        p, d = parse_platform_date(xls.name)
        platform = platform or p
        date = date or d
    if not platform or not date:
        raise SystemExit(f"ERROR: 无法从文件名解析平台/日期，请显式传入 platform date: {xls.name}")
    out_dir = Path(sys.argv[4]) if len(sys.argv) > 4 else xls.parent / f"二次圈矿成果_{platform}_{date}"
    out_dir.mkdir(parents=True, exist_ok=True)
    blast_id = f"BS-{platform}-{date}"

    print(f"[Step1] 数据库: {xls}")
    print(f"[Step1] 平台={platform} 日期={date} blast_id={blast_id}")
    print(f"[Step1] 输出目录: {out_dir}")

    comp = load_xls_blast(xls)
    print(f"[数据] {len(comp)} 个炮孔")

    # 品位归属单元：全部孔（含废孔）Voronoi —— 矿块范围内各孔控制区域按品位加权
    cells_all = build_voronoi_cells(comp["X"].to_numpy(float), comp["Y"].to_numpy(float),
                                    comp["Grade"].to_numpy(float), comp["Hole_ID"].tolist())
    ore_mask = comp["Grade"].to_numpy(float) >= 0.5
    comp_ore = comp[ore_mask].reset_index(drop=True)
    print(f"[数据] >=0.5g/t 参与圈矿孔数 = {len(comp_ore)}（剔除 <0.5 废孔 {int((~ore_mask).sum())} 个）")

    H = BENCH_HEIGHT_M
    D = DENSITY_ORE_T_M3
    # 品位加权用全部孔（含废孔）Voronoi：3DMine 矿块算量覆盖块内所有孔的控制区域；
    # 圈矿边界仍只用矿孔（CA），废孔不参与圈矿但参与块内品位/矿量计算
    CF = build_voronoi_cells(comp["X"].to_numpy(float), comp["Y"].to_numpy(float),
                             comp["Grade"].to_numpy(float), comp["Hole_ID"].tolist())
    CA = build_voronoi_cells(comp_ore["X"].to_numpy(float), comp_ore["Y"].to_numpy(float),
                             comp_ore["Grade"].to_numpy(float), comp_ore["Hole_ID"].tolist())

    # ---- 圈矿边界：各档孔点 Alpha Shape 凹包 + 外扩（贴人工手圈，替代 Voronoi 单元并） ----
    blocks_by_level = {}
    for lv in GRADE_LEVELS:
        sel = comp_ore[(comp_ore["Grade"] >= lv["lo"]) & (comp_ore["Grade"] < lv["hi"])]
        pts = np.column_stack([sel["X"].to_numpy(float), sel["Y"].to_numpy(float)])
        if len(pts) == 0:
            blocks_by_level[lv["id"]] = []
            continue
        poly = outline_for(pts)
        if poly is None or poly.area < MIN_ORE_AREA_M2:
            blocks_by_level[lv["id"]] = []
            continue
        parts = list(poly.geoms) if poly.geom_type == "MultiPolygon" else [poly]
        bl = []
        for part in parts:
            if part.area < MIN_ORE_AREA_M2:
                continue
            n_in = sum(Point(px, py).within(part) for px, py in pts)
            bl.append(rebuild_block(lv["id"], [], part.buffer(0), H, D, CF, n_holes=int(n_in)))
        blocks_by_level[lv["id"]] = bl
        print(f"[{lv['id']}] {lv['label']}: {len(bl)} 块 -> "
              + ", ".join(f"#{i}({b.cell_count}孔,{b.area_m2:.0f}m2)" for i, b in enumerate(bl, 1)))

    def cluster_blocks(bs):
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
                poly = _union_all([b.polygon for b in group])
                merged.append(rebuild_block(group[0].level_id, [], poly, H, D, CF,
                                            n_holes=sum(b.cell_count for b in group)))
            else:
                merged.append(group[0])
        return merged

    hi_blocks = []
    for lv in ["L4", "L3", "L2"]:
        hi_blocks.extend(blocks_by_level.get(lv, []))
    lo_blocks = [b for b in blocks_by_level.get("L1", [])]

    # 数据驱动归并（替代旧版"L2 一律并入 L1"的硬编码）：
    #   ① 面积 < MIN_BLOCK_AREA 的碎块，或 ② 加权品位 < 0.5（低于工业品位）的矿块，
    #   并入最近的相邻大块（跨档、按空间距离）；并入后品位按块内全部孔单元重新加权。
    #   这样 1004（L2 为单孔碎块）并入 L1 保持 3 块版，而 1008（L2 成片 6 孔）独立成块。
    def merge_small_blocks(blocks, lo_blocks):
        """碎块归并（宿主制）：大块（≥MIN_BLOCK_AREA 且 ≥0.5）为并入宿主，碎块找最近宿主并入；
        并入后宿主面积增大、可继续吸收相邻碎块；无法并入的高品位碎块保留独立（人工独立圈）。"""
        cand = list(blocks) + list(lo_blocks)
        hosts = [b for b in cand if b.area_m2 >= MIN_BLOCK_AREA and b.avg_grade_g_t >= 0.5]
        frags = [b for b in cand if b not in hosts]
        hosts.sort(key=lambda b: BLOCK_ORDER.index(b.level_id) if b.level_id in BLOCK_ORDER else 99)
        frags.sort(key=lambda b: -b.area_m2)
        merged = list(hosts)
        for b in frags:
            best, best_key = None, None
            for mb in merged:
                d = b.polygon.distance(mb.polygon)
                lv_i = BLOCK_ORDER.index(b.level_id) if b.level_id in BLOCK_ORDER else len(BLOCK_ORDER) - 1
                mb_i = BLOCK_ORDER.index(mb.level_id) if mb.level_id in BLOCK_ORDER else len(BLOCK_ORDER) - 1
                if mb_i == lv_i:
                    allowed = 0        # 同档
                elif mb_i < lv_i:
                    allowed = 1        # 并入更高档（低→高）
                elif mb.avg_grade_g_t >= 1.0:
                    allowed = 1        # 并入相邻矿化簇（高→低但目标品位 ≥1.0）
                else:
                    allowed = 2        # 并入更低品位大块（拒绝，高品位碎块独立圈）
                key = (allowed, d)
                if best_key is None or key < best_key:
                    best_key = key
                    best = mb
            if best is not None and best_key[0] < 2 and best_key[1] < MERGE_DIST:
                poly = _union_all([b.polygon, best.polygon])
                nb = rebuild_block(best.level_id, [], poly, H, D, CF,
                                   n_holes=b.cell_count + best.cell_count)
                nb.block_no = best.block_no
                idx = next(i for i, mb in enumerate(merged) if mb is best)
                merged[idx] = nb
                if b.level_id != best.level_id:
                    print(f"[归并] {b.level_id}({b.cell_count}孔,{b.area_m2:.0f}m2) -> 并入 "
                          f"{best.level_id}({best.cell_count}孔) 距离{best_key[1]:.1f}m")
            elif b.avg_grade_g_t < 0.5:
                print(f"[提示] 矿块({b.level_id},{b.cell_count}孔,{b.area_m2:.0f}m2) 加权品位 "
                      f"{b.avg_grade_g_t:.3f} < 0.5 且无相邻矿块，按废石剔除")
            else:
                merged.append(b)
        return merged

    merged_blocks = merge_small_blocks(hi_blocks, lo_blocks)
    lo_blocks = [b for b in merged_blocks if b.level_id == "L1"]
    hi_blocks = [b for b in merged_blocks if b.level_id != "L1"]
    # 跨档碎块归并之后，再做同档空间合并（cluster）与品位回分。
    # 顺序不可颠倒：若先 cluster，同档碎块先并成大块，将不再参与跨档归并。
    hi_blocks = cluster_blocks(hi_blocks)
    lo_blocks = cluster_blocks(lo_blocks)
    for b in hi_blocks:
        b.level_id = "L4" if b.avg_grade_g_t >= 3.0 else ("L3" if b.avg_grade_g_t >= 1.5 else "L2")
    for lv in ["L4", "L3", "L2"]:
        for b in [x for x in hi_blocks if x.level_id == lv]:
            ins = [c.hole_id.split("-")[-1] for c in CA if Point(c.x, c.y).within(b.polygon)]
            print(f"[debug] cluster后 {lv} #{b.area_m2:.0f}m2 {b.cell_count}孔: {sorted(ins)}")

    # 矿块间去重叠（高档优先）：低档矿块扣除高档矿块已占区域，保证矿块互不侵入、各自独立
    resolved = resolve_overlaps(hi_blocks + lo_blocks, H, D, CA, CF)
    # 去重叠后同档相邻矿块再合并（人工把同品位矿化圈成整块便于开采，如 L1 15 孔应成一块）
    from collections import defaultdict
    by_lv = defaultdict(list)
    for b in resolved:
        by_lv[b.level_id].append(b)
    resolved = []
    for lv in BLOCK_ORDER:
        resolved += cluster_blocks(by_lv.get(lv, []))
    blocks_by_level = {"L4": [b for b in resolved if b.level_id == "L4"],
                       "L3": [b for b in resolved if b.level_id == "L3"],
                       "L2": [b for b in resolved if b.level_id == "L2"],
                       "L1": [b for b in resolved if b.level_id == "L1"]}

    all_blocks: list[OreBlock] = []
    for lv in BLOCK_ORDER:
        for b in blocks_by_level.get(lv, []):
            b.block_no = len(all_blocks) + 1
            all_blocks.append(b)
    # 最终品位强制回分（防档位与品位不一致）
    for b in all_blocks:
        b.level_id = ("L4" if b.avg_grade_g_t >= 3.0 else
                      ("L3" if b.avg_grade_g_t >= 1.5 else
                       ("L2" if b.avg_grade_g_t >= 1.0 else "L1")))
    all_blocks.sort(key=lambda b: BLOCK_ORDER.index(b.level_id))
    for i, b in enumerate(all_blocks, 1):
        b.block_no = i
    # 按孔点落在矿块边界内填充每块炮孔号（报告/图件/3ds 均引用此列表）
    for b in all_blocks:
        b.cells = [c for c in CA if c.grade >= 0.5 and Point(c.x, c.y).within(b.polygon)]
        b.cell_count = len(b.cells)
    for b in all_blocks:
        print(f"[矿块#{b.block_no}] {REPORT_LABEL[b.level_id]}: "
              f"{b.area_m2:.0f} m2 / {b.volume_m3:.0f} m3 / {b.tonnage_t:.0f} t / "
              f"{b.avg_grade_g_t:.4f} g/t / {b.cell_count} 孔")

    from shapely.ops import triangulate
    bench_z = float(comp["Z"].median())
    data = {
        "meta": {
            "blast_id": blast_id, "platform": platform, "date": date,
            "bench_z": bench_z, "bench_height_m": H,
            "density_ore_t_m3": D, "grid_res_m": GRID_RES_M,
            "_xls": str(xls),
        },
        "holes": [{"id": h, "x": float(x), "y": float(y), "grade": float(g)}
                  for h, x, y, g in zip(comp["Hole_ID"], comp["X"], comp["Y"], comp["Grade"])],
        "blocks": [],
    }
    for b in all_blocks:
        polys = list(b.polygon.geoms) if b.polygon.geom_type == "MultiPolygon" else [b.polygon]
        polys = [p.buffer(0) for p in polys if p.area > 1e-6]
        parts = [[[float(x), float(y)] for x, y in np.asarray(p.exterior.coords)] for p in polys]
        grid_lines = []
        for pp in polys:
            for ln in grid_lines_inside(pp, cell_size=GRID_RES_M):
                for (x1, y1), (x2, y2) in [list(ln.coords)]:
                    grid_lines.append([[float(x1), float(y1)], [float(x2), float(y2)]])
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
            "tonnage_t": round(b.tonnage_t, 3), "avg_grade_g_t": round(b.avg_grade_g_t, 4),
            "metal_g": round(b.metal_g, 3),
            "grid_lines": grid_lines,
            "tri_verts": tri_verts, "tri_faces": tri_faces,
        })
    json_path = out_dir / f"{blast_id}_blocks.json"
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[JSON] {json_path}")

    lines = [f"{'体号':<5}{'品位类型':<14}{'面积m2':>9}{'体积m3':>10}{'重量t':>11}"
             f"{'平均品位g/t':>12}{'金属量g':>10}  炮孔数  炮孔号"]
    for b in all_blocks:
        holes_s = "、".join(c.hole_id.split("-")[-1] for c in b.cells)
        lines.append(f"#{b.block_no:<4}{REPORT_LABEL[b.level_id]:<14}{b.area_m2:>9.1f}"
                     f"{b.volume_m3:>10.1f}{b.tonnage_t:>11.1f}{b.avg_grade_g_t:>12.4f}"
                     f"{b.metal_g:>10.0f}  {b.cell_count:<5}{holes_s}")
    (out_dir / f"{blast_id}_报告.txt").write_text("\n".join(lines), encoding="utf-8")

    rows = []
    for lv in BLOCK_ORDER:
        bs = [b for b in all_blocks if b.level_id == lv]
        if not bs:
            continue
        for b in bs:
            rows.append({"类型": REPORT_LABEL[lv], "体号": b.block_no, "体积": round(b.volume_m3, 3),
                         "重量（t）": round(b.tonnage_t, 3), "平均品位(Au)": round(b.avg_grade_g_t, 4),
                         "金属量（百克）": round(b.metal_g / 100.0, 3)})
        st = sum(b.tonnage_t for b in bs)
        sm = sum(b.metal_g for b in bs)
        rows.append({"类型": "小计", "体号": None, "体积": round(sum(b.volume_m3 for b in bs), 3),
                     "重量（t）": round(st, 3), "平均品位(Au)": round(sm / st, 4),
                     "金属量（百克）": round(sm / 100.0, 3)})
    t_all = sum(b.tonnage_t for b in all_blocks)
    m_all = sum(b.metal_g for b in all_blocks)
    rows.append({"类型": "合计", "体号": None, "体积": round(sum(b.volume_m3 for b in all_blocks), 3),
                 "重量（t）": round(t_all, 3), "平均品位(Au)": round(m_all / t_all, 4),
                 "金属量（百克）": round(m_all / 100.0, 3)})
    pd.DataFrame(rows).to_csv(out_dir / f"{blast_id}_报告.csv", index=False, encoding="utf-8-sig")
    print(f"[报告] {out_dir / f'{blast_id}_报告.txt'} / .csv")
    print("[Step1] 完成")


if __name__ == "__main__":
    main()
