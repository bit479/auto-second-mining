# -*- coding: utf-8 -*-
"""实验：矿界与综合图边界"贴上的部分"对齐——只吸收"离矿界 <= snap 且在外侧"的那条窄边，
不整块吞历史矿块。"""
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
        tv=sum(b.volume_m3 for b in res["blocks"])
        line="%-11s 现状 iou=%.3f vol=%+.1f%%" % (plat+"-"+date, ring.intersection(man).area/ring.union(man).area, 100*(tv-mv)/mv if mv else 0)
        for snap in (1.5,2.5,4.0):
            slivers=[]
            for c in comp:
                blk=c[2]
                d=blk.distance(ring)
                if d>snap: continue
                sl=blk.intersection(ring.buffer(snap, join_style="mitre"))
                if not sl.is_empty: slivers.append(sl)
            if not slivers: line+=" | s%.1f:无" % snap; continue
            m=unary_union([ring]+slivers)
            if m.geom_type=="MultiPolygon":
                m=m.buffer(0.6,join_style="mitre").buffer(-0.6,join_style="mitre")
            if m.geom_type!="Polygon": line+=" | s%.1f:碎" % snap; continue
            cells=_cells_within(ore,m); vol=sum(cells[h.hid].area*h.grade_lenght for h in ore if h.hid in cells)
            line+=" | s%.1f iou=%.3f vol=%+.1f%%(外孔%d)" % (snap, m.intersection(man).area/m.union(man).area, 100*(vol-mv)/mv if mv else 0, len([h for h in ore if not m.contains(Point(h.x,h.y))]))
        print(line)
