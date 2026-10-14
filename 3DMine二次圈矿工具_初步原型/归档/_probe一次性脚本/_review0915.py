# -*- coding: utf-8 -*-
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
DAY = ROOT.parent/"北部山头3940平台2026"
folder = [d for d in (DAY/"7、单日数据").iterdir() if d.is_dir() and d.name.endswith("0915")][0]
holes = load_holes_xls(sorted(folder.glob("1、*.xls"))[0]); allh=list(holes.values())
comp = load_composite_blocks(DAY/"5、 北部山头3940平台二次圈矿矿块图-2026综合.dwg")
P = dict(_params.for_blast("0915", platform="3940"))
old = dict(P); old["end_pair_beyond"] = False
res_new = run_blast(holes, allh, P, comp, blast="0915")
res_old = run_blast(holes, allh, old, comp, blast="0915")
j = json.loads(_bl.scan_path("3940","0915").read_text(encoding="utf-8"))
mb=[Polygon(p["pts"]).buffer(0) for p in j["polylines"] if p["layer"] not in {"爆区方格网","钻孔","点","线条","孔口文字"} and len(p["pts"])>=3 and _bl.is_block(Polygon(p["pts"]).buffer(0),p["layer"],allh)]
man=unary_union(mb)
def ext(g, out):
    for gg in ([g] if g.geom_type=="Polygon" else list(g.geoms)):
        x,y=gg.exterior.xy; out.append((x,y))
def ring_geom(res):
    r=res["rings"][0]
    for rr in res["rings"][1:]: r=r.union(rr)
    return r
rings={"new":ring_geom(res_new), "old":ring_geom(res_old)}
fig,axs=plt.subplots(1,2,figsize=(21,10))
for ax,(x0,x1,y0,y1),title in zip(axs,[(469995,470082,4349632,4349668),(469994,470030,4349635,4349658)],["3940-0915 全图对照","0915 西端头放大"]):
    ext(man, [])
    for gg in ([man] if man.geom_type=="Polygon" else list(man.geoms)):
        x,y=gg.exterior.xy; ax.plot(x,y,color="#d62728",lw=2.0,label="人工图")
    for key,col,ls,lw,lab in (("old","#999999","--",1.4,"旧闭合（端部借用内侧无品位孔）"),("new","#1f77b4","-",1.8,"新闭合（端部只认端外无品位孔 → 3 m）")):
        for gg in ([rings[key]] if rings[key].geom_type=="Polygon" else list(rings[key].geoms)):
            x,y=gg.exterior.xy; ax.plot(x,y,color=col,ls=ls,lw=lw,label=lab if key=="new" or True else None)
    for h in allh:
        col="orange" if h.grade>=0.5 else "black"
        ax.plot(h.x,h.y,"o",color=col,ms=5)
        ax.annotate(h.short.replace("BS-3940-0915-","")+"/%.2f"%h.grade,(h.x,h.y),fontsize=7.5)
    ax.set_xlim(x0,x1); ax.set_ylim(y0,y1); ax.set_aspect("equal"); ax.grid(alpha=.3)
    h,l=ax.get_legend_handles_labels(); seen=set(); hh=[];ll=[]
    for a,b in zip(h,l):
        if b in seen: continue
        seen.add(b); hh.append(a); ll.append(b)
    ax.legend(hh,ll,loc="upper left",fontsize=10)
    ax.set_title(title,fontsize=13)
fig.savefig(ROOT/"sample_data"/"output"/"审图_3940-0915_端部闭合对比.png",dpi=115,bbox_inches="tight")
print("saved")
