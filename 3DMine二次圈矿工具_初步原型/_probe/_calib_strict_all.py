# -*- coding: utf-8 -*-
"""严格档（排掉当日本身块）下批量标定：每个炮区给"块数一致 + |体积差|最小 + IoU 最大"的建议。
不写参数，只打印。用法: python _calib_strict_all.py <平台>
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
plat = sys.argv[1]
pdir=ROOT.parent/("北部山头%s平台2026" % plat)
comp_all=load_composite_blocks(sorted(pdir.glob("*综合*.dwg"))[0])
for folder in sorted(d for d in (pdir/"7、单日数据").iterdir() if d.is_dir()):
    xls=sorted(folder.glob("1、*.xls"))
    if not xls: continue
    from run_batch import parse_folder
    date=parse_folder(folder.name)[1] or folder.name.split("-")[-1].strip()
    jf=_bl.scan_path(plat,date)
    if not jf.exists(): continue
    holes=load_holes_xls(xls[0]); allh=list(holes.values()); ore=[h for h in allh if h.grade>=0.5]
    j=json.loads(jf.read_text(encoding="utf-8"))
    mb=[Polygon(p["pts"]).buffer(0) for p in j["polylines"] if p["layer"] not in {"爆区方格网","钻孔","点","线条","孔口文字"} and len(p["pts"])>=3 and _bl.is_block(Polygon(p["pts"]).buffer(0),p["layer"],allh)]
    man=unary_union(mb)
    comp=[c for c in comp_all if all(c[2].intersection(m).area/c[2].union(m).area<0.9 for m in mb)]
    mv,_=_bl.volume_for_gate(plat,date,man,ore)
    base=_params.for_blast(date,platform=plat)
    rows=[]
    for mode in ("clusters","chain"):
        for strip in (None,"hull"):
            for ex in (1.5,2.0,2.5,3.0,3.5,4.0,4.5,5.0,6.0):
                for seam in (0.0,0.5):
                    P=dict(base); P["ring_mode"]=mode; P["extrude_m"]=float(ex); P["seam_join_m"]=seam
                    P.pop("cluster_strip_mode",None)
                    if strip: P["cluster_strip_mode"]=strip
                    try: res=run_blast(holes, allh, P, comp, blast=date)
                    except Exception: continue
                    if not res["rings"] or not res["blocks"]: continue
                    rg=res["rings"][0]
                    for rr in res["rings"][1:]: rg=rg.union(rr)
                    tv=sum(b.volume_m3 for b in res["blocks"])
                    iou=rg.intersection(man).area/rg.union(man).area
                    rows.append((abs(len(res["blocks"])-len(mb)), abs(tv-mv)/mv, -iou, mode, strip, ex, seam, len(res["blocks"]), tv, iou))
    rows.sort(key=lambda r:(r[0], r[1], r[2]))
    cur_mode = base.get("ring_mode","chain"); cur_ex=float(base.get("extrude_m",3.0)); cur_seam=float(base.get("seam_join_m") or 0)
    cur=[r for r in rows if r[3]==cur_mode and abs(r[5]-cur_ex)<1e-9 and abs(r[6]-cur_seam)<1e-9]
    print("--- %s-%s 人工 %d 块 %.1f m² 基准 %.1f" % (plat,date,len(mb),man.area,mv))
    if cur:
        r=cur[0]; print("     当前: %s ex%.1f seam%.1f -> %d块 %+.1f%% IoU %.3f" % (r[3],r[5],r[6],r[7],100*(r[8]-mv)/mv,r[9]))
    for r in rows[:3]:
        print("     建议: %s%s ex%.1f seam%.1f -> %d块 %+.1f%% IoU %.3f" % (r[3], ("+hull" if r[4]=="hull" else ""), r[5], r[6], r[7], 100*(r[8]-mv)/mv, r[9]))
