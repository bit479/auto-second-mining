# -*- coding: utf-8 -*-
# 无窗口驱动 GUI，跑一遍 3940-1008 的"一键出三件套"（勾选转 DWG、不并入），
# 验证"AutoCAD 没开也能自动拉起"这条链。
import sys
import tkinter as tk
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "client"))
import gui  # noqa: E402

XLS = Path(r"D:\WK\N CRT\北部山头3940平台2026\7、单日数据\北部山头3940平台-1008"
           r"\1、3940平台 炮孔数据库1008.xls")
COMP = Path(r"D:\WK\N CRT\北部山头3940平台2026\5、 北部山头3940平台二次圈矿矿块图-2026综合.dwg")
OUT = ROOT / "sample_data" / "output" / "GUI跑通_1008"

root = tk.Tk()
root.withdraw()
app = gui.App(root)


def setup():
    app.var_xls.set(str(XLS))
    app.var_comp.set(str(COMP))
    app.var_platform.set("3940")
    app.var_date.set("1008")
    app.var_out.set(str(OUT))
    app.var_dwg.set(True)      # 试 DXF -> DWG 2010（AutoCAD 未开时应自动拉起）
    app.var_merge.set(False)   # 不动用户的综合图目录
    app.start()
    root.after(2000, watch)


def watch(n=[0]):
    n[0] += 1
    if app.busy and n[0] < 900:
        root.after(1000, watch)
        return
    txt = app.log.get("1.0", "end")
    print("=== 日志尾部 ===")
    print("\n".join(txt.strip().splitlines()[-14:]))
    print("=== 产出 ===")
    for f in sorted(OUT.iterdir()):
        print("   %-46s %7.1f KB" % (f.name, f.stat().st_size / 1024))
    root.after(400, root.destroy)


root.after(500, setup)
root.after(1800000, root.destroy)
root.mainloop()
