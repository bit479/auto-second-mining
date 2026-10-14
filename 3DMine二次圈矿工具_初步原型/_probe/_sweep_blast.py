# -*- coding: utf-8 -*-
"""对某个 3960 炮区扫"模式×外推"，看哪种最贴人工图。用法: python _sweep_blast.py <平台> <日期>"""
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
plat, date = sys.argv[1], sys.argv[2]
pdir=ROOT.parent/("北部山头%s平台2026" % plat)
folder=[d for d in (pdir/"7、单日数据").iterdir() if d.is_dir() and d.name.endswith(date)][0]
holes=load_holes_xls(sorted(folder.glob("1、*.xls"))[0]); allh=list(holes.values())
comp=load_composite_blocks(sorted(pdir.glob("*综合*.dwg"))[0])
j=json.loads(_bl.scan_path(plat,date).read_text(encoding="utf-8"))
mb=[Polygon(p["pts"]).buffer(0) for p in j["polylines"] if p["layer"] not in {"爆区方格网","钻孔","点","线条","孔口文字"} and len(p["pts"])>=3 and _bl.is_block(Polygon(p["pts"]).buffer(0),p["layer"],allh)]
man=unary_union(mb)
ore=[h for h in allh if h.grade>=0.5]
mv,src=_bl.volume_for_gate(plat,date,man,ore)
print("人工 %d 块 / 面积 %.1f / 基准体积 %.1f (%s)" % (len(mb), man.area, mv, src))
base=_params.for_blast(date,platform=plat)
for mode in ("clusters","chain"):
    for strip in (None,"hull"):
        row=[]
        for ex in (2,3,4,5,6,7):
            P=dict(base); P["ring_mode"]=mode; P["extrude_m"]=float(ex)
            P.pop("cluster_strip_mode",None)
            if strip: P["cluster_strip_mode"]=strip
            res=run_blast(holes, allh, P, comp, blast=date)
            if not res["rings"]: row.append("ex%.0f:-"%ex); continue
            ring=res["rings"][0]
            for rr in res["rings"][1:]: ring=ring.union(rr)
            iou=ring.intersection(man).area/ring.union(man).area
            tv=sum(b.volume_m3 for b in res["blocks"])
            row.append("ex%.0f:%.3f/%+.0f%%/%d块" % (ex,iou,100*(tv-mv)/mv if mv else 0,len(res["blocks"])))
        print("  %-8s %-5s %s" % (mode, strip or "-", "  ".join(row)))
