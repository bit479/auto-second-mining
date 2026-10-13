# -*- coding: utf-8 -*-
"""批量圈矿：把一个目录下的多个单日炮区一次跑完，出横向汇总。

用法:
  python run_batch.py <父目录> <综合图.dwg> [输出目录] [--full]

  父目录 ：里面每个子目录放一天的炮孔数据库（如 "7、单日数据"）
  综合图 ：该平台的年度综合图 DWG（所有天共用）
  --full ：除了汇总，还给每天生成完整三件套（慢）

产出（输出目录，缺省 = 父目录）:
  批量汇总.xlsx    两个表：明细（每块一行）、按日合计
  批量汇总.png     按日的体积/金属量横向对比
  批量总览.png     每天一张分块图拼在一起
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun"]
matplotlib.rcParams["axes.unicode_minus"] = False

sys.path.insert(0, str(Path(__file__).resolve().parent))

from oreblocks import load_holes_xls                        # noqa: E402
from pipeline import run_blast                              # noqa: E402
from run_strip import DENSITY                               # noqa: E402
import params as _params                                    # noqa: E402

COLORS = {"L4": "#f4b183", "L3": "#ffd966", "L2": "#b4a7d6", "L1": "#a9d6d0"}
LV_TXT = {"L4": "≥3", "L3": "1.5-3", "L2": "1-1.5", "L1": "0.5-1"}


def parse_folder(name: str):
    m = re.search(r"(\d{3,4})\s*平台", name)
    plat = m.group(1) if m else ""
    d = re.search(r"-\s*(\d{4})\s*$", name) or re.search(r"(\d{4})", name)
    return plat, (d.group(1) if d else "")


def run_day(folder: Path, comp):
    xls = sorted(folder.glob("1、*.xls")) or sorted(folder.glob("*.xls"))
    if not xls:
        return None
    xls = xls[0]
    plat, date = parse_folder(folder.name)
    if not date:
        plat2, date = parse_folder(xls.name)
        plat = plat or plat2
    P = _params.for_blast(date, platform=plat)
    holes = load_holes_xls(xls)
    res = run_blast(holes, list(holes.values()), P, comp, blast=date)
    if not res["blocks"]:
        return None
    res.update({"date": date, "platform": plat, "folder": folder, "xls": xls,
                "params": P, "holes": res["holes"],
                "ring": res["rings"][0] if res["rings"] else None})
    return res


def write_summary_xlsx(out: Path, results, comp=None) -> None:
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "明细"
    ws.append(["日期", "体号", "类型", "面积(m²)", "体积(m³)", "重量(t)",
               "平均品位(Au)", "金属量（百克）", "炮孔"])
    for r in results:
        for b in r["blocks"]:
            ws.append([r["date"], b.no, b.label, round(b.area_m2, 3),
                       round(b.volume_m3, 3), round(b.tonnage_t, 3),
                       round(b.grade, 3), round(b.metal_hg, 3),
                       "、".join(h.short for h in b.holes)])
    ws2 = wb.create_sheet("按日合计")
    ws2.append(["日期", "矿孔数", "矿块数", "体积(m³)", "重量(t)", "金属量（百克）"])
    for r in results:
        ws2.append([r["date"], len(r["ore"]), len(r["blocks"]),
                    round(sum(b.volume_m3 for b in r["blocks"]), 3),
                    round(sum(b.tonnage_t for b in r["blocks"]), 3),
                    round(sum(b.metal_hg for b in r["blocks"]), 3)])
    ws3 = wb.create_sheet("参数")
    ws3.append(["日期", "外推(m)", "连接半径(m)", "最小块段(m²)", "接综合图(m)", "矿界自检"])
    for r in results:
        P = r.get("params", {})
        ws3.append([r["date"], P.get("extrude_m"), P.get("zone_link_m"),
                    P.get("min_fragment_m2"), P.get("merge_gap_m"),
                    "；".join(r.get("warn") or []) or "OK"])
    # 是否已并入综合图（按几何重合度判，见 core/merge_status.py）
    if comp:
        ws4 = wb.create_sheet("并图状态")
        ws4.append(["日期", "已并入块数", "总块数", "各块与综合图的最大重叠率"])
        for r in results:
            hit = 0
            det = []
            for b in r["blocks"]:
                best = 0.0
                if b.polygon is not None and not b.polygon.is_empty:
                    for layer, _c, poly in comp:
                        if poly is None or poly.is_empty or not poly.intersects(b.polygon):
                            continue
                        best = max(best, poly.intersection(b.polygon).area
                                   / max(b.polygon.area, 1e-9))
                hit += int(best >= 0.80)
                det.append("%d号%.0f%%" % (b.no, best * 100))
            ws4.append([r["date"], hit, len(r["blocks"]), " ".join(det)])
    xlsx = out / "批量汇总.xlsx"
    wb.save(xlsx)
    print("汇总表 ->", xlsx)


def write_summary_png(out: Path, results) -> None:
    fig, ax = plt.subplots(figsize=(1.6 * len(results) + 4, 6), dpi=110)
    x = list(range(len(results)))
    bottom = [0.0] * len(results)
    for one in ("L4", "L3", "L2", "L1"):
        vals = [sum(b.volume_m3 for b in r["blocks"] if b.level_id == one)
                for r in results]
        ax.bar(x, vals, bottom=bottom, color=COLORS[one], label=LV_TXT[one])
        bottom = [a + b for a, b in zip(bottom, vals)]
    top = max(bottom) if bottom else 1.0
    for i, r in enumerate(results):
        ax.text(i, bottom[i] + top * 0.02,
                "%.0f m³\n%.1f 百克" % (bottom[i],
                                        sum(b.metal_hg for b in r["blocks"])),
                ha="center", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels([r["date"] for r in results])
    ax.set_ylabel("体积 (m³)")
    ax.set_title("各炮区二次圈矿体积（按品位档堆叠）")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    p = out / "批量汇总.png"
    fig.savefig(p)
    plt.close(fig)
    print("汇总图 ->", p)


def write_overview_png(out: Path, results) -> None:
    n = len(results)
    cols = min(4, n)
    rows_n = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows_n, cols, figsize=(5.2 * cols, 7.2 * rows_n), dpi=95)
    axes = list(getattr(axes, "flat", [axes]))
    for ax, r in zip(axes, results):
        for b in r["blocks"]:
            if b.polygon is None:
                continue
            for g in getattr(b.polygon, "geoms", [b.polygon]):
                xs, ys = g.exterior.xy
                ax.fill(xs, ys, color=COLORS.get(b.level_id, "#ccc"), alpha=0.6, zorder=2)
                ax.plot(xs, ys, color="#0b7a6b", lw=1.1, zorder=4)
            c = b.polygon.representative_point()
            ax.text(c.x, c.y, "%d号\n%.0f m³\n%.2f" % (b.no, b.volume_m3, b.grade),
                    ha="center", va="center", fontsize=6, zorder=9)
        for h in r["holes"]:
            ax.plot([h.x], [h.y], marker="+", ms=4, mew=1.0,
                    color="#0b4f4f" if h.grade >= 0.5 else "#b0b0b0", zorder=7)
        ax.set_title("%s  %d 块 / %.0f m³"
                     % (r["date"], len(r["blocks"]),
                        sum(b.volume_m3 for b in r["blocks"])), fontsize=10)
        ax.set_aspect("equal")
        ax.grid(alpha=0.2)
    for ax in axes[len(results):]:
        ax.axis("off")
    fig.tight_layout()
    p = out / "批量总览.png"
    fig.savefig(p)
    plt.close(fig)
    print("总览图 ->", p)


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        return
    parent = Path(sys.argv[1])
    comp_dwg = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    out = Path(sys.argv[3]) if len(sys.argv) > 3 and not sys.argv[3].startswith("--") \
        else parent
    full = "--full" in sys.argv
    out.mkdir(parents=True, exist_ok=True)

    comp = []
    if comp_dwg and comp_dwg.exists():
        from composite import load_composite_blocks
        comp = load_composite_blocks(comp_dwg)
        print("综合图历史矿块 %d 个" % len(comp))

    results = []
    for f in sorted(d for d in parent.iterdir() if d.is_dir()):
        r = run_day(f, comp)
        if r is None:
            continue
        results.append(r)
        print("%-10s 矿孔%3d  %2d 块  %9.1f m3  %8.1f 百克   %s"
              % (r["date"], len(r["ore"]), len(r["blocks"]),
                 sum(b.volume_m3 for b in r["blocks"]),
                 sum(b.metal_hg for b in r["blocks"]),
                 ("自检:" + "；".join(r["warn"])) if r["warn"] else ""))
    if not results:
        print("没找到任何单日炮区（子目录里要有 1、*.xls）")
        return

    write_summary_xlsx(out, results, comp=comp)
    write_summary_png(out, results)
    write_overview_png(out, results)

    if full:
        import subprocess
        py = sys.executable
        core = Path(__file__).resolve().parent
        for r in results:
            day_out = r["folder"] / ("二次圈矿成果_%s_%s"
                                     % (r["platform"] or "?", r["date"]))
            print("== %s 出三件套 -> %s" % (r["date"], day_out))
            subprocess.run([py, "-X", "utf8", str(core / "run_strip.py"),
                            str(r["xls"]), r["platform"], r["date"], str(day_out),
                            str(comp_dwg)], check=False)


if __name__ == "__main__":
    main()
