# -*- coding: utf-8 -*-
"""一键出三件套（条带法核心，人工流程复刻）。

用法:
  python run_strip.py <炮孔数据库.xls> [平台] [日期] [输出目录] [综合图.dwg]

流程：
  读库 - 矿孔分档 - 孤立单孔剔除（列待取样）- 走向中线分左右链
  - 链局部法向外推 3 m + 端部中点闭合 - 外围矿界
  - 外围矿界内按品位档分块（块内 Voronoi 算量）
  - 与综合图合并（<=4.5 m，重新编号）/ 空白区标注 - 报告 + 图 + .3ds
"""
from __future__ import annotations

import math
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from deliver import (write_3ds, write_dxf, write_report_png,   # noqa: E402
                     write_report_xlsx)
from oreblocks import load_holes_xls                           # noqa: E402
from pipeline import pick_zone, run_blast                      # noqa: E402
import params as _params                                       # noqa: E402

DENSITY = 2.7


def parse_tag(name: str):
    m = re.search(r"(\d{3,4})\s*平台", name)
    plat = m.group(1) if m else ""
    rest = name[m.end():] if m else name
    d = re.search(r"(\d{4})(?=\.\w+$|[^0-9]|$)", rest)
    return plat, (d.group(1) if d else "")


# 孤立孔判定：矿孔之间相距 ≤ 15 m 才算"连在同一条矿化带上"（用户 2026-10-10 定）。
# 依据：1004 人工图把北边间隔 10.6~13.9 m 的孔都连成一条；1008 的 P43 离主带 21.4 m 没圈。
# 现在这段逻辑在 pipeline.py，这里保留常量名给别的脚本引用。
ZONE_LINK_M = 15.0


