# -*- coding: utf-8 -*-
"""「TXT 坐标 + 粘贴品位表 -> 炮孔数据库」窗口。"""
from __future__ import annotations

import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

ROOT = Path(__file__).resolve().parent.parent
CORE = ROOT / "core"
if str(CORE) not in sys.path:
    sys.path.insert(0, str(CORE))

from make_database import (build, parse_grades, parse_tag_from_txt,  # noqa: E402
                           parse_txt)


class DbBuilder:
    def __init__(self, master, txt_path=None):
        self.win = tk.Toplevel(master)
        self.win.title("自动生成炮孔数据库（TXT + 品位表）")
        self.win.geometry("920x700")
        self.win.minsize(760, 580)
        self.var_txt = tk.StringVar()
        self.var_out = tk.StringVar()
        self.var_platform = tk.StringVar()
        self.var_date = tk.StringVar()
        self.var_bench = tk.StringVar(value="10.0")

        info = tk.Label(
            self.win, anchor="w", fg="#0a6",
            text="① 选坐标 TXT（每行：工程号,,E,N,R）  ② 把品位表整段粘贴到下面  "
                 "③ 生成 .xls + .mdb（3DMine 可直接打开）")
        info.pack(fill="x", padx=12, pady=(10, 4))

        frm = tk.Frame(self.win)
        frm.pack(fill="x", padx=12)
        tk.Label(frm, text="坐标 TXT：", width=12, anchor="w").pack(side="left")
        tk.Entry(frm, textvariable=self.var_txt).pack(side="left", fill="x", expand=True)
        tk.Button(frm, text="浏览…", command=self.browse_txt).pack(side="left", padx=4)

        frm = tk.Frame(self.win)
        frm.pack(fill="x", padx=12, pady=(6, 0))
        tk.Label(frm, text="输出目录：", width=12, anchor="w").pack(side="left")
        tk.Entry(frm, textvariable=self.var_out).pack(side="left", fill="x", expand=True)
        tk.Button(frm, text="浏览…", command=self.browse_out).pack(side="left", padx=4)

        frm = tk.Frame(self.win)
        frm.pack(fill="x", padx=12, pady=(6, 0))
        tk.Label(frm, text="平台 / 日期：", width=12, anchor="w").pack(side="left")
        tk.Entry(frm, textvariable=self.var_platform, width=8).pack(side="left")
        tk.Label(frm, text=" / ").pack(side="left")
        tk.Entry(frm, textvariable=self.var_date, width=8).pack(side="left")
        tk.Label(frm, text="   台阶高度(m)：").pack(side="left")
        tk.Entry(frm, textvariable=self.var_bench, width=7).pack(side="left")
        tk.Label(frm, text="（孔底高程 = 平台高程 − 台阶高度）", fg="#666").pack(side="left")

        tk.Label(self.win, text="粘贴品位数据（支持从 Excel 直接粘贴，也支持 Markdown 表格）：",
                 anchor="w").pack(fill="x", padx=12, pady=(10, 2))
        self.txt_grades = scrolledtext.ScrolledText(
            self.win, height=12, font=("Consolas", 9), wrap="none")
        self.txt_grades.pack(fill="both", expand=True, padx=12)

        bar = tk.Frame(self.win)
        bar.pack(fill="x", padx=12, pady=8)
        tk.Button(bar, text="解析预览", command=self.preview, padx=12).pack(side="left")
        self.btn_make = tk.Button(
            bar, text="生成 .xls + .mdb", command=self.make,
            bg="#4472C4", fg="white", font=("Microsoft YaHei", 10, "bold"),
            padx=16, pady=4)
        self.btn_make.pack(side="left", padx=8)
        tk.Button(bar, text="打开输出目录", command=self.open_out, padx=10).pack(side="left")
        tk.Button(bar, text="关闭", command=self.win.destroy, padx=10).pack(side="right")

        self.log = scrolledtext.ScrolledText(
            self.win, height=4, font=("Consolas", 9), state="disabled")
        self.log.pack(fill="x", padx=12, pady=(0, 10))

        if txt_path:
            self.set_txt(Path(txt_path))
        self.win.update_idletasks()
        self.win.geometry("920x700")

    def set_txt(self, p: Path):
        self.var_txt.set(str(p))
        self.var_out.set(str(p.parent))
        plat, date = parse_tag_from_txt(p)
        if plat:
            self.var_platform.set(plat)
        if date:
            self.var_date.set(date)
        self.log_line("已选坐标 TXT：%s" % p)
        try:
            holes = parse_txt(p)
            self.log_line("读到 %d 个炮孔（%s … %s）"
                          % (len(holes), holes[0].hid, holes[-1].hid))
        except Exception as exc:
            self.log_line("[错误] %s" % exc)

    def browse_txt(self):
        p = filedialog.askopenfilename(
            title="选择炮孔坐标 TXT",
            filetypes=[("坐标 TXT", "*.txt"), ("所有文件", "*.*")])
        if p:
            self.set_txt(Path(p))

    def browse_out(self):
        p = filedialog.askdirectory(title="选择输出目录")
        if p:
            self.var_out.set(p)

    def log_line(self, s):
        self.log.configure(state="normal")
        self.log.insert("end", s + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _parse(self):
        p = Path(self.var_txt.get().strip())
        if not p.is_file():
            raise ValueError("找不到坐标 TXT：%s" % p)
        holes = parse_txt(p)
        grades = parse_grades(self.txt_grades.get("1.0", "end"), holes)
        return holes, grades

    def preview(self):
        try:
            holes, grades = self._parse()
        except Exception as exc:
            messagebox.showerror("解析失败", str(exc), parent=self.win)
            return
        self.log_line("解析：TXT %d 孔；品位表读到 %d 行、匹配 %d 孔"
                      % (len(holes), grades.n_rows, len(grades.grades)))
        if grades.missing:
            self.log_line("[缺品位] " + "、".join(grades.missing[:20])
                          + (" … 共 %d 个" % len(grades.missing)
                             if len(grades.missing) > 20 else ""))
        if grades.extra:
            self.log_line("[多出] " + "、".join(sorted(set(grades.extra))[:12])
                          + (" …" if len(set(grades.extra)) > 12 else ""))
        if grades.duplicates:
            self.log_line("[重复且品位不同] " + "；".join(grades.duplicates[:6]))
        if not grades.missing and not grades.duplicates:
            self.log_line("✓ 品位表与 TXT 工程号完全对应")
        for h in holes[:5]:
            g = grades.grades.get(h.hid)
            self.log_line("  %s  E=%.3f N=%.3f R=%.3f  Au=%s"
                          % (h.hid, h.e, h.n, h.r,
                             "%.*f" % (grades.decimals, g) if g is not None else "缺"))

    def make(self):
        try:
            holes, grades = self._parse()
        except Exception as exc:
            messagebox.showerror("解析失败", str(exc), parent=self.win)
            return
        if grades.missing:
            messagebox.showerror(
                "品位表不全",
                "缺少 %d 个工程号：\n%s" % (len(grades.missing),
                                             "、".join(grades.missing[:30])),
                parent=self.win)
            return
        if grades.duplicates:
            messagebox.showerror("品位冲突", "同一工程号出现不同品位：\n%s"
                                 % "；".join(grades.duplicates[:10]), parent=self.win)
            return
        txt = Path(self.var_txt.get().strip())
        out = Path(self.var_out.get().strip() or txt.parent)
        platform = self.var_platform.get().strip()
        date = self.var_date.get().strip()
        if not platform or not date:
            messagebox.showerror("缺平台/日期", "请填写平台高程和日期编号。", parent=self.win)
            return
        exists = [p.name for p in (
            out / ("1、%s平台 炮孔数据库%s.xls" % (platform, date)),
            out / ("2、%s平台炮孔数据库%s.mdb" % (platform, date))) if p.exists()]
        force = False
        if exists:
            if not messagebox.askyesno(
                    "文件已存在",
                    "以下文件已存在：\n%s\n\n是否先备份到 bak\\ 再覆盖？" % "\n".join(exists),
                    parent=self.win):
                return
            force = True
        try:
            res = build(txt, self.txt_grades.get("1.0", "end"), out_dir=out,
                        platform=platform, date=date,
                        bench_height=self.var_bench.get().strip() or 10.0,
                        force=force)
        except Exception as exc:
            messagebox.showerror("生成失败", str(exc), parent=self.win)
            self.log_line("[错误] %s" % exc)
            return
        self.log_line("✓ 生成完成：%d 孔" % res["holes"])
        self.log_line("  " + str(res["xls"]))
        self.log_line("  " + str(res["mdb"]))
        if res["extra"]:
            self.log_line("  [提示] 品位表多出的工程号已忽略：%s"
                          % "、".join(res["extra"][:10]))
        messagebox.showinfo("生成完成",
                            "已生成：\n%s\n%s" % (res["xls"], res["mdb"]),
                            parent=self.win)

    def open_out(self):
        p = self.var_out.get().strip()
        if p and os.path.isdir(p):
            os.startfile(p)

