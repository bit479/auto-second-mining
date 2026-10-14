# -*- coding: utf-8 -*-
"""实验：把"真正贴上"（间距 <= 0.3/1.0 m）的综合图历史块并进矿界，看会不会更贴人工图。"""
import sys, json
from pathlib import Path
ROOT = Path(".").resolve()
sys.path.insert(0, str(ROOT/"core")); sys.path.insert(0, str(ROOT/"_probe"))
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from oreblocks import load_holes_xls
from pipeline import run_blast
from composite import load_composite_blocks
import params as _params, baseline as _bl
from strip import _cells_within
DAY = ROOT.parent/"北部山头3940平台2026"; plat="3940"
comp = load_composite_blocks(DAY/"5、 北部山头3940平台二次圈矿矿块图-2026综合.dwg")
for date in ("0915","0903","1003","1004","1008","0922"):
    folder=[d for d in (DAY/"7、单日数据").iterdir() if d.is_dir() and d.name.endswith(date)]
    if not folder: continue
    folder=folder[0]
    xls=sorted(folder.glob("1、*.xls"))
    if not xls: continue
    holes=load_holes_xls(xls[0]); allh=list(holes.values()); ore=[h for h in allh if h.grade>=0.5]
    if not _bl.scan_path(plat,date).exists(): continue
    j=json.loads(_bl.scan_path(plat,date).read_text(encoding="utf-8"))
    mb=[Polygon(p["pts"]).buffer(0) for p in j["polylines"] if p["layer"] not in {"爆区方格网","钻孔","点","线条","孔口文字"} and len(p["pts"])>=3 and _bl.is_block(Polygon(p["pts"]).buffer(0),p["layer"],allh)]
    man=unary_union(mb); rep=_bl.manual_volume(plat,date)
    res=run_blast(holes, allh, _params.for_blast(date,platform=plat), comp, blast=date)
    ring=res["rings"][0]
    for rr in res["rings"][1:]: ring=ring.union(rr)
    tv=sum(b.volume_m3 for b in res["blocks"])
    line="%s 现状: iou=%.3f vol=%+.1f%%" % (date, ring.intersection(man).area/ring.union(man).area, 100*(tv-rep)/rep)
    for gap in (0.3,1.0,2.0):
        grp=[ring]+[c[2] for c in comp if ring.distance(c[2])<=gap]
        if len(grp)==1: line+=" | g%.1f:无" % gap; continue
        m=unary_union(grp)
        if m.geom_type=="MultiPolygon":
            d=0.6; m=m.buffer(d,join_style="mitre").buffer(-d,join_style="mitre")
        iou=m.intersection(man).area/m.union(man).area
        cells=_cells_within(ore,m); vol=sum(cells[h.hid].area*h.grade_lenght for h in ore if h.hid in cells)
        line+=" | g%.1f:n=%d iou=%.3f vol=%+.1f%%" % (gap,len(grp)-1,iou,100*(vol-rep)/rep)
    print(line)
