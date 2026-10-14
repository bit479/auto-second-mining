# -*- coding: utf-8 -*-
"""0915：与综合图"贴合对齐"前后对照（人工红 / 旧矿界灰虚 / 新矿界蓝）。"""
import sys, json
from pathlib import Path
ROOT = Path(".").resolve()
sys.path.insert(0, str(ROOT/"core")); sys.path.insert(0, str(ROOT/"_probe"))
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
matplotlib.rcParams["font.sans-serif"]=["Microsoft YaHei","SimHei"]; matplotlib.rcParams["axes.unicode_minus"]=False
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from oreblocks import load_holes_xls
from pipeline import run_blast
from composite import load_composite_blocks
import params as _params, baseline as _bl
DAY = ROOT.parent/"北部山头3940平台2026"; date="0915"
folder=[d for d in (DAY/"7、单日数据").iterdir() if d.is_dir() and d.name.endswith(date)][0]
holes=load_holes_xls(sorted(folder.glob("1、*.xls"))[0]); allh=list(holes.values())
comp=load_composite_blocks(DAY/"5、 北部山头3940平台二次圈矿矿块图-2026综合.dwg")
base=_params.for_blast(date,platform="3940")
def run(seam):
    P=dict(base); P["seam_join_m"]=seam
    r=run_blast(holes, allh, P, comp, blast=date)
    g=r["rings"][0]
    for rr in r["rings"][1:]: g=g.union(rr)
    return g, r, sum(b.volume_m3 for b in r["blocks"])
g0,r0,v0=run(0.0); g1,r1,v1=run(0.5)
j=json.loads(_bl.scan_path("3940",date).read_text(encoding="utf-8"))
man=unary_union([Polygon(p["pts"]).buffer(0) for p in j["polylines"] if p["layer"] not in {"爆区方格网","钻孔","点","线条","孔口文字"} and len(p["pts"])>=3 and _bl.is_block(Polygon(p["pts"]).buffer(0),p["layer"],allh)])
fig,ax=plt.subplots(figsize=(16,11))
for g in ([man] if man.geom_type=="Polygon" else list(man.geoms)):
    x,y=g.exterior.xy; ax.plot(x,y,color="#d62728",lw=2.2,label="人工图")
for g,col,ls,lab in ((g0,"#999999","--","旧（不贴合综合图）"),(g1,"#1f77b4","-","新（贴合综合图 ≤0.5 m）")):
    for gg in ([g] if g.geom_type=="Polygon" else list(g.geoms)):
        x,y=gg.exterior.xy; ax.plot(x,y,color=col,ls=ls,lw=1.8,label=lab)
for lay,col,poly in comp:
    x,y=poly.exterior.xy; ax.plot(x,y,color="#c8e6c9",lw=0.9)
for h in allh:
    ax.plot(h.x,h.y,"o",color=("orange" if h.grade>=0.5 else "black"),ms=5)
    ax.annotate(h.short.replace("BS-3940-0915-",""),(h.x,h.y),fontsize=7)
ax.set_aspect("equal"); ax.grid(alpha=.3)
h,l=ax.get_legend_handles_labels(); seen=set(); hh=[];ll=[]
for a,b in zip(h,l):
    if b in seen: continue
    seen.add(b); hh.append(a); ll.append(b)
ax.legend(hh,ll,fontsize=11,loc="upper left")
ax.set_title("3940-0915 与综合图贴合对齐前后：旧 IoU %.3f / %.1f m³（%+.1f%%）；新 IoU %.3f / %.1f m³（%+.1f%%）；块数 %d→%d（人工 7 块）"
             % (g0.intersection(man).area/g0.union(man).area, v0, 100*(v0-13497.316)/13497.316,
                g1.intersection(man).area/g1.union(man).area, v1, 100*(v1-13497.316)/13497.316,
                len(r0["blocks"]), len(r1["blocks"])))
fig.savefig(ROOT/"sample_data"/"output"/"审图_0915_贴合综合图.png",dpi=115,bbox_inches="tight"); print("ok")
