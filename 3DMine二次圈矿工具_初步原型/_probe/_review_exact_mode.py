# -*- coding: utf-8 -*-
"""1008 精确模式 vs 自动：人工图(红) / 自动矿界(蓝) / 人工导出的四段线拼出的矿界(绿)"""
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
import params as _params, baseline as _bl, strip as S
DAY = ROOT.parent/"北部山头3940平台2026"; date="1008"
folder=[d for d in (DAY/"7、单日数据").iterdir() if d.is_dir() and d.name.endswith(date)][0]
holes=load_holes_xls(sorted(folder.glob("1、*.xls"))[0]); allh=list(holes.values())
comp=load_composite_blocks(DAY/"5、 北部山头3940平台二次圈矿矿块图-2026综合.dwg")
j=json.loads(_bl.scan_path("3940",date).read_text(encoding="utf-8"))
man=unary_union([Polygon(p["pts"]).buffer(0) for p in j["polylines"] if p["layer"] not in {"爆区方格网","钻孔","点","线条","孔口文字"} and len(p["pts"])>=3 and _bl.is_block(Polygon(p["pts"]).buffer(0),p["layer"],allh)])
P=_params.for_blast(date,platform="3940")
r_auto=run_blast(holes, allh, P, comp, blast=date)
g_auto=r_auto["rings"][0]
for rr in r_auto["rings"][1:]: g_auto=g_auto.union(rr)
D=Path(r"C:\Users\Administrator\Desktop")
parts=["左边界，已外推3m.3ds","与综合图边界.3ds","右边界，已外推3m.3ds","连接辅助线中点形成右上边界.3ds"]
g_out=S.ring_from_outline_files([D/n for n in parts])
fig,ax=plt.subplots(figsize=(13,13))
for g,col,ls,lab in ((man,"#d62728","-","人工图 %.0f m²" % man.area),
                     (g_auto,"#1f77b4","--","自动圈矿 %.0f m²（IoU %.3f）" % (g_auto.area, g_auto.intersection(man).area/g_auto.union(man).area)),
                     (g_out,"#2ca02c","-","精确模式：人工四段线拼出 %.0f m²（IoU %.3f）" % (g_out.area, g_out.intersection(man).area/g_out.union(man).area))):
    for gg in ([g] if g.geom_type=="Polygon" else list(g.geoms)):
        x,y=gg.exterior.xy; ax.plot(x,y,color=col,ls=ls,lw=2.2,label=lab)
for h in allh:
    ax.plot(h.x,h.y,"o",color=("orange" if h.grade>=0.5 else "black"),ms=5)
    ax.annotate(h.short.replace("BS-3940-1008-",""),(h.x,h.y),fontsize=7.5)
ax.set_aspect("equal"); ax.grid(alpha=.3); ax.legend(fontsize=11,loc="lower left")
ax.set_title("3940-1008：精确模式（导入人工画好的矿界）与自动圈矿对比")
fig.savefig(ROOT/"sample_data"/"output"/"审图_1008精确模式.png",dpi=115,bbox_inches="tight"); print("ok")
