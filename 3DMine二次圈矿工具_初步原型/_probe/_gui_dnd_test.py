# -*- coding: utf-8 -*-
# 验证拖拽分流：造一个假的 <<Drop>> 事件，喂几种路径给 on_drop，看落到哪个框里。
import sys
import tkinter as tk
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "client"))
import gui  # noqa: E402


class FakeEvent:
    def __init__(self, data):
        self.data = data


root = gui.TkinterDnD.Tk() if gui.DND_OK else tk.Tk()
root.withdraw()
app = gui.App(root)
print("DND_OK =", gui.DND_OK)

# ① 数据文件夹里的三样（数据库 / 人工圈矿图 / 综合图）
db = (r"{D:\WK\N CRT\北部山头3940平台2026\7、单日数据\北部山头3940平台-1011"
      r"\1、3940平台 炮孔数据库1011.xls}")
fig = r"{D:\WK\N CRT\北部山头3940平台2026\7、单日数据\北部山头3940平台-1011\5、 北部山头3940平台二次圈矿矿块图1011.dwg}"
comp = r"{D:\WK\N CRT\北部山头3940平台2026\5、 北部山头3940平台二次圈矿矿块图-2026综合.dwg}"
out3ds = r"{C:\Users\Administrator\Desktop\左边界，未外推.3ds} {C:\Users\Administrator\Desktop\右边界，未外推.3ds}"
app.on_drop(FakeEvent("%s %s %s" % (db, fig, comp)))
print("① 数据库 :", app.var_xls.get())
print("  平台/日期:", app.var_platform.get(), "/", app.var_date.get())
print("  综合图  :", app.var_comp.get())
print("  输出目录:", app.var_out.get())
print("  人工图  :", app._manual_dwg)

app.on_drop(FakeEvent(out3ds))
print("② 精确模式轮廓:", app.var_outline.get())

app.on_drop(FakeEvent(r"{D:\WK\N CRT\release_v1}"))
print("③ 输出目录:", app.var_out.get())

print("--- 日志区内容 ---")
print(app.log.get("1.0", "end").strip()[:600])
root.destroy()
