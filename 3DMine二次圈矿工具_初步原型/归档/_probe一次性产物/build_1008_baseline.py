# -*- coding: utf-8 -*-
"""由人工 1008 图（scan_manual_dwg.py 抽出的 JSON）+ 人工报告，生成验收基准文件。

输出：
  D:\\WK\\N CRT\\Test\\1008_baseline\\人工1008_基准.json
  D:\\WK\\N CRT\\Test\\1008_baseline\\人工1008_基准.md
"""
from __future__ import annotations

import json
from pathlib import Path

import xlrd
from shapely.geometry import Point, Polygon

PROBE = Path(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\_probe")
SCAN = PROBE / "manual_1008_full.json"
XLS = Path(r"D:\WK\N CRT\北部山头3940平台2026\7、单日数据\北部山头3940平台-1008"
           r"\1、3940平台 炮孔数据库1008.xls")
OUTDIR = Path(r"D:\WK\N CRT\Test\1008_baseline")

# 人工报告（新，2026-10-09 13:51 版）
REPORT = [
    {"no": 1, "level": "0.500-1.000", "volume_m3": 714.095, "tonnage_t": 1928.056,
     "grade": 0.680, "metal_hg": 13.111},
    {"no": 2, "level": "0.500-1.000", "volume_m3": 1327.522, "tonnage_t": 3584.311,
     "grade": 0.729, "metal_hg": 26.134},
    {"no": 3, "level": "1.000-1.500", "volume_m3": 1909.877, "tonnage_t": 5156.668,
     "grade": 1.204, "metal_hg": 62.104},
]


def load_holes():
    wb = xlrd.open_workbook(str(XLS))
    loc, bl = wb.sheet_by_name("定位表"), wb.sheet_by_name("pit_blast")
    holes = {}
    for r in range(1, loc.nrows):
        hid = str(loc.cell_value(r, 0)).strip()
        holes[hid] = {"x": loc.cell_value(r, 1), "y": loc.cell_value(r, 2),
                      "z": loc.cell_value(r, 3), "depth": loc.cell_value(r, 5)}
    for r in range(1, bl.nrows):
        hid = str(bl.cell_value(r, 0)).strip()
        if hid in holes:
            holes[hid]["grade"] = bl.cell_value(r, 3)
    return holes


def main() -> None:
    scan = json.loads(SCAN.read_text(encoding="utf-8"))
    holes = load_holes()

    outlines = []
    for p in scan["polylines"]:
        if p["layer"] not in ("0", "0.500-1.000", "1.000-1.500",
                              "1.500-3.000", "3.000-999.000"):
            continue
        pts = p["pts"]
        if pts[0] != pts[-1]:
            pts = pts + [pts[0]]
        outlines.append({"layer": p["layer"], "pts": pts,
                         "area_m2": round(Polygon(pts).buffer(0).area, 4)})

    labels = [{"txt": t["txt"], "pos": t["pos"]}
              for t in scan["texts"] if t["kind"] == "AcDbMText"]
    leaders = scan["lines"]

    blocks = []
    for o in outlines:
        poly = Polygon(o["pts"]).buffer(0)
        inside = sorted(h for h, v in holes.items()
                        if poly.contains(Point(v["x"], v["y"])))
        blocks.append({
            "layer": o["layer"],
            "area_drawn_m2": o["area_m2"],
            "volume_drawn_m3": round(o["area_m2"] * 10, 4),
            "holes": inside,
            "hole_count": len(inside),
            "grade_arith_mean": round(sum(holes[h]["grade"] for h in inside) / len(inside), 6)
            if inside else None,
            "outline": o["pts"],
        })

    # 与人工报告按品位就近配对
    for b in blocks:
        best, bestd = None, 9e9
        for r in REPORT:
            if r in [x for x in blocks if x.get("report_no")]:
                continue
            d = abs(b["grade_arith_mean"] - r["grade"])
            if d < bestd:
                best, bestd = r, d
        if best is not None:
            b["report_no"] = best["no"]
            b["report"] = best
            b["area_reported_m2"] = round(best["volume_m3"] / 10, 4)
            b["area_ratio_reported_over_drawn"] = round(
                b["area_reported_m2"] / b["area_drawn_m2"], 4)

    data = {
        "source_dwg": scan["dwg"],
        "source_xls": str(XLS),
        "bench_height_m": 10.0,
        "density_t_m3": 2.7,
        "report": REPORT,
        "report_total": {
            "volume_m3": round(sum(r["volume_m3"] for r in REPORT), 4),
            "tonnage_t": round(sum(r["tonnage_t"] for r in REPORT), 4),
            "metal_hg": round(sum(r["metal_hg"] for r in REPORT), 4),
        },
        "block_labels": labels,
        "block_leaders": leaders,
        "blocks": blocks,
        "hole_count_total": len(holes),
        "ore_holes": sorted(h for h, v in holes.items() if v.get("grade", 0) >= 0.5),
    }
    OUTDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / "人工1008_基准.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    L = ["# 人工 1008 二次圈矿 · 验收基准（由人工图与人工报告反查）", "",
         "- 人工图：%s" % scan["dwg"],
         "- 数据库：%s" % XLS,
         "- 台阶高 %.1f m，容重 %.2f" % (10.0, 2.7), "",
         "## 人工报告（新，3 块）", "",
         "| 类型 | 体号 | 体积 m³ | 重量 t | 平均品位 | 金属量 百克 |",
         "|---|---|---|---|---|---|"]
    for r in REPORT:
        L.append("| %s | %d | %.3f | %.3f | %.3f | %.3f |"
                 % (r["level"], r["no"], r["volume_m3"], r["tonnage_t"], r["grade"], r["metal_hg"]))
    t = data["report_total"]
    L.append("| 合计 | | %.3f | %.3f | | %.3f |" % (t["volume_m3"], t["tonnage_t"], t["metal_hg"]))
    L += ["", "## 人工图上手画的矿界轮廓（%d 条）" % len(blocks), "",
          "| 轮廓图层 | 图上面积 m² | ×10m 体积 m³ | 含孔数 | 孔品位算术均值 | 对应报告体号 | 报告面积 m² | 报告/图上 |",
          "|---|---|---|---|---|---|---|---|"]
    for b in sorted(blocks, key=lambda x: x["report_no"] or 99):
        L.append("| %s | %.4f | %.4f | %d | %s | %s | %s | %s |"
                 % (b["layer"], b["area_drawn_m2"], b["volume_drawn_m3"], b["hole_count"],
                    ("%.4f" % b["grade_arith_mean"]) if b["grade_arith_mean"] else "-",
                    b.get("report_no", "-"),
                    ("%.4f" % b["area_reported_m2"]) if b.get("area_reported_m2") else "-",
                    ("%.4f" % b["area_ratio_reported_over_drawn"])
                    if b.get("area_ratio_reported_over_drawn") else "-"))
    L += ["", "## 逐块孔归属", ""]
    for b in sorted(blocks, key=lambda x: x["report_no"] or 99):
        L.append("- 报告 %s 号（%s）：%s" % (
            b.get("report_no", "?"), b["layer"],
            "、".join(h.split("-")[-1] for h in b["holes"])))
    L += ["", "## 待确认", "",
          "1. 图上矿界面积×10 与人工报告体积不一致（比值 1.10 / 1.15 / 1.16），3DMine 的体积口径待你确认。",
          "2. 1008 有两版人工报告：本文件用今天 13:51 的 3 块版（合计 3951.494 m³）；",
          "   `handle\\3940平台 1008炮孔数据报告.xlsx` 是 4 块版（合计 2903.655 m³）。验收以哪版为准待确认。"]
    (OUTDIR / "人工1008_基准.md").write_text("\n".join(L), encoding="utf-8")

    print("blocks:", len(blocks))
    for b in sorted(blocks, key=lambda x: x["report_no"] or 99):
        print("  报告%s号 图上%.3f m²  -> 体积%.3f  (报告 %.3f, 比 %.4f)  孔%d 均值%.4f"
              % (b.get("report_no"), b["area_drawn_m2"], b["volume_drawn_m3"],
                 b.get("report", {}).get("volume_m3", 0),
                 b.get("area_ratio_reported_over_drawn", 0),
                 b["hole_count"], b["grade_arith_mean"]))
    print("saved ->", OUTDIR)


if __name__ == "__main__":
    main()
