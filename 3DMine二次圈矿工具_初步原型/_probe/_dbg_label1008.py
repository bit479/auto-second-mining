# -*- coding: utf-8 -*-
"""看 1008 的矿块号放置：走了哪条分支、和哪个矿块压了多少。"""
import sys, json, math
from pathlib import Path
ROOT = Path(".").resolve()
sys.path.insert(0, str(ROOT/"core")); sys.path.insert(0, str(ROOT/"_probe"))
from shapely.geometry import Polygon, box
from oreblocks import load_holes_xls
from pipeline import run_blast
from composite import load_composite_blocks
import params as _params
DAY = ROOT.parent/"北部山头3940平台2026"
folder=[d for d in (DAY/"7、单日数据").iterdir() if d.is_dir() and d.name.endswith("1008")][0]
holes=load_holes_xls(sorted(folder.glob("1、*.xls"))[0]); allh=list(holes.values())
comp=load_composite_blocks(DAY/"5、 北部山头3940平台二次圈矿矿块图-2026综合.dwg")
res=run_blast(holes, allh, _params.for_blast("1008",platform="3940"), comp, blast="1008")
blocks=[b for b in res["blocks"] if b.polygon is not None]
allpts=[pt for b in blocks for pt in b.polygon.convex_hull.exterior.coords]
gcx=sum(p[0] for p in allpts)/len(allpts); gcy=sum(p[1] for p in allpts)/len(allpts)
hw, hh = 2.2*3.0, 0.6*3.0
print("矿块 %d 个；组质心 (%.1f, %.1f)" % (len(blocks), gcx, gcy))
for b in blocks:
    cen=b.polygon.representative_point()
    dx,dy=cen.x-gcx, cen.y-gcy
    L=math.hypot(dx,dy); ux,uy=dx/L,dy/L
    d=math.sqrt(b.polygon.area)*0.9+8.0
    tx,ty=cen.x+ux*d, cen.y+uy*d
    r=box(tx-hw,ty-hh,tx+hw,ty+hh)
    hits=[bb.no for bb in blocks if bb.polygon.intersects(r)]
    print("  %d号矿块 cen(%.1f,%.1f) 方向(%.2f,%.2f) 放(%.1f,%.1f) 框内压到矿块 %s" % (b.no,cen.x,cen.y,ux,uy,tx,ty,hits))
