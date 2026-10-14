# -*- coding: utf-8 -*-
"""看 3960 各炮区：自动矿界 vs 人工图 —— 面积比、形心偏移、IoU（判断是不是"整体偏移"型误差）。"""
import sys, json
from pathlib import Path
ROOT = Path(".").resolve()
sys.path.insert(0, str(ROOT/"core")); sys.path.insert(0, str(ROOT/"_probe"))
from shapely.geometry import Polygon
from shapely.ops import unary_union
from oreblocks import load_holes_xls
from pipeline import run_blast
from composite import load_composite_blocks
import params as _params, baseline as _bl
from run_batch import parse_folder
plat="3960"; pdir=ROOT.parent/"北部山头3960平台2026"
comp=load_composite_blocks(sorted(pdir.glob("*综合*.dwg"))[0])
print("%-11s %8s %8s %7s %8s %8s" % ("炮区","自动面积","人工面积","面积比","形心偏移m","IoU"))
for folder in sorted(d for d in (pdir/"7、单日数据").iterdir() if d.is_dir()):
    xls=sorted(folder.glob("1、*.xls"))
    if not xls: continue
    date=parse_folder(folder.name)[1]
    jf=_bl.scan_path(plat,date)
    if not jf.exists(): continue
    holes=load_holes_xls(xls[0]); allh=list(holes.values())
    j=json.loads(jf.read_text(encoding="utf-8"))
    mb=[Polygon(p["pts"]).buffer(0) for p in j["polylines"] if p["layer"] not in {"爆区方格网","钻孔","点","线条","孔口文字"} and len(p["pts"])>=3 and _bl.is_block(Polygon(p["pts"]).buffer(0),p["layer"],allh)]
    man=unary_union(mb)
    res=run_blast(holes, allh, _params.for_blast(date,platform=plat), comp, blast=date)
    if not res["rings"]: continue
    rg=res["rings"][0]
    for rr in res["rings"][1:]: rg=rg.union(rr)
    c1=rg.centroid; c2=man.centroid
    d=((c1.x-c2.x)**2+(c1.y-c2.y)**2)**0.5
    print("%-11s %8.1f %8.1f %7.2f %8.2f %8.3f" % (date, rg.area, man.area, rg.area/man.area, d, rg.intersection(man).area/rg.union(man).area))