def main() -> None:
    t0 = time.time()
    if len(sys.argv) < 2:
        print("用法: python run_strip.py <炮孔数据库.xls> [平台] [日期] "
              "[输出目录] [综合图.dwg] [--manual-blocks a.3ds;b.3ds] [--outline a.3ds]")
        sys.exit(2)
    xls = Path(sys.argv[1])
    if not xls.exists():
        print("[错误] 找不到炮孔数据库：%s" % xls)
        sys.exit(2)
    if xls.suffix.lower() not in (".xls", ".xlsx"):
        print("[错误] 炮孔数据库应当是 .xls/.xlsx，收到的是：%s" % xls.name)
        sys.exit(2)
    plat = sys.argv[2] if len(sys.argv) > 2 else ""
    date = sys.argv[3] if len(sys.argv) > 3 else ""
    if not plat or not date:
        p, d = parse_tag(xls.name)
        plat, date = plat or p, date or d
    if not date:
        print("[错误] 认不出日期（炮区号），请在命令行给第 3 个参数，"
              "或把文件名写成含 4 位日期（如 …炮孔数据库1008.xls）")
        sys.exit(2)
    out_dir = Path(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4] else \
        xls.parent / ("二次圈矿成果_%s_%s" % (plat or "?", date or "?"))
    out_dir.mkdir(parents=True, exist_ok=True)
    comp_dwg = sys.argv[5] if len(sys.argv) > 5 and sys.argv[5] else None
    # 命令行覆盖两个"人工画线"参数（GUI 用它把界面上的选择直接传进来，不用先存参数）：
    #   --manual-blocks  人工圈矿模式：每条闭合线 = 一块，程序不再自己圈
    #   --outline        精确模式：整条当矿界，界内程序按品位再分块
    manual_blocks = outline = None
    for key, idx in (("--manual-blocks", None), ("--outline", None)):
        if key in sys.argv:
            i = sys.argv.index(key)
            if i + 1 < len(sys.argv):
                val = [x.strip() for x in sys.argv[i + 1].split(";") if x.strip()]
                if key == "--manual-blocks":
                    manual_blocks = val
                else:
                    outline = val
    # 没在命令行/参数里给 .3ds 时，**自己去炮区文件夹里找**（用户 2026-10-15：
    # 他的习惯就是把"选择集对象.3ds"放在数据库旁边，希望程序直接用）。
    auto_3ds = None
    if not manual_blocks and not outline:
        cands = sorted(xls.parent.glob("*.3ds"))
        if cands:
            # 优先"分品位"那份（他自己按品位分好的），否则取第一个
            pick = next((c for c in cands if "分品位" in c.name), cands[0])
            from strip import read_3ds_polylines as _r3
            n = len(_r3(pick))
            auto_3ds = (pick, n)
            if n <= 1:
                outline = [str(pick)]
            else:
                manual_blocks = [str(pick)]
    log = []

    def note(s):
        print(s)
        log.append(s)

    meta = {"platform": plat or "?", "date": date or "?", "density": DENSITY}
    P = _params.for_blast(date, platform=plat)
    if manual_blocks:
        P["manual_blocks"] = list(manual_blocks)
    if outline:
        P["outline_files"] = list(outline)
    if P.get("manual_blocks"):
        note("模式：**人工圈矿**（%d 个 .3ds：每条闭合线当一块，程序只算量出图）"
             % len(P["manual_blocks"]))
        note("参数：容重 废 %.2f / 矿 %.2f；金属量 = 重量×品位÷100（百克，3 位小数）"
             % (P.get("density_waste", 2.65), P.get("density_ore", 2.7)))
    elif P.get("outline_files"):
        note("模式：**精确模式**（%d 个 .3ds：整条当矿界、界内按品位档分块；矿界原样用，"
             "不抽稀/不修补/不并综合图）" % len(P["outline_files"]))
    else:
        note("参数：外推 %.2f m / 连接半径 %.1f m / 最小块段 %.0f m² / 接综合图 %.1f m"
             % (P["extrude_m"], P["zone_link_m"], P["min_fragment_m2"], P["merge_gap_m"]))
    if auto_3ds:
        note("[自动取用] 炮区文件夹里的 %s（%d 条闭合线）——"
             "不想用它就在界面上指定别的 .3ds，或把该文件移开" % (auto_3ds[0].name, auto_3ds[1]))

    comp = []
    if comp_dwg:
        from composite import load_composite_blocks
        comp = load_composite_blocks(comp_dwg)
        if comp:
            note("综合图历史矿块 %d 个" % len(comp))
        else:
            note("[提示] 综合图没读到历史矿块——要么该图没有，要么 AutoCAD 没开且没有扫描缓存。"
                 "程序会照常出成果，只是不做「与综合图合并」这一步。")

    try:
        holes = load_holes_xls(xls)
    except Exception as exc:
        note("[错误] 读炮孔数据库失败：%s" % exc)
        print("       需要的工作表：定位表（工程号/开孔坐标E/开孔坐标N/最大孔深）、"
              "测斜表、pit_blast（工程号/从/至/Au）")
        sys.exit(2)
    allh = list(holes.values())
    try:
        res = run_blast(holes, allh, P, comp, blast=date)
    except Exception as exc:
        note("[错误] 圈矿计算失败：%s" % exc)
        sys.exit(2)
    ore, pending, blocks = res["ore"], res["pending"], res["blocks"]
    note("数据库: %s" % xls)
    note("炮孔 %d 个；矿孔 %d 个；主矿化带 %d 孔；孤立待取样 %d 组"
         % (len(allh), len([h for h in allh if h.grade >= 0.5]),
            len(ore), len(pending)))
    if not blocks:
        note("[错误] 没圈出任何矿块：可能该炮区一个够品位的孔都没有，"
             "或者（%s）——请核对数据库。" % "矿孔少于 2 个")
        sys.exit(2)

    for w in res["warn"]:
        note("   [矿界自检] %s（已自动修补成单块并把矿孔包进来，建议目视复核）" % w)
    for r in res["rings"]:
        note("外围矿界面积 = %.3f m2" % r.area)
    from strip import LAST_RING
    mb = LAST_RING.get("merged_block")
    cands = [c for c in comp if mb is not None and c[2] is mb] or None
    for b in blocks:
        note("   %d 号 %s  %9.3f m2  %10.3f m3  %10.3f t  %.3f g/t  %.3f 百克  (%s)"
             % (b.no, b.label, b.area_m2, b.volume_m3, b.tonnage_t, b.grade,
                b.metal_hg, "、".join(h.short for h in b.holes)))
    tv = sum(b.volume_m3 for b in blocks)
    tt = sum(b.tonnage_t for b in blocks)
    tm = sum(b.metal_hg for b in blocks)
    note("合计 %.3f m3 / %.3f t / %.3f 百克" % (tv, tt, tm))
    if pending:
        note("未圈闭区域（缺工程，待取样验证后再进行施工）：")
        for g in pending:
            note("   " + "、".join(h.short for h in g))

    tag = "%s平台 %s" % (meta["platform"], meta["date"])
    xlsx = out_dir / ("%s炮孔数据报告.xlsx" % tag)
    png = out_dir / ("%s炮孔数据报告.png" % tag)
    dxf = out_dir / ("%s二次圈矿矿块图.dxf" % tag)
    tds = out_dir / ("%s矿块边界线.3ds" % tag)
    made = []
    try:
        write_report_xlsx(blocks, meta, xlsx, allh)
        made.append(xlsx)
        png_used, pw, ph = write_report_png(blocks, meta, allh, png)
        made.append(Path(png_used))
        write_dxf(blocks, allh, [], meta, dxf,
                  report_png=png_used, report_px=(pw, ph),
                  pending=[("L1", g) for g in pending], composite_blocks=comp,
                  merge_candidates=cands,
                  # 用了人工画的 .3ds（人工圈矿 / 精确模式）：**不并综合图、不画综合图参照线**——
                  # 成果图必须严格就是我画的那几条线（用户 2026-10-15）
                  check_merge=not (P.get("manual_blocks") or P.get("outline_files")))
        made.append(dxf)
        _keep_comp = None if (P.get("manual_blocks") or P.get("outline_files")) else comp
        _keep_cands = None if (P.get("manual_blocks") or P.get("outline_files")) else cands
        write_3ds(blocks, meta, tds,
                  composite_blocks=_keep_comp, merge_candidates=_keep_cands)
        made.append(tds)
    except PermissionError as exc:
        note("[错误] 有成果文件正被占用（多半是 Excel/CAD 开着同名文件）：%s" % exc)
        print("       关掉占用它的程序再跑一次即可；已生成的其它文件不会丢。")
        _write_runlog(out_dir, tag, xls, comp_dwg, P, meta, made, log, t0, ok=False)
        sys.exit(3)
    except Exception as exc:
        note("[错误] 写成果文件失败：%s" % exc)
        _write_runlog(out_dir, tag, xls, comp_dwg, P, meta, made, log, t0, ok=False)
        sys.exit(3)
    note("完成 -> %s" % out_dir)
    _write_runlog(out_dir, tag, xls, comp_dwg, P, meta, made, log, t0, ok=True)


