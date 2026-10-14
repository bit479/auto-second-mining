# -*- coding: utf-8 -*-
"""检验"人工块边界 = 矿孔与相邻无品位孔的中点(1/2 工程间距)"这条规则。
做法：把人工块边界按 0.5 m 采样，对每个采样点算 到最近矿孔 d_ore / 到最近无品位孔 d_waste，
再看 d_ore/d_waste 与 d_waste-d_ore 的分布。"""
import sys, json
from pathlib import Path
ROOT = Path(".").resolve()
sys.path.insert(0, str(ROOT/"core")); sys.path.insert(0, str(ROOT/"_probe"))
import numpy as np
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from oreblocks import load_holes_xls
import baseline as _bl
def analyse(plat, date):
    pdir=ROOT.parent/("北部山头%s平台2026" % plat)
    folder=[d for d in (pdir/"7、单日数据").iterdir() if d.is_dir() and d.name.endswith(date)][0]
    holes=load_holes_xls(sorted(folder.glob("1、*.xls"))[0]); allh=list(holes.values())
    ore=[(h.x,h.y) for h in allh if h.grade>=0.5]; waste=[(h.x,h.y) for h in allh if h.grade<0.5]
    j=json.loads(_bl.scan_path(plat,date).read_text(encoding="utf-8"))
    mb=[Polygon(p["pts"]).buffer(0) for p in j["polylines"] if p["layer"] not in {"爆区方格网","钻孔","点","线条","孔口文字"} and len(p["pts"])>=3 and _bl.is_block(Polygon(p["pts"]).buffer(0),p["layer"],allh)]
    man=unary_union(mb)
    pts=[]
    geoms=[man] if man.geom_type=="Polygon" else list(man.geoms)
    for g in geoms:
        L=g.exterior.length
        for t in np.arange(0, L, 0.5):
            p=g.exterior.interpolate(t); pts.append((p.x,p.y))
    d_ore=[]; d_was=[]; ratio=[]; diff=[]
    for x,y in pts:
        do=min(np.hypot(x-a,y-b) for a,b in ore)
        if not waste: break
        dw=min(np.hypot(x-a,y-b) for a,b in waste)
        if dw>12: continue
        d_ore.append(do); d_was.append(dw); ratio.append(do/dw if dw else 9); diff.append(do-dw)
    if not d_ore: print("  %s-%s 无可用采样" % (plat,date)); return
    d_ore=np.array(d_ore); d_was=np.array(d_was); ratio=np.array(ratio)
    print("  %s-%s 采样 %d 点（距最近无品位孔 ≤12m 的 %d 点）" % (plat,date,len(pts),len(d_ore)))
    print("     d_ore  中位 %.2f  均值 %.2f   [p25 %.2f p75 %.2f]" % (np.median(d_ore), d_ore.mean(), np.percentile(d_ore,25), np.percentile(d_ore,75)))
    print("     d_waste中位 %.2f  均值 %.2f" % (np.median(d_was), d_was.mean()))
    print("     d_ore-d_waste 中位 %+.2f  ；落在 |d_ore-d_waste|<=1.0 的比例 %.0f%%" % (np.median(d_ore-d_was), 100*np.mean(np.abs(d_ore-d_was)<=1.0)))
    print("     (即中点假设的成立比例)")
for plat,date in (("3960","1007"),("3960","0922"),("3960","0904"),("3960","0902"),("3940","1008"),("3940","0915"),("3960","1008"),("3960","0908")):
    try: analyse(plat,date)
    except Exception as e: print("  %s-%s 失败 %s" % (plat,date,e))
