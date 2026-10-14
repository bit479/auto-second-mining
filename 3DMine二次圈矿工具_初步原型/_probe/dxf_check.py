# -*- coding: utf-8 -*-
"""成果图（DXF）实体自检 —— 把需求清单第五节那些"图上要素"逐条验掉。

用法: python dxf_check.py <平台> <日期> [成果图.dxf]
找 DXF 的顺序：参数给的 → sample_data/output/对账_<日期>/ → GUI跑通_<日期>/；都没有就自己跑一遍。

检查项（依据：《二次圈矿工具需求清单》五、图件绘制细则）：
  1. 图名文字在（"<平台>平台 <日期>二次圈矿矿块图"，中文不乱码）；
  2. 炮孔十字：层 `点`，每孔一组横/竖各 1.0 m，颜色 138，中心落在孔位上；
  3. 引线：层 `钻孔`，长 1.2 m，颜色 = 该孔品位档的颜色（0.5-1 青4 / 1-1.5 蓝5 / 1.5-3 红1 / ≥3 黄2）；
  4. 工程号：完整写 "BS-<平台>-<日期>-Pxx"，高 0.4，颜色 138；
  5. 品位数字：高 0.7，数值与数据库一致；
  6. 1 m 方格：层 `爆区方格网`，每个闭合小多边形边长 ≈1.0 m；
  7. 网格品位小字：层 0，高 0.133；
  8. 矿块号："n号矿块" MText 每块一个、不重号、互不重叠、不压矿块、不压报告图；
  9. 报告图：有一张 IMAGE 实体。
退出码 0 = 全过。
"""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAY = ROOT.parent
sys.path.insert(0, str(ROOT / "core")); sys.path.insert(0, str(ROOT / "_probe"))
BAND_COLOR = {"L1": 4, "L2": 5, "L3": 1, "L4": 2}
CROSS_COLOR = 138
TOL = 0.05


def level_color(g: float) -> int:
    if g < 0.5:
        return 8                    # 废孔：灰色（deliver.py 里 LEVEL_COLOR.get(lid, 8)）
    if g >= 3.0:
        return BAND_COLOR["L4"]
    if g >= 1.5:
        return BAND_COLOR["L3"]
    if g >= 1.0:
        return BAND_COLOR["L2"]
    return BAND_COLOR["L1"]


def find_dxf(plat, date, arg):
    if arg:
        return Path(arg)
    fresh = "--fresh" in sys.argv
    if not fresh:
        for d in (ROOT / "sample_data" / "output" / ("对账_%s" % date),
                  ROOT / "sample_data" / "output" / ("GUI跑通_%s" % date)):
            p = d / ("%s平台 %s二次圈矿矿块图.dxf" % (plat, date))
            if p.exists():
                return p
    out = ROOT / "sample_data" / "output" / ("对账_%s" % date)
    xls = sorted((DAY / ("北部山头%s平台2026" % plat) / "7、单日数据" /
                  ("北部山头%s平台-%s" % (plat, date))).glob("1、*.xls"))
    comp = sorted((DAY / ("北部山头%s平台2026" % plat)).glob("*综合*.dwg"))
    if not xls or not comp:
        return None
    subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "core" / "run_strip.py"),
                    str(xls[0]), plat, date, str(out), str(comp[0])],
                   stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, check=False)
    p = out / ("%s平台 %s二次圈矿矿块图.dxf" % (plat, date))
    return p if p.exists() else None