def _write_runlog(out_dir: Path, tag: str, xls: Path, comp_dwg, P: dict,
                  meta: dict, made, log, t0: float, ok: bool) -> None:
    """在成果目录写一份「运行记录.txt」：参数、输入、耗时、产生的文件。"""
    try:
        lines = ["%s 二次圈矿运行记录" % tag,
                 "运行时间：%s" % time.strftime("%Y-%m-%d %H:%M:%S"),
                 "结果：%s" % ("成功" if ok else "未完成（见下面日志）"),
                 "总耗时：%.1f 秒" % (time.time() - t0),
                 "",
                 "【输入】",
                 "  炮孔数据库：%s" % xls,
                 "  综合图 DWG：%s" % (comp_dwg or "（未提供）"),
                 "【参数】",
                 "  " + " / ".join("%s=%s" % (k, v) for k, v in P.items()
                                   if k != "platform_used"),
                 "【产出文件】"]
        lines += ["  %s" % p for p in made] or ["  （无）"]
        lines += ["", "【运行日志】"] + ["  " + s for s in log]
        (out_dir / "运行记录.txt").write_text("\n".join(lines), encoding="utf-8")
        print("运行记录 -> %s" % (out_dir / "运行记录.txt"))
    except Exception as exc:
        print("（运行记录写失败：%s）" % exc)


if __name__ == "__main__":
    main()
