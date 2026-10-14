# -*- coding: utf-8 -*-
"""实验：矿界与综合图边界"贴合对齐"的几种做法对比。

(a) 吸收窄边：ring ∪ (历史块 ∩ ring.buffer(gap))
(b) 只吸收"在矿界外侧"的窄边（同上，但只取 block.difference(ring)）
(c) 整块并入（对照，已知很差）
只对"离矿界 ≤ gap"的历史块做。
"""
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
DAY = ROOT.parent
PLAT={"3940":DAY/"北部山头3940平台2026","3960":DAY/"北部山头3960平台2026"}
for plat,pdir in PLAT.items():
    comp=load_composite_blocks(sorted(pdir.glob("*综合*.dwg"))[0])
    for folder in sorted(d for d in (pdir/"7、单日数据").iterdir() if d.is_dir()):
        xls=sorted(folder.glob("1、*.xls"))
        if not xls: continue
        date=folder.name.split("-")[-1].strip()
        jf=_bl.scan_path(plat,date)
        if not jf.exists(): continue
        holes=load_holes_xls(xls[0]); allh=list(holes.values()); ore=[h for h in allh if h.grade>=0.5]
        j=json.loads(jf.read_text(encoding="utf-8"))
        mb=[Polygon(p["pts"]).buffer(0) for p in j["polylines"] if p["layer"] not in {"爆区方格网","钻孔","点","线条","孔口文字"} and len(p["pts"])>=3 and _bl.is_block(Polygon(p["pts"]).buffer(0),p["layer"],allh)]
        if not mb: continue
        man=unary_union(mb)
        res=run_blast(holes, allh, _params.for_blast(date,platform=plat), comp, blast=date)
        if not res["rings"]: continue
        ring=res["rings"][0]
        for rr in res["rings"][1:]: ring=ring.union(rr)
        mv,_=_bl.volume_for_gate(plat,date,man,ore)
        def ev(g):
            if False:
                g = max(g.geoms, key=lambda q: q.area)
            cells=_cells_within(ore,g)
            vol=sum(cells[h.hid].area*h.grade_lenght for h in ore if h.hid in cells)
            return (g.intersection(man).area/g.union(man).area, 100*(vol-mv)/mv if mv else 0, vol)
        base=ev(ring)
        line="%-11s 现状 iou=%.3f vol=%+.1f%%" % (plat+"-"+date, base[0], base[1])
        for gap in (2.0,3.0,4.5):
            sl=[]
            for c in comp:
                blk=c[2]
                if blk.distance(ring)>gap: continue
                part=blk.difference(ring).intersection(ring.buffer(gap, join_style="mitre"))
                if not part.is_empty: sl.append(part)
            if sl:
                g=_safe=unary_union([ring]+sl)
                if g.geom_type=="MultiPolygon":
                    g=g.buffer(0.6,join_style="mitre").buffer(-0.6,join_style="mitre")
                r=ev(g)
                if r: line+=" | 贴边%.1f: iou=%.3f vol=%+.1f%%" % (gap, r[0], r[1])
                else: line+=" | 贴边%.1f:碎" % gap
            else:
                line+=" | 贴边%.1f:无" % gap
        print(line)