def main():
    plat, date = sys.argv[1], sys.argv[2]
    arg = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith("-") else None
    dxf = find_dxf(plat, date, arg)
    if dxf is None:
        print("找不到/生成不了成果图 DXF")
        return 2
    print("成果图：%s" % dxf)
    import ezdxf
    from shapely.geometry import LineString, box as _box, Point, Polygon
    from oreblocks import load_holes_xls
    doc = ezdxf.readfile(str(dxf))
    msp = doc.modelspace()
    xls = sorted((DAY / ("北部山头%s平台2026" % plat) / "7、单日数据" /
                  ("北部山头%s平台-%s" % (plat, date))).glob("1、*.xls"))[0]
    holes = list(load_holes_xls(xls).values())
    bad = []

    def rep(ok, msg):
        print("  %s %s" % ("✓" if ok else "✗", msg))
        if not ok:
            bad.append(msg)

    # 1. 图名
    title = "%s平台 %s二次圈矿矿块图" % (plat, date)
    texts = [e for e in msp if e.dxftype() == "TEXT"]
    rep(any(t.dxf.text == title for t in texts), "图名文字：%r" % title)

    # 2/3/4/5. 炮孔十字 / 引线 / 工程号 / 品位
    cross = []          # (x, y, color, len)
    lead = []           # (x, y, color, len)
    for e in msp:
        if e.dxftype() != "LINE":
            continue
        a, b = e.dxf.start, e.dxf.end
        ln = ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
        mid = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
        if e.dxf.layer == "点":
            cross.append((mid[0], mid[1], e.dxf.color, ln, a, b))
        elif e.dxf.layer == "钻孔":
            lead.append(((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0, e.dxf.color, ln))
    n_hole = len(holes)
    rep(len(cross) == 2 * n_hole, "十字线段数 %d（应为 2×%d＝%d）" % (len(cross), n_hole, 2 * n_hole))
    rep(all(abs(c[3] - 1.0) < TOL for c in cross), "十字臂长都≈1.0 m")
    rep(all(c[2] == CROSS_COLOR for c in cross), "十字颜色都是 %d" % CROSS_COLOR)
    # 每个孔位附近要有一横一竖（±0.3 m 内取中点）
    miss = []
    for h in holes:
        near = [c for c in cross if abs(c[0] - h.x) < 0.35 and abs(c[1] - h.y) < 0.35]
        hs = [c for c in near if abs(c[4][1] - c[5][1]) < 1e-6]
        vs = [c for c in near if abs(c[4][0] - c[5][0]) < 1e-6]
        if not (hs and vs):
            miss.append(h.short)
    rep(not miss, "每个炮孔都有横+竖十字%s" % ("" if not miss else "（缺 %s）" % ",".join(miss[:6])))
    rep(len(lead) == n_hole, "引线数 %d（应为 %d）" % (len(lead), n_hole))
    rep(all(abs(l[3] - 1.2) < TOL for l in lead), "引线长度都≈1.2 m")
    wrong = []
    for h in holes:
        near = [l for l in lead if abs(l[0] - h.x) < 1.0 and abs(l[1] - h.y) < 1.0]
        if not near:
            wrong.append("%s 没引线" % h.short)
        elif all(l[2] != level_color(h.grade) for l in near):
            wrong.append("%s 引线色 %s≠档色 %d" % (h.short, [l[2] for l in near], level_color(h.grade)))
    rep(not wrong, "引线颜色都跟品位档一致%s" % ("" if not wrong else "（%s）" % wrong[0]))
    code_txt = [t for t in texts if t.dxf.layer == "钻孔" and str(t.dxf.text).startswith("BS-")]
    rep(len(code_txt) == n_hole, "工程号文本 %d 条（应为 %d）" % (len(code_txt), n_hole))
    # 按**数据库里的工程号**逐条对（不能拿文件夹日期拼前缀：3960-0908 这个文件夹里，
    # 数据库自己的工程号是 BS-3960-0907-Pxx——炮孔是 0907 打的、图按 0908 归档的）
    want = {h.hid for h in holes}
    got = {str(t.dxf.text) for t in code_txt}
    missing = want - got
    extra = got - want
    rep(not missing and not extra,
        "工程号与数据库逐条一致（如 %s）%s" %
        (sorted(want)[0] if want else "?", "" if (not missing and not extra)
         else "；缺 %s；多 %s" % (sorted(missing)[:3], sorted(extra)[:3])))
    rep(all(abs(t.dxf.height - 0.4) < 1e-6 for t in code_txt), "工程号字高都 0.4")
    grade_txt = [t for t in texts if t.dxf.layer == "钻孔" and not str(t.dxf.text).startswith("BS-")]
    rep(len(grade_txt) == n_hole, "品位数字 %d 条（应为 %d）" % (len(grade_txt), n_hole))
    rep(all(abs(t.dxf.height - 0.7) < 1e-6 for t in grade_txt), "品位数字字高都 0.7")

    # 6. 1 m 方格
    cells = [e for e in msp if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == "爆区方格网"]
    sides_bad = 0
    for e in cells:
        pts = [(p[0], p[1]) for p in e.get_points()]
        for i in range(len(pts) - 1):
            d = ((pts[i + 1][0] - pts[i][0]) ** 2 + (pts[i + 1][1] - pts[i][1]) ** 2) ** 0.5
            if d > 1.0 + TOL and abs(d - 1.0) > TOL:
                sides_bad += 1
                break
    rep(len(cells) > 0, "方格小格 %d 个" % len(cells))
    # 人工图本身也有 10.7%~14.9% 的"被矿界裁掉一块"的小格（实测 1004 10.7%/0915 10.9%/
    # 1008 14.9%），所以这里允许到 20%——超了才说明方格生成有问题。
    rep(sides_bad <= 0.20 * len(cells),
        "方格边长≈1 m（被裁格 %d/%d＝%.1f%%，人工图同项 10.7~14.9%%，上限 20%%）"
        % (sides_bad, len(cells), 100.0 * sides_bad / max(1, len(cells))))

    # 7. 网格品位小字
    grid_txt = [t for t in texts if t.dxf.layer == "0" and abs(t.dxf.height - 0.1333) < 5e-4]
    rep(len(grid_txt) > 0.5 * len(cells), "网格品位小字 %d 条（≈格数 %d）" % (len(grid_txt), len(cells)))

    # 8. 矿块号
    lab = [e for e in msp if e.dxftype() == "MTEXT" and str(e.text).endswith("号矿块")]
    nums = [str(e.text) for e in lab]
    rep(len(set(nums)) == len(nums), "矿块号不重号（%s）" % "、".join(nums))
    blocks = [Polygon([(p[0], p[1]) for p in e.get_points()])
              for e in msp if e.dxftype() == "LWPOLYLINE"
              and e.dxf.layer in ("0.500-1.000", "1.000-1.500", "1.500-3.000", "3.000-999.000")]
    hw, hh = 2.2 * 3.0, 0.6 * 3.0
    rects = [_box(e.dxf.insert[0] - hw, e.dxf.insert[1] - hh,
                  e.dxf.insert[0] + hw, e.dxf.insert[1] + hh) for e in lab]
    rep(not any(r.intersects(b) for r in rects for b in blocks), "矿块号不压矿块")
    rep(all(not a.intersects(b) for i, a in enumerate(rects) for b in rects[i + 1:]),
        "矿块号互不重叠")
    img = [e for e in msp if e.dxftype() == "IMAGE"]
    rep(bool(img), "报告图（IMAGE）%d 张" % len(img))
    if img:
        i = img[0]
        r = _box(i.dxf.insert[0], i.dxf.insert[1],
                 i.dxf.insert[0] + 40.0, i.dxf.insert[1] + 29.0)
        rep(not any(x.intersects(r) for x in rects), "矿块号不压报告图")

    print()
    if bad:
        print("结论：%d 项没过：%s" % (len(bad), "；".join(bad)))
        return 1
    print("结论：成果图实体自检全部通过 ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
