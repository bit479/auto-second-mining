# -*- coding: utf-8 -*-
"""打开真实 GUI，并让它自己跑一次「一键出三件套」（Tk 调用全部在主线程，避免线程死锁）。
跑完把日志写进 _gui_run.log，然后关掉窗口。
"""
import sys, tkinter as tk
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "client"))
import gui

XLS = Path(r"D:\WK\N CRT\北部山头3940平台2026\7、单日数据\北部山头3940平台-1004\1、3940平台 炮孔数据库1004.xls")
COMP = Path(r"D:\WK\N CRT\北部山头3940平台2026\5、 北部山头3940平台二次圈矿矿块图-2026综合.dwg")
OUT = ROOT / "sample_data" / "output" / "GUI跑通_1004"
LOG = ROOT / "_probe" / "_gui_run.log"

root = tk.Tk()
app = gui.App(root)
steps = []

def setup():
    app.var_xls.set(str(XLS)); app.var_comp.set(str(COMP))
    app.var_platform.set("3940"); app.var_date.set("1004")
    app.var_out.set(str(OUT))
    app.var_dwg.set(True); app.var_merge.set(False)
    app.refresh_params()
    steps.append("参数区(生效值): %s" % {k: v.get() for k, v in app.var_p.items()})
    app.start()
    root.after(2000, watch)

def watch(n=[0]):
    n[0] += 1
    if app.busy and n[0] < 900:
        root.after(1000, watch); return
    steps.append("=== GUI 运行日志 ===")
    steps.append(app.log.get("1.0", "end"))
    steps.append("=== 成果文件 ===")
    if OUT.exists():
        for f in sorted(OUT.iterdir()):
            steps.append("   %-52s %8.1f KB" % (f.name, f.stat().st_size / 1024))
    LOG.write_text("\n".join(steps), encoding="utf-8")
    print("已写日志", LOG)
    root.after(500, root.destroy)

root.after(600, setup)
root.after(180000, root.destroy)     # 保险：3 分钟必关
root.mainloop()
