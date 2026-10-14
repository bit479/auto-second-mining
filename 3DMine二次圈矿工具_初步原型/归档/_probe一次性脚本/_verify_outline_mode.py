# -*- coding: utf-8 -*-
"""验证精确模式：用用户 Desktop 上的 1008 四段 .3ds 拼出矿界，与人工 1008 图对账。"""
import sys, json
from pathlib import Path
ROOT = Path(".").resolve()
sys.path.insert(0, str(ROOT/"core")); sys.path.insert(0, str(ROOT/"_probe"))
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from oreblocks import load_holes_xls
from pipeline import run_blast
from composite import load_composite_blocks
import params as _params, baseline as _bl, strip as S
D = Path(r"C:\Users\Administrator\Desktop")
parts = ["左边界，已外推3m.3ds", "与综合图边界.3ds", "右边界，已外推3m.3ds",
         "连接辅助线中点形成右上边界.3ds"]
ring = S.ring_from_outline_files([D/n for n in parts])
print("精确模式拼出的矿界：面积 %.3f m²" % ring.area)
DAY = ROOT.parent/"北部山头3940平台2026"
folder=[d for d in (DAY/"7、单日数据").iterdir() if d.is_dir() and d.name.endswith("1008")][0]
holes=load_holes_xls(sorted(folder.glob("1、*.xls"))[0]); allh=list(holes.values())
j=json.loads(_bl.scan_path("3940","1008").read_text(encoding="utf-8"))
mb=[Polygon(p["pts"]).buffer(0) for p in j["polylines"] if p["layer"] not in {"爆区方格网","钻孔","点","线条","孔口文字"} and len(p["pts"])>=3 and _bl.is_block(Polygon(p["pts"]).buffer(0),p["layer"],allh)]
man=unary_union(mb)
print("人工 1008 图 %.1f m²；与精确模式矿界 IoU %.4f" % (man.area, ring.intersection(man).area/ring.union(man).area))
comp=load_composite_blocks(DAY/"5、 北部山头3940平台二次圈矿矿块图-2026综合.dwg")
P=dict(_params.for_blast("1008",platform="3940")); P["outline_files"]=[str(D/n) for n in parts]
res=run_blast(holes, allh, P, comp, blast="1008")
print("走 pipeline 精确模式：块数 %d 体积 %.1f m³（人工报告 3951.49）" % (len(res["blocks"]), sum(b.volume_m3 for b in res["blocks"])))
for b in res["blocks"]:
    ins=[h.short.replace("BS-3940-1008-","") for h in allh if b.polygon.contains(Point(h.x,h.y))]
    print("   %s %-14s a=%7.1f vol=%8.1f g=%.4f 孔(%d) %s" % (b.no, b.level_id, b.polygon.area, b.volume_m3, b.grade, len(ins), ",".join(ins)))
