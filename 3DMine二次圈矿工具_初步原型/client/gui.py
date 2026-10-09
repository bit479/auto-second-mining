# -*- coding: utf-8 -*-
"""二次圈矿工具 · 桌面客户端
选择 Excel 炮孔数据库 → 一键生成三件套：
  1) DWG 2010 成果图   2) 炮孔数据报告 xlsx/PNG   3) 矿块边界线 .3ds
"""
from __future__ import annotations
import re
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext

ROOT = Path(__file__).resolve().parent.parent
CLIENT = Path(__file__).resolve().parent
PREP = CLIENT / "prep_generic.py"
MAKE = CLIENT / "make_dwg_generic.py"
CONV = CLIENT / "conv_generic.py"
PY = sys.executable


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
        root.geometry("860x620")
        root.minsize(720, 520)

        pad = {"padx": 8, "pady": 6}

        # ---- 输入区 ----
        frm = tk.LabelFrame(root, text="输入", padx=10, pady=8)
        frm.pack(fill="x", padx=10, pady=6)

        row1 = tk.Frame(frm)
        row1.pack(fill="x")
        tk.Label(row1, text="炮孔数据库 Excel：", width=16, anchor="w").pack(side="left")
        self.var_xls = tk.StringVar()
        tk.Entry(row1, textvariable=self.var_xls).pack(side="left", fill="x", expand=True)
        tk.Button(row1, text="浏览...", command=self.browse).pack(side="left", padx=4)

        row2 = tk.Frame(frm)
        row2.pack(fill="x", pady=(6, 0))
        tk.Label(row2, text="平台 / 日期：", width=16, anchor="w").pack(side="left")
        self.var_platform = tk.StringVar()
        tk.Entry(row2, textvariable=self.var_platform, width=10).pack(side="left")
        tk.Label(row2, text=" / ").pack(side="left")
        self.var_date = tk.StringVar()
        tk.Entry(row2, textvariable=self.var_date, width=10).pack(side="left")
        tk.Label(row2, text="  （从文件名自动识别，可手动改）", fg="#666").pack(side="left")

        row3 = tk.Frame(frm)
        row3.pack(fill="x", pady=(6, 0))
        tk.Label(row3, text="输出目录：", width=16, anchor="w").pack(side="left")
        self.var_out = tk.StringVar()
        tk.Entry(row3, textvariable=self.var_out).pack(side="left", fill="x", expand=True)
        tk.Button(row3, text="浏览...", command=self.browse_out).pack(side="left", padx=4)

        # ---- 按钮 ----
        btn = tk.Frame(root)
        btn.pack(fill="x", padx=10, pady=4)
        self.btn_start = tk.Button(btn, text="开始生成成果", command=self.start,
                                   bg="#4472C4", fg="white", font=("Microsoft YaHei", 11, "bold"),
                                   padx=18, pady=6)
        self.btn_start.pack(side="left")
        self.btn_open = tk.Button(btn, text="打开输出文件夹", command=self.open_out,
                                  state="disabled", padx=10)
        self.btn_open.pack(side="left", padx=8)

        # ---- 日志 ----
        tk.Label(root, text="运行日志：", anchor="w").pack(fill="x", padx=10)
        self.log = scrolledtext.ScrolledText(root, height=14, font=("Consolas", 9))
        self.log.pack(fill="both", expand=True, padx=10, pady=4)

        # ---- 成果区 ----
        tk.Label(root, text="成果文件：", anchor="w").pack(fill="x", padx=10)
        self.var_res = tk.StringVar(value="（尚未生成）")
        tk.Label(root, textvariable=self.var_res, anchor="w", fg="#0a6", justify="left",
                 wraplength=820).pack(fill="x", padx=10, pady=(0, 8))

        self.busy = False

    # ---------- 界面动作 ----------
    def browse(self):
        f = filedialog.askopenfilename(
            title="选择炮孔数据库 Excel", filetypes=[("Excel", "*.xls *.xlsx"), ("所有文件", "*.*")])
        if f:
            self.var_xls.set(f)
            plat, date = parse_platform_date(Path(f).name)
            if plat:
                self.var_platform.set(plat)
            if date:
                self.var_date.set(date)
            self.var_out.set(str(Path(f).parent / f"二次圈矿成果_{plat or '?'}_{date or '?'}"))

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
            os_startfile(d)

    def set_busy(self, busy):
        self.busy = busy
        self.btn_start.config(state="disabled" if busy else "normal")

    # ---------- 主流程 ----------
    def start(self):
        if self.busy:
            return
        xls = self.var_xls.get().strip()
        if not xls or not Path(xls).exists():
            messagebox.showwarning("缺少输入", "请先选择存在的炮孔数据库 Excel 文件。")
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
        self.log_line(f"炮孔数据库：{xls}")
        self.log_line(f"平台={platform}  日期={date}  输出={out}")
        self.log_line("-" * 60)
        t = threading.Thread(target=self.run_pipeline, args=(xls, platform, date, out), daemon=True)
        t.start()

    def run_pipeline(self, xls, platform, date, out):
        steps = [
            ("Step1 圈矿算量", [PY, "-X", "utf8", str(PREP), xls, platform, date, out]),
            ("Step2 生成图件/报告/.3ds", [PY, "-X", "utf8", str(MAKE), str(Path(out) / f"BS-{platform}-{date}_blocks.json"), out]),
        ]
        ok_all = True
        for name, cmd in steps:
            self.log_line(f"== {name} ==")
            try:
                p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     text=True, encoding="utf-8", errors="replace",
                                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                for line in p.stdout:
                    self.log_line(line.rstrip())
                p.wait(timeout=1800)
                if p.returncode != 0:
                    self.log_line(f"[失败] {name} 退出码 {p.returncode}")
                    ok_all = False
                    break
                self.log_line(f"[完成] {name}")
            except Exception as ex:
                self.log_line(f"[异常] {name}: {ex}")
                ok_all = False
                break
        self.log_line("-" * 60)
        if ok_all:
            blast = f"BS-{platform}-{date}"
            xlsx = Path(out) / f"{blast}_炮孔数据报告.xlsx"
            threeds = Path(out) / f"{blast}_矿块边界线.3ds"
            dxf = Path(out) / f"{blast}_二次圈矿矿块图_full.dxf"
            self.log_line("全部流程结束。")
            self.var_res.set(
                f"1) 矿块边界线(.3ds)：{threeds}\n"
                f"2) 炮孔数据报告：{xlsx}   （图片版：{Path(out) / f'{blast}_炮孔数据报告.png'}）\n"
                f"3) 成果图(DXF，如需 DWG 可在 CAD 里另存为)：{dxf}")
            self.btn_open.config(state="normal")
        else:
            self.var_res.set("（流程未全部成功，详见日志）")
        self.set_busy(False)


def os_startfile(p):
    import os
    try:
        os.startfile(p)  # noqa
    except Exception:
        subprocess.Popen(["explorer", p])


def main():
    import app_icon

    app_icon.set_app_user_model_id()   # 必须在 Tk() 之前，否则任务栏显示 python 图标
    root = tk.Tk()
    app_icon.set_window_icon(root)     # 标题栏左上角 + 默认窗口图标
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
