# -*- coding: utf-8 -*-
"""通用审图：人工图 vs 自动圈矿（单炮区）。用法: python _review_one.py <平台> <日期> [外推m]"""
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
plat=sys.argv[1]; date=sys.argv[2]
pdir=ROOT.parent/("北部山头%s平台2026" % plat)
folder=[d for d in (pdir/"7、单日数据").iterdir() if d.is_dir() and d.name.endswith(date)][0]
holes=load_holes_xls(sorted(folder.glob("1、*.xls"))[0]); allh=list(holes.values())
comp=load_composite_blocks(sorted(pdir.glob("*综合*.dwg"))[0])
P=dict(_params.for_blast(date,platform=plat))
if len(sys.argv)>3: P["extrude_m"]=float(sys.argv[3])
res=run_blast(holes, allh, P, comp, blast=date)
j=json.loads(_bl.scan_path(plat,date).read_text(encoding="utf-8"))
mb=[]
for p in j["polylines"]:
    if p["layer"] in {"爆区方格网","钻孔","点","线条","孔口文字"} or len(p["pts"])<3: continue
    poly=Polygon(p["pts"]).buffer(0)
    if _bl.is_block(poly,p["layer"],allh): mb.append((p["layer"],poly))
fig,ax=plt.subplots(figsize=(15,13))
for lay,poly in mb:
    x,y=poly.exterior.xy; ax.plot(x,y,color="#d62728",lw=2.0)
    c=poly.representative_point(); ax.annotate("人工%.0f"%poly.area,(c.x,c.y),color="#d62728",fontsize=10)
for b in res["blocks"]:
    for g in ([b.polygon] if b.polygon.geom_type=="Polygon" else list(b.polygon.geoms)):
        x,y=g.exterior.xy; ax.plot(x,y,color="green",lw=1.5)
        c=g.representative_point(); ax.annotate("自动%.0f(g%.2f)"%(b.polygon.area,b.grade),(c.x,c.y),color="green",fontsize=10)
for rr in res["rings"]:
    for g in ([rr] if rr.geom_type=="Polygon" else list(rr.geoms)):
        x,y=g.exterior.xy; ax.plot(x,y,color="blue",lw=1.0,ls="--")
for h in allh:
    ax.plot(h.x,h.y,"o",color=("orange" if h.grade>=0.5 else "black"),ms=5)
    ax.annotate(h.short.split("-")[-1]+"/%.2f"%h.grade,(h.x,h.y),fontsize=8)
ax.set_aspect("equal"); ax.grid(alpha=.3)
ax.set_title("%s-%s  人工(红) vs 自动(绿)  外推=%.1f 块数 %d  警告:%s" % (plat,date,P["extrude_m"],len(res["blocks"]),res["warn"]))
out=ROOT/"sample_data"/"output"/("审图_%s-%s.png" % (plat,date))
fig.savefig(out,dpi=115,bbox_inches="tight"); print("->",out)
