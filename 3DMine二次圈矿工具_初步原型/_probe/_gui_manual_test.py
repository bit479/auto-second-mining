# -*- coding: utf-8 -*-
# 无窗口驱动 GUI，跑一遍"人工圈矿模式"：把用户画的 .3ds 填进轮廓栏、勾上人工圈矿，出三件套。
import sys
import tkinter as tk
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "client"))
import gui  # noqa: E402

day = Path(r"D:\WK\N CRT\北部山头3970平台2026")
blast = day / "7、单日数据" / "北部山头3970平台-1011"
XLS = blast / "1、3970平台 炮孔数据库1011.xls"
COMP = day / "5、 北部山头3970平台二次圈矿矿块图-2026综合.dwg"
OUT = ROOT / "sample_data" / "output" / "人工圈矿3970_1011"

root = gui.TkinterDnD.Tk() if gui.DND_OK else tk.Tk()
root.withdraw()
app = gui.App(root)


def setup():
    app.var_xls.set(str(XLS))
    app.var_comp.set(str(COMP))
    app.var_platform.set("3970")
    app.var_date.set("1011")
    app.var_out.set(str(OUT))
    app.var_dwg.set(False)          # 这次只验圈矿/算量/出图
    app.var_merge.set(False)
    app.var_outline.set(str(blast / "选择集对象分品位.3ds"))
    app.var_manual.set(True)        # ← 人工圈矿模式
    app.start()
    root.after(2000, watch)


def watch(n=[0]):
    n[0] += 1
    if app.busy and n[0] < 300:
        root.after(1000, watch)
        return
    txt = app.log.get("1.0", "end")
    keep = [l for l in txt.splitlines() if ("人工画线" in l or "模式：**人工圈矿" in l
            or "号 " in l or "合计" in l or "[完成]" in l or "[失败]" in l)]
    print("\n".join(keep))
    print("=== 产出 ===")
    for f in sorted(OUT.iterdir()):
        print("   %-46s %7.1f KB" % (f.name, f.stat().st_size / 1024))
    root.after(400, root.destroy)


root.after(500, setup)
root.after(900000, root.destroy)
root.mainloop()
