# -*- coding: utf-8 -*-
"""细扫外推（严格档，0.1 m 步长）：找体积最贴人工图的那个外推距离。

用法: python _sweep_fine.py <平台> <炮区> [起始x10=15] [结束x10=41]
例：  python _sweep_fine.py 3960 0902 15 41
"""
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
plat = sys.argv[1] if len(sys.argv) > 1 else "3960"
date = sys.argv[2] if len(sys.argv) > 2 else "0902"
pdir=ROOT.parent/("北部山头%s平台2026" % plat)
folder=_bl.blast_dir(plat, date)
holes=load_holes_xls(sorted(folder.glob("1、*.xls"))[0]); allh=list(holes.values()); ore=[h for h in allh if h.grade>=0.5]
comp_all=load_composite_blocks(sorted(pdir.glob("*综合*.dwg"))[0])
j=json.loads(_bl.scan_path(plat,date).read_text(encoding="utf-8"))
mb=[Polygon(p["pts"]).buffer(0) for p in j["polylines"] if p["layer"] not in {"爆区方格网","钻孔","点","线条","孔口文字"} and len(p["pts"])>=3 and _bl.is_block(Polygon(p["pts"]).buffer(0),p["layer"],allh)]
man=unary_union(mb)
comp=[c for c in comp_all if all(c[2].intersection(m).area/c[2].union(m).area<0.9 for m in mb)]
mv,_=_bl.volume_for_gate(plat,date,man,ore)
base=_params.for_blast(date,platform=plat)
print("人工块 %.1f m²  基准体积 %.1f  孔数 %d（矿孔 %d）" % (man.area, mv, len(allh), len(ore)))
print("%-6s %-5s %-6s %8s %8s %8s" % ("模式","hull","外推","块数","体积差","IoU"))
rows=[]
for mode in ("clusters","chain"):
    for strip in (None,"hull"):
        for ex10 in range(int(sys.argv[3]) if len(sys.argv) > 3 else 15, int(sys.argv[4]) if len(sys.argv) > 4 else 41):
            ex = ex10/10.0
            P=dict(base); P["ring_mode"]=mode; P["extrude_m"]=ex; P["seam_join_m"]=0.0
            P.pop("cluster_strip_mode",None)
            if strip: P["cluster_strip_mode"]=strip
            try: res=run_blast(holes, allh, P, comp, blast=date)
            except Exception: continue
            if not res["rings"] or not res["blocks"]: continue
            rg=res["rings"][0]
            for rr in res["rings"][1:]: rg=rg.union(rr)
            tv=sum(b.volume_m3 for b in res["blocks"])
            iou=rg.intersection(man).area/rg.union(man).area
            rows.append((abs(tv-mv)/mv, -iou, mode, strip or "-", ex, len(res["blocks"]), tv, iou))
rows.sort()
for r in rows[:12]:
    print("%-8s %-5s %-6.1f %8d %+7.1f%% %8.3f" % (r[2], r[3] or "-", r[4], r[5], 100*(r[6]-mv)/mv, r[7]))

