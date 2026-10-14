# -*- coding: utf-8 -*-
"""3960-0922-2 标定：簇内碎片合并阈值 cluster_merge_m2 × 外推 × 贴合（严格档）。"""
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
plat, date = "3960", "0922-2"
pdir=ROOT.parent/("北部山头%s平台2026" % plat)
folder=[d for d in (pdir/"7、单日数据").iterdir() if d.is_dir() and "0922 - 2" in d.name][0]
holes=load_holes_xls(sorted(folder.glob("1、*.xls"))[0]); allh=list(holes.values()); ore=[h for h in allh if h.grade>=0.5]
comp_all=load_composite_blocks(sorted(pdir.glob("*综合*.dwg"))[0])
j=json.loads(_bl.scan_path(plat,date).read_text(encoding="utf-8"))
mb=[Polygon(p["pts"]).buffer(0) for p in j["polylines"] if p["layer"] not in {"爆区方格网","钻孔","点","线条","孔口文字"} and len(p["pts"])>=3 and _bl.is_block(Polygon(p["pts"]).buffer(0),p["layer"],allh)]
man=unary_union(mb)
comp=[c for c in comp_all if all(c[2].intersection(m).area/c[2].union(m).area<0.9 for m in mb)]
mv,_=_bl.volume_for_gate(plat,date,man,ore)
base=_params.for_blast(date,platform=plat)
rows=[]
for mer in (0.0,10.0,20.0,30.0,40.0,60.0):
    for ex in (1.5,2.0,2.5,3.0,3.5,4.0):
        for seam in (0.0,0.5):
            P=dict(base); P["ring_mode"]="clusters"; P["cluster_merge_m2"]=mer
            P["extrude_m"]=float(ex); P["seam_join_m"]=seam
            try: res=run_blast(holes, allh, P, comp, blast=date)
            except Exception: continue
            if not res["rings"] or not res["blocks"]: continue
            rg=res["rings"][0]
            for rr in res["rings"][1:]: rg=rg.union(rr)
            tv=sum(b.volume_m3 for b in res["blocks"])
            iou=rg.intersection(man).area/rg.union(man).area
            rows.append((abs(len(res["blocks"])-4), abs(tv-mv)/mv, -iou, mer, ex, seam, len(res["blocks"]), tv, iou))
rows.sort(key=lambda r:(r[0],r[1],r[2]))
print("人工 4 块 %.1f m² 基准 %.1f" % (man.area, mv))
for r in rows[:12]:
    print("  合并阈值%.0f 外推%.1f 贴合%.1f -> %d块 %+.1f%% IoU %.3f" % (r[3],r[4],r[5],r[6],100*(r[7]-mv)/mv,r[8]))
