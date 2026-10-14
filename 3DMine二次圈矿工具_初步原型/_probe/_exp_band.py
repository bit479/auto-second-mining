# -*- coding: utf-8 -*-
"""实验：把"同一排"窗口去掉（band=∞）看 3940/3960 会怎样。"""
import sys, json
from pathlib import Path
ROOT = Path(".").resolve()
sys.path.insert(0, str(ROOT/"core")); sys.path.insert(0, str(ROOT/"_probe"))
from shapely.geometry import Polygon
from shapely.ops import unary_union
from oreblocks import load_holes_xls
import strip as S
DAY = ROOT.parent
PLAT={"3940":DAY/"北部山头3940平台2026","3960":DAY/"北部山头3960平台2026"}
import baseline as _bl, params as _params
from pipeline import run_blast
from composite import load_composite_blocks

def report(tag):
    print("=== %s ===" % tag)
    for plat, pdir in PLAT.items():
        comp=load_composite_blocks(sorted(pdir.glob("*综合*.dwg"))[0])
        for folder in sorted(d for d in (pdir/"7、单日数据").iterdir() if d.is_dir()):
            if not sorted(folder.glob("1、*.xls")): continue
            date=folder.name.split("-")[-1].strip()
            jf=_bl.scan_path(plat,date)
            if not jf.exists(): continue
            holes=load_holes_xls(sorted(folder.glob("1、*.xls"))[0]); allh=list(holes.values())
            j=json.loads(jf.read_text(encoding="utf-8"))
            mb=[Polygon(p["pts"]).buffer(0) for p in j["polylines"] if p["layer"] not in {"爆区方格网","钻孔","点","线条","孔口文字"} and len(p["pts"])>=3 and _bl.is_block(Polygon(p["pts"]).buffer(0),p["layer"],allh)]
            if not mb: continue
            man=unary_union(mb)
            P=_params.for_blast(date,platform=plat)
            res=run_blast(holes, allh, P, comp, blast=date)
            if not res["rings"]: print("  %s-%s 无矿界" % (plat,date)); continue
            ring=res["rings"][0]
            for rr in res["rings"][1:]: ring=ring.union(rr)
            iou=ring.intersection(man).area/ring.union(man).area
            tv=sum(b.volume_m3 for b in res["blocks"])
            mv,_=_bl.volume_for_gate(plat,date,man,res["ore"])
            print("  %-11s iou=%.3f 块=%d vol差=%+.1f%% 外孔=%d" % (plat+"-"+date, iou, len(res["blocks"]), 100*(tv-mv)/mv if mv else 0, len([h for h in res["ore"] if not ring.contains(__import__("shapely.geometry",fromlist=["Point"]).Point(h.x,h.y))])))

report("当前 band=0.9×孔距")
S.CHAIN_BAND_FACTOR = 50.0
report("实验 band=∞（不设范围）")
