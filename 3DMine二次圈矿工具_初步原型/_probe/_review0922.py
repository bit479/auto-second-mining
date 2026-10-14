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
folder=[d for d in (DAY/"7、单日数据").iterdir() if d.is_dir() and d.name.endswith("0922")][0]
holes=load_holes_xls(sorted(folder.glob("1、*.xls"))[0]); allh=list(holes.values())
comp=load_composite_blocks(DAY/"5、 北部山头3940平台二次圈矿矿块图-2026综合.dwg")
res=run_blast(holes, allh, _params.for_blast("0922",platform="3940"), comp, blast="0922")
j=json.loads(_bl.scan_path("3940","0922").read_text(encoding="utf-8"))
mb=[(p["layer"],Polygon(p["pts"]).buffer(0)) for p in j["polylines"] if p["layer"] not in {"爆区方格网","钻孔","点","线条","孔口文字"} and len(p["pts"])>=3 and _bl.is_block(Polygon(p["pts"]).buffer(0),p["layer"],allh)]
fig,ax=plt.subplots(figsize=(15,12))
for lay,poly in mb:
    for g in ([poly] if poly.geom_type=="Polygon" else list(poly.geoms)):
        x,y=g.exterior.xy; ax.plot(x,y,color="#d62728",lw=2.0)
        c=g.representative_point(); ax.annotate("人工 %.0f"%poly.area,(c.x,c.y),color="#d62728",fontsize=9)
for b in res["blocks"]:
    for g in ([b.polygon] if b.polygon.geom_type=="Polygon" else list(b.polygon.geoms)):
        x,y=g.exterior.xy; ax.plot(x,y,color="green",lw=1.4)
        c=g.representative_point(); ax.annotate("自动%.0f(g%.2f)"%(b.polygon.area,b.grade),(c.x,c.y),color="green",fontsize=9)
for rr in res["rings"]:
    for g in ([rr] if rr.geom_type=="Polygon" else list(rr.geoms)):
        x,y=g.exterior.xy; ax.plot(x,y,color="blue",lw=1.0,ls="--")
for h in allh:
    ax.plot(h.x,h.y,"o",color=("orange" if h.grade>=0.5 else "black"),ms=6)
    ax.annotate(h.short.replace("BS-3940-0922-","")+"/%.2f"%h.grade,(h.x,h.y),fontsize=8)
ax.set_aspect("equal"); ax.grid(alpha=.3); ax.legend(["人工图块","","","自动矿块","矿界"],fontsize=10)
ax.set_title("3940-0922 人工(红) vs 自动(绿)  外推=9.0m")
fig.savefig(ROOT/"sample_data"/"output"/"审图_3940-0922.png",dpi=115,bbox_inches="tight"); print("ok")
