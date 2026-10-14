# -*- coding: utf-8 -*-
"""3960-0919 审图：人工(红) vs 自动(蓝) vs 严格档(绿)"""
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
plat, date = "3960", "0919"
pdir=ROOT.parent/("北部山头%s平台2026" % plat)
folder=[d for d in (pdir/"7、单日数据").iterdir() if d.is_dir() and d.name.endswith(date)][0]
holes=load_holes_xls(sorted(folder.glob("1、*.xls"))[0]); allh=list(holes.values())
comp_all=load_composite_blocks(sorted(pdir.glob("*综合*.dwg"))[0])
j=json.loads(_bl.scan_path(plat,date).read_text(encoding="utf-8"))
mb=[Polygon(p["pts"]).buffer(0) for p in j["polylines"] if p["layer"] not in {"爆区方格网","钻孔","点","线条","孔口文字"} and len(p["pts"])>=3 and _bl.is_block(Polygon(p["pts"]).buffer(0),p["layer"],allh)]
man=unary_union(mb)
base=_params.for_blast(date,platform=plat)
def ring_of(comp, **kw):
    P=dict(base); P.update(kw)
    r=run_blast(holes, allh, P, comp, blast=date)
    g=r["rings"][0]
    for rr in r["rings"][1:]: g=g.union(rr)
    return g, r
g_norm, r_norm = ring_of(comp_all, extrude_m=6.0, seam_join_m=0.5)
g_old, r_old = ring_of(comp_all, extrude_m=7.0, seam_join_m=0.0)
fig,ax=plt.subplots(figsize=(15,13))
for g in ([man] if man.geom_type=="Polygon" else list(man.geoms)):
    x,y=g.exterior.xy; ax.plot(x,y,color="#d62728",lw=2.4,label="人工图 %.0f m²" % man.area)
for g,col,ls,lab in ((g_old,"#1f77b4","-","自动 外推7m 不贴合 IoU %.3f 1块 %.0f m³" % (g_old.intersection(man).area/g_old.union(man).area, sum(b.volume_m3 for b in r_old["blocks"]))),
                     (g_norm,"#9467bd","--","自动 外推6m+贴合0.5m IoU %.3f %d块 %.0f m³" % (g_norm.intersection(man).area/g_norm.union(man).area, len(r_norm["blocks"]), sum(b.volume_m3 for b in r_norm["blocks"])))):
    for gg in ([g] if g.geom_type=="Polygon" else list(g.geoms)):
        x,y=gg.exterior.xy; ax.plot(x,y,color=col,ls=ls,lw=1.8,label=lab)
for h in allh:
    ax.plot(h.x,h.y,"o",color=("orange" if h.grade>=0.5 else "black"),ms=7)
    ax.annotate(h.short.replace("BS-3960-0919-","")+"/%.2f"%h.grade,(h.x,h.y),fontsize=9)
ax.set_aspect("equal"); ax.grid(alpha=.3); ax.legend(fontsize=11)
ax.set_title("3960-0919 人工图 vs 自动（人工只圈了 7 个矿孔那块，P31 单独一个矿孔没圈）")
fig.savefig(ROOT/"sample_data"/"output"/"审图_3960-0919.png",dpi=115,bbox_inches="tight"); print("ok")
