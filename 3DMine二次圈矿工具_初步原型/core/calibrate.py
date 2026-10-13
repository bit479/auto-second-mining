# -*- coding: utf-8 -*-
"""一键标定：把人工圈矿图读进来，自动标出该炮区的"外推距离 + 左右链"。

用法:
  python calibrate.py <炮区号> <人工圈矿图.dwg> [--platform 3940]
                      [--extrude 3 4 5] [--write] [--by-volume]

  --extrude  要联搜的外推距离(m)，不填就只用当前参数里的值
  --write    把标定结果写进 圈矿参数.json（不填只打印建议）

步骤：
  ① 只读扫描人工 DWG（AutoCAD COM，带重试）→ _probe/manual_<炮区>_c.json
  ② 以"矿界 vs 人工块并集 的 IoU"为目标，贪心搜"哪些孔该进左/右链"
  ③ （--write 时）把结果合并进 圈矿参数.json 的 platforms.<炮区>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))
sys.path.insert(0, str(ROOT / "_probe"))

from shapely.geometry import Polygon                             # noqa: E402
from shapely.ops import unary_union                             # noqa: E402

from oreblocks import load_holes_xls                            # noqa: E402
from pipeline import pick_zone, run_blast                       # noqa: E402
from strip import zone_chains                                   # noqa: E402
from composite import load_composite_blocks                     # noqa: E402
import params as _params                                        # noqa: E402

PROBE = ROOT / "_probe"
PLATFORM_DIRS = {"3940": ROOT.parent / "北部山头3940平台2026",
                 "3960": ROOT.parent / "北部山头3960平台2026"}
SKIP = {"爆区方格网", "钻孔", "点", "线条", "孔口文字"}
def manual_volume(platform: str, date: str, man_poly=None, ore=None):
    """基准体积（用来算体积差；没基准的炮区就不做体积优选）。

    走 `_probe/baseline.volume_for_gate`：报告与"图面积×平均孔长"对不上时用图推算。
    """
    try:
        import baseline as _bl
        if man_poly is not None:
            return _bl.volume_for_gate(platform, date, man_poly, ore)[0]
        return _bl.manual_volume(platform, date)
    except Exception:
        return None


def _bl_vol(platform: str, date: str, man_poly, ore):
    """(基准体积, 来源) —— 报告与图对不上时按图推算（见 _probe/baseline.py）。"""
    try:
        import baseline as _bl
        return _bl.volume_for_gate(platform, date, man_poly, ore)
    except Exception:
        return None, ""


def scan_manual(dwg: Path, out_json: Path, tries: int = 5) -> bool:
    """只读扫描人工 DWG（复用 _probe 里的带重试实现）。"""
    import subprocess
    script = PROBE / "scan_manual_retry.py"
    if not script.exists():
        print("缺少 %s，无法扫描" % script)
        return False
    r = subprocess.run([sys.executable, "-X", "utf8", str(script), str(dwg),
                        str(out_json), str(tries)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    print((r.stdout or "").strip()[-400:])
    return out_json.exists()


def manual_union(json_path: Path):
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    polys = []
    for p in data.get("polylines", []):
        if p.get("layer") in SKIP or len(p.get("pts", [])) < 3:
            continue
        poly = Polygon(p["pts"]).buffer(0)
        if poly.area >= 5.0:
            polys.append(poly)
    return unary_union(polys) if polys else None


def manual_block_count(json_path: Path) -> int:
    """人工图里有几个块（面积 ≥5 m² 的折线数）——用来约束"自动块的个数要对得上"。"""
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    n = 0
    for p in data.get("polylines", []):
        if p.get("layer") in SKIP or len(p.get("pts", [])) < 3:
            continue
        if Polygon(p["pts"]).buffer(0).area >= 5.0:
            n += 1
    return n


def iou(a, b):
    if a is None or b is None or a.is_empty or b.is_empty:
        return 0.0
    return a.intersection(b).area / a.union(b).area


def evaluate(holes, allh, P, comp, date, ml, mr):
    P2 = dict(P)
    P2["chain_left"], P2["chain_right"] = list(ml), list(mr)
    res = run_blast(holes, allh, P2, comp, blast=date)
    if not res["rings"]:
        return None, [], 0.0
    ring = res["rings"][0]
    for rr in res["rings"][1:]:
        ring = ring.union(rr)
    tv = sum(b.volume_m3 for b in res["blocks"])
    return ring, res["blocks"], tv


def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__)
        return
    date, dwg = sys.argv[1], Path(sys.argv[2])
    platform = "3940"
    if "--platform" in sys.argv:
        platform = sys.argv[sys.argv.index("--platform") + 1]
    grid = None
    if "--extrude" in sys.argv:
        i = sys.argv.index("--extrude")
        grid = [float(x) for x in sys.argv[i + 1:] if not x.startswith("-")]
    write = "--write" in sys.argv
    by_volume = "--by-volume" in sys.argv

    # 找该炮区的数据库与综合图（同目录/上级目录里带"综合"的 dwg）
    day = PLATFORM_DIRS.get(platform)
    data_dir = (day / "7、单日数据") if day else dwg.parent
    folder = data_dir / ("北部山头%s平台-%s" % (platform, date))
    if not folder.exists():
        cands = [d for d in data_dir.glob("*-%s" % date)]
        folder = cands[0] if cands else dwg.parent
    xls = sorted(folder.glob("1、*.xls"))
    if not xls:
        print("在 %s 里找不到炮孔数据库" % folder)
        return
    comp_dwg = None
    for c in list(folder.glob("*综合*.dwg")) + list(folder.parent.glob("*综合*.dwg")) + \
            list(day.glob("*综合*.dwg") if day else []):
        comp_dwg = c
        break
    comp = load_composite_blocks(comp_dwg) if comp_dwg else []
    print("数据库：%s" % xls[0].name)
    print("综合图：%s" % (comp_dwg.name if comp_dwg else "（无）"))

    scan_json = PROBE / ("manual_%s-%s_c.json" % (platform, date))
    if not scan_json.exists() or "--rescan" in sys.argv:
        if not scan_manual(dwg, scan_json):
            print("扫描失败")
            return
    man = manual_union(scan_json)
    if man is None:
        print("人工图里没读到块轮廓")
        return

    holes = load_holes_xls(xls[0])
    allh = list(holes.values())
    P0 = _params.for_blast(date, platform=platform)
    ore, _ = pick_zone(holes, adjacent_max=P0["zone_link_m"])
    cands = []
    for ex in (grid or [P0["extrude_m"]]):
        P = dict(P0)
        P["extrude_m"] = float(ex)
        ml, mr = list(P0.get("chain_left") or []), list(P0.get("chain_right") or [])
        ring, blocks, tv = evaluate(holes, allh, P, comp, date, ml, mr)
        if ring is None:
            continue
        sc = iou(ring, man)
        left, right, _, _, _ = zone_chains(ore, allh, manual_left=ml, manual_right=mr)
        inchain = set(ore[j].short for j in left) | set(ore[j].short for j in right)
        cand = [h.short for h in ore if h.short not in inchain]
        moved = True
        while moved and cand:
            moved = False
            for name in list(cand):
                for tl, tr in ((ml + [name], mr), (ml, mr + [name])):
                    r2, _, _ = evaluate(holes, allh, P, comp, date, tl, tr)
                    s2 = iou(r2, man)
                    if s2 > sc + 1e-4:
                        sc, ml, mr, moved = s2, tl, tr, True
                if name in ml or name in mr:
                    cand.remove(name)
        ring, blocks, tv = evaluate(holes, allh, P, comp, date, ml, mr)
        print("  外推 %4.1f m → IoU %.3f  体积 %9.1f  %d 块"
              % (ex, sc, tv, len(blocks)))
        cands.append((sc, float(ex), ml, mr, tv, len(blocks)))
    if not cands:
        print("没算出来")
        return
    mv, _src = (None, "") if man is None else _bl_vol(platform, date, man, ore)
    if by_volume and mv:
        # 先按"块数要与人工图一致 + IoU 在最佳附近"筛，再取体积差最小的
        n_man = manual_block_count(scan_json)
        top = max(c[0] for c in cands)
        pool = [c for c in cands if c[0] >= top - 0.02 and c[5] == n_man]
        if not pool:
            pool = [c for c in cands if c[0] >= top - 0.02] or cands
        best = min(pool, key=lambda c: abs(c[4] - mv))
    else:
        best = max(cands, key=lambda c: c[0])
    sc, ex, ml, mr, tv, nb = best
    dev = (tv - mv) / mv * 100 if mv else 0.0
    print("\n最佳：外推 %.1f m  IoU %.3f  体积 %.1f (%+.1f%%)  %d 块"
          % (ex, sc, tv, dev, nb))
    print("  chain_left  = %s" % json.dumps(ml, ensure_ascii=False))
    print("  chain_right = %s" % json.dumps(mr, ensure_ascii=False))
    if write:
        cfg = _params.load()
        key = "%s-%s" % (platform, date)      # 带平台号，避免 3940/3960 同一天撞车
        pl = cfg.setdefault("blasts", {}).setdefault(key, {})
        pl["extrude_m"] = ex
        pl["chain_left"], pl["chain_right"] = ml, mr
        pl["_说明"] = "由 calibrate.py 自动标定（平台 %s，炮区 %s）" % (platform, date)
        path = _params.save(cfg)
        print("已写入：", path)
    else:
        print("（加 --write 可写进 圈矿参数.json）")


if __name__ == "__main__":
    main()
