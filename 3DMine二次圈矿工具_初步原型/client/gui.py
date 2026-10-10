# -*- coding: utf-8 -*-
"""二次圈矿工具 · 桌面客户端（走标定过的 core 流程）。

输入两个文件 → 一键出三件套：
  ① 炮孔数据库 Excel（必填）
  ② 该平台的综合图 DWG（必填，每次手工指定）
产出：
  1) 炮孔数据报告 xlsx + 图片
  2) 二次圈矿矿块图（DWG 2010；转换不了就留 DXF）
  3) 矿块边界线 .3ds
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext

ROOT = Path(__file__).resolve().parent.parent
CLIENT = Path(__file__).resolve().parent
CORE = ROOT / "core"
RUN_STRIP = CORE / "run_strip.py"
DXF2DWG = CORE / "dxf2dwg.py"
PY = sys.executable
PYW = str(Path(PY).with_name("pythonw.exe")) if Path(PY).with_name("pythonw.exe").exists() else PY
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def parse_platform_date(fname: str):
    s = str(fname)
    m = re.search(r"(\d{3,4})\s*平台", s)
    platform = m.group(1) if m else ""
    rest = s[m.end():] if m else s
    d = re.search(r"(\d{4})(?=\.\w+$|[^0-9]|$)", rest)
    return platform, (d.group(1) if d else "")


class App:
    def __init__(self, root):
        self.root = root
        root.title("二次圈矿工具客户端")
        root.geometry("900x680")
        root.minsize(760, 560)

        # ---- 输入 ----
        frm = tk.LabelFrame(root, text="输入（两个都要给）", padx=10, pady=8)
        frm.pack(fill="x", padx=10, pady=6)

        row1 = tk.Frame(frm)
        row1.pack(fill="x")
        tk.Label(row1, text="① 炮孔数据库 Excel：", width=18, anchor="w").pack(side="left")
        self.var_xls = tk.StringVar()
        tk.Entry(row1, textvariable=self.var_xls).pack(side="left", fill="x", expand=True)
        tk.Button(row1, text="浏览...", command=self.browse).pack(side="left", padx=4)

        rowc = tk.Frame(frm)
        rowc.pack(fill="x", pady=(6, 0))
        tk.Label(rowc, text="② 综合图 DWG：", width=18, anchor="w").pack(side="left")
        self.var_comp = tk.StringVar()
        tk.Entry(rowc, textvariable=self.var_comp).pack(side="left", fill="x", expand=True)
        tk.Button(rowc, text="浏览...", command=self.browse_comp).pack(side="left", padx=4)

        row2 = tk.Frame(frm)
        row2.pack(fill="x", pady=(6, 0))
        tk.Label(row2, text="平台 / 日期：", width=18, anchor="w").pack(side="left")
        self.var_platform = tk.StringVar()
        tk.Entry(row2, textvariable=self.var_platform, width=10).pack(side="left")
        tk.Label(row2, text=" / ").pack(side="left")
        self.var_date = tk.StringVar()
        tk.Entry(row2, textvariable=self.var_date, width=10).pack(side="left")
        tk.Label(row2, text="  （从文件名自动识别，可手动改）", fg="#666").pack(side="left")

        row3 = tk.Frame(frm)
        row3.pack(fill="x", pady=(6, 0))
        tk.Label(row3, text="输出目录：", width=18, anchor="w").pack(side="left")
        self.var_out = tk.StringVar()
        tk.Entry(row3, textvariable=self.var_out).pack(side="left", fill="x", expand=True)
        tk.Button(row3, text="浏览...", command=self.browse_out).pack(side="left", padx=4)

        # ---- 按钮 ----
        btn = tk.Frame(root)
        btn.pack(fill="x", padx=10, pady=4)
        self.btn_start = tk.Button(btn, text="一键出三件套", command=self.start,
                                   bg="#4472C4", fg="white",
                                   font=("Microsoft YaHei", 11, "bold"), padx=18, pady=6)
        self.btn_start.pack(side="left")
        self.btn_open = tk.Button(btn, text="打开输出文件夹", command=self.open_out,
                                  state="disabled", padx=10)
        self.btn_open.pack(side="left", padx=8)
        self.var_dwg = tk.BooleanVar(value=True)
        tk.Checkbutton(btn, text="转 DWG 2010（需本机 AutoCAD；失败就留 DXF）",
                       variable=self.var_dwg).pack(side="left", padx=12)

        # ---- 日志 ----
        tk.Label(root, text="运行日志：", anchor="w").pack(fill="x", padx=10)
        self.log = scrolledtext.ScrolledText(root, height=15, font=("Consolas", 9))
        self.log.pack(fill="both", expand=True, padx=10, pady=4)

        tk.Label(root, text="成果文件：", anchor="w").pack(fill="x", padx=10)
        self.var_res = tk.StringVar(value="（尚未生成）")
        tk.Label(root, textvariable=self.var_res, anchor="w", fg="#0a6", justify="left",
                 wraplength=860).pack(fill="x", padx=10, pady=(0, 8))

        self.busy = False

    # ---------- 界面动作 ----------
    def browse(self):
        f = filedialog.askopenfilename(
            title="选择炮孔数据库 Excel",
            filetypes=[("Excel", "*.xls *.xlsx"), ("所有文件", "*.*")])
        if not f:
            return
        self.var_xls.set(f)
        plat, date = parse_platform_date(Path(f).name)
        if plat:
            self.var_platform.set(plat)
        if date:
            self.var_date.set(date)
        folder = Path(f).parent
        self.var_out.set(str(folder / ("二次圈矿成果_%s_%s" % (plat or "?", date or "?"))))
        # 自动找同目录/上级目录里的综合图
        for cand in sorted(folder.glob("*综合*.dwg")) + \
                sorted(folder.parent.glob("*综合*.dwg")) + \
                [folder.parent / "5、 北部山头3940平台二次圈矿矿块图-2026综合.dwg"]:
            if cand.exists():
                self.var_comp.set(str(cand))
                break

    def browse_comp(self):
        f = filedialog.askopenfilename(
            title="选择该平台的综合图 DWG",
            filetypes=[("DWG", "*.dwg"), ("所有文件", "*.*")])
        if f:
            self.var_comp.set(f)

    def browse_out(self):
        d = filedialog.askdirectory(title="选择输出目录")
        if d:
            self.var_out.set(d)

    def log_line(self, s):
        self.log.insert("end", s + "\n")
        self.log.see("end")
        self.root.update_idletasks()

    def open_out(self):
        d = self.var_out.get()
        if d and Path(d).exists():
            try:
                os.startfile(d)
            except Exception:
                subprocess.Popen(["explorer", d])

    def set_busy(self, busy):
        self.busy = busy
        self.btn_start.config(state="disabled" if busy else "normal")

    # ---------- 主流程 ----------
    def start(self):
        if self.busy:
            return
        xls = self.var_xls.get().strip()
        comp = self.var_comp.get().strip()
        if not xls or not Path(xls).exists():
            messagebox.showwarning("缺少输入", "请先选择存在的炮孔数据库 Excel。")
            return
        if not comp or not Path(comp).exists():
            messagebox.showwarning("缺少输入", "请指定该平台的综合图 DWG（每次都要手工给）。")
            return
        platform = self.var_platform.get().strip()
        date = self.var_date.get().strip()
        if not platform or not date:
            messagebox.showwarning("缺少参数", "平台和日期不能为空。")
            return
        out = self.var_out.get().strip() or str(Path(xls).parent)
        Path(out).mkdir(parents=True, exist_ok=True)
        self.var_res.set("（生成中...）")
        self.set_busy(True)
        self.log.delete("1.0", "end")
        self.log_line("炮孔数据库：%s" % xls)
        self.log_line("综合图    ：%s" % comp)
        self.log_line("平台=%s  日期=%s" % (platform, date))
        self.log_line("输出目录  ：%s" % out)
        self.log_line("-" * 68)
        threading.Thread(target=self.run_pipeline,
                         args=(xls, platform, date, out, comp), daemon=True).start()

    def run_pipeline(self, xls, platform, date, out, comp):
        tag = "%s平台 %s" % (platform, date)
        ok_all = True

        def run(name, cmd):
            self.log_line("== %s ==" % name)
            try:
                p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, text=True,
                                     encoding="utf-8", errors="replace",
                                     creationflags=CREATE_NO_WINDOW)
                for line in p.stdout:
                    self.log_line(line.rstrip())
                p.wait(timeout=3600)
                if p.returncode != 0:
                    self.log_line("[失败] %s 退出码 %s" % (name, p.returncode))
                    return False
                self.log_line("[完成] %s" % name)
                return True
            except Exception as ex:
                self.log_line("[异常] %s: %s" % (name, ex))
                return False

        ok_all = run("第 1 步 圈矿算量 + 出报告/图/.3ds",
                     [PY, "-X", "utf8", str(RUN_STRIP), xls, platform, date, out, comp])

        dxf = Path(out) / ("%s二次圈矿矿块图.dxf" % tag)
        dwg = Path(out) / ("%s二次圈矿矿块图_2010.dwg" % tag)
        if ok_all and self.var_dwg.get() and dxf.exists():
            if not run("第 2 步 DXF → DWG 2010（AutoCAD）",
                       [PY, "-X", "utf8", str(DXF2DWG), str(dxf)]):
                self.log_line("（DWG 转换没成功，DXF 已保留，可在 CAD 里手工另存 2010）")

        self.log_line("-" * 68)
        if ok_all:
            xlsx = Path(out) / ("%s炮孔数据报告.xlsx" % tag)
            png = Path(out) / ("%s炮孔数据报告.png" % tag)
            tds = Path(out) / ("%s矿块边界线.3ds" % tag)
            lines = ["1) 报告：%s   （图片版 %s）" % (xlsx, png),
                     "2) 成果图：%s" % (dwg if dwg.exists() else dxf),
                     "3) 边界线 .3ds：%s" % tds]
            self.log_line("全部流程结束。")
            self.var_res.set("\n".join(lines))
            self.btn_open.config(state="normal")
        else:
            self.var_res.set("（流程未全部成功，详见日志）")
        self.set_busy(False)


def main():
    try:
        import app_icon
        app_icon.set_app_user_model_id()
    except Exception:
        app_icon = None
    root = tk.Tk()
    if app_icon is not None:
        try:
            app_icon.set_window_icon(root)
        except Exception:
            pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
