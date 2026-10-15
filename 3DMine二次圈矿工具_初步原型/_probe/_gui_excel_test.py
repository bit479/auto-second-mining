# -*- coding: utf-8 -*-
# 无窗口验证：主界面里"把数据库所在的那天并入总表（预演）"这条链能不能走通。
import sys
import tkinter as tk
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "client"))
import gui  # noqa: E402

XLS = Path(r"D:\WK\N CRT\北部山头3940平台2026\7、单日数据\北部山头3940平台-1008"
           r"\1、3940平台 炮孔数据库1008.xls")

root = gui.TkinterDnD.Tk() if gui.DND_OK else tk.Tk()
root.withdraw()
app = gui.App(root)


def setup():
    app.var_xls.set(str(XLS))
    app.merge_day(dry=True)
    root.after(2000, watch)


def watch(n=[0]):
    n[0] += 1
    if app.busy and n[0] < 200:
        root.after(1000, watch)
        return
    print("=== 日志（并入预演）===")
    print(app.log.get("1.0", "end").strip()[:1200])
    print("=== 结论标签 ===")
    print(app.var_res.get())
    root.after(300, root.destroy)


root.after(500, setup)
root.after(600000, root.destroy)
root.mainloop()
