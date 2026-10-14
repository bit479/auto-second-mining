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
RUN_BATCH = CORE / "run_batch.py"
MERGE_COMP = CORE / "merge_to_composite.py"
CALIBRATE = CORE / "calibrate.py"
APPLY_MERGE = CORE / "apply_merge.py"
PROBE = ROOT / "_probe"
PARAMS_REPORT = PROBE / "params_report.py"
ACCEPT_ALL = PROBE / "accept_all.py"
ACCEPT_REPORT = ROOT / "验收报告.md"
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


def _acad_running() -> bool:
    """AutoCAD 在不在跑（不在的话第 2/3 步要先把它拉起来）。"""
    try:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq acad.exe"],
                             capture_output=True, text=True, errors="replace").stdout
        return "acad.exe" in (out or "").lower()
    except Exception:
        return False


class App:
    def __init__(self, root):
        self.root = root
        root.title("二次圈矿工具客户端")
        root.geometry("940x740")
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

        # ---- 参数区（按平台可覆盖，存 圈矿参数.json）----
        pf = tk.LabelFrame(root, text="参数（留空=用默认；改完点“存为该平台默认”或“存为该炮区”）",
                           padx=10, pady=6)
        pf.pack(fill="x", padx=10, pady=(0, 4))
        self.var_p = {}
        NUMS = (("extrude_m", "外推(m)"), ("zone_link_m", "连接半径(m)"),
                ("min_fragment_m2", "最小块段(m²)"), ("merge_gap_m", "接综合图(m)"),
                ("seam_join_m", "贴合综合图(m)"), ("isolated_min_holes", "孤立组最少孔数"),
                ("ring_alpha_k", "外轮廓兜底k"))
        self.btn_p = {}
        for i, (key, label) in enumerate(NUMS):
            r, c = divmod(i, 3)
            tk.Label(pf, text=label).grid(row=r * 2, column=c * 2, sticky="e", padx=(6, 2))
            v = tk.StringVar()
            tk.Entry(pf, textvariable=v, width=7).grid(row=r * 2, column=c * 2 + 1, sticky="w")
            self.var_p[key] = v
        tk.Label(pf, text="精确模式轮廓文件(.3ds，多个用分号隔开；填了就照人工画的矿界出图)",
                 fg="#333").grid(row=6, column=0, columnspan=2, sticky="e", pady=(6, 0))
        self.var_outline = tk.StringVar()
        tk.Entry(pf, textvariable=self.var_outline).grid(
            row=6, column=2, columnspan=4, sticky="we", pady=(6, 0))
        tk.Button(pf, text="…", width=3,
                  command=self.browse_outline).grid(row=6, column=6, padx=6, sticky="w")
        tk.Button(pf, text="存为该平台默认", command=self.save_params).grid(
            row=7, column=0, padx=(6, 4), pady=(8, 0), sticky="w")
        tk.Button(pf, text="存为该炮区", command=lambda: self.save_params(blast=True)).grid(
            row=7, column=1, padx=4, pady=(8, 0), sticky="w")
        tk.Button(pf, text="刷新参数", command=self.refresh_params).grid(
            row=7, column=2, padx=4, pady=(8, 0), sticky="w")
        tk.Label(pf, text="（默认 外推3.0 / 连接15 / 最小块段40 / 接图8 / 贴合0.5；"
                          "1003 外推 2.5，各炮区另有个别覆盖）",
                 fg="#666").grid(row=8, column=0, columnspan=7, sticky="w", pady=(6, 0))

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
        self.btn_batch = tk.Button(btn, text="批量跑整个目录…", command=self.start_batch,
                                   padx=10)
        self.btn_batch.pack(side="left", padx=8)
        self.btn_merge = tk.Button(btn, text="并入综合图（副本）…", command=self.start_merge,
                                   padx=10)
        self.btn_merge.pack(side="left", padx=8)
        self.btn_cal = tk.Button(btn, text="用人工图标定本炮区…", command=self.start_calibrate,
                                 padx=10)
        self.btn_cal.pack(side="left", padx=8)
        self.btn_apply = tk.Button(btn, text="确认替换综合图原件…", command=self.start_apply,
                                   padx=10)
        self.btn_apply.pack(side="left", padx=8)
        self.var_dwg = tk.BooleanVar(value=True)
        tk.Checkbutton(btn, text="转 DWG 2010（需本机 AutoCAD；失败就留 DXF）",
                       variable=self.var_dwg).pack(side="left", padx=12)
        self.var_merge = tk.BooleanVar(value=True)
        tk.Checkbutton(btn, text="圈完顺手并入综合图副本（出预览）",
                       variable=self.var_merge).pack(side="left", padx=6)

        # ---- 自查（参数台账 / 一键验收）----
        diag = tk.Frame(root)
        diag.pack(fill="x", padx=10, pady=(0, 4))
        tk.Button(diag, text="查看参数台账", command=self.start_params_report,
                  padx=10).pack(side="left")
        tk.Button(diag, text="跑一键验收（全量，约 3 分钟）",
                  command=lambda: self.start_accept(False), padx=10).pack(side="left", padx=8)
        tk.Button(diag, text="快检（只挑代表炮区）",
                  command=lambda: self.start_accept(True), padx=10).pack(side="left", padx=4)
        self.btn_report = tk.Button(diag, text="打开验收报告",
                                    command=self.open_accept_report, state="disabled",
                                    padx=10)
        self.btn_report.pack(side="left", padx=8)

        # ---- 日志 ----
        tk.Label(root, text="运行日志：", anchor="w").pack(fill="x", padx=10)
        self.log = scrolledtext.ScrolledText(root, height=15, font=("Consolas", 9))
        self.log.pack(fill="both", expand=True, padx=10, pady=4)

        tk.Label(root, text="成果文件：", anchor="w").pack(fill="x", padx=10)
        self.var_res = tk.StringVar(value="（尚未生成）")
        tk.Label(root, textvariable=self.var_res, anchor="w", fg="#0a6", justify="left",
                 wraplength=860).pack(fill="x", padx=10, pady=(0, 8))

        self.busy = False
        self.refresh_params()

    # ---------- 参数 ----------
    def _params_mod(self):
        if str(CORE) not in sys.path:
            sys.path.insert(0, str(CORE))
        import params
        return params

    def refresh_params(self):
        try:
            p = self._params_mod()
            plat = self.var_platform.get().strip()
            date = self.var_date.get().strip() or ""
            if date and plat:
                P = p.for_blast(date, platform=plat)
            elif plat:
                P = p.for_platform(plat)
            else:
                P = p.load()
            for k, v in self.var_p.items():
                val = P.get(k)
                v.set("" if val is None else ("%g" % float(val)))
            files = P.get("outline_files") or []
            self.var_outline.set(";".join(str(x) for x in files))
        except Exception:
            pass

    def save_params(self, blast: bool = False):
        """把参数区写回 圈矿参数.json。

        坑（2026-10-14 修）：原来一律写进 `platforms[<日期>]`（拿日期当平台号），
        存完根本不生效（`for_blast` 查的是 `platforms[<平台号>]` 和 `blasts[<平台>-<日期>]`）。
        现在：勾"存为该炮区"→ `blasts["<平台>-<日期>"]`；否则 → `platforms[<平台>]`；
        没有平台号就写全局默认。
        """
        try:
            p = self._params_mod()
            cfg = p.load()
            plat = self.var_platform.get().strip()
            date = self.var_date.get().strip()
            vals = {}
            for k, v in self.var_p.items():
                s = v.get().strip()
                if s:
                    vals[k] = (int(float(s)) if k == "isolated_min_holes"
                               else float(s))
            files = [x.strip() for x in self.var_outline.get().split(";") if x.strip()]
            if files or self.var_outline.get().strip() != "":
                vals["outline_files"] = files
            if not vals:
                messagebox.showinfo("参数", "没有要保存的值。")
                return
            if blast:
                if not (plat and date):
                    messagebox.showinfo("参数", "存为该炮区需要先填平台号和日期。")
                    return
                key = "%s-%s" % (plat, date)
                cfg.setdefault("blasts", {}).setdefault(key, {}).update(vals)
                where = "炮区 %s" % key
            elif plat:
                cfg.setdefault("platforms", {}).setdefault(plat, {}).update(vals)
                where = "平台 %s" % plat
            else:
                cfg.update(vals)
                where = "全局默认"
            path = p.save(cfg)
            messagebox.showinfo("参数", "已保存为%s：\n%s" % (where, path))
        except Exception as ex:
            messagebox.showerror("参数", "保存失败：%s" % ex)

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
        self.refresh_params()

    def browse_comp(self):
        f = filedialog.askopenfilename(
            title="选择该平台的综合图 DWG",
            filetypes=[("DWG", "*.dwg"), ("所有文件", "*.*")])
        if f:
            self.var_comp.set(f)

    def browse_outline(self):
        """精确模式：挑人工从 3DMine 导出的矿界 .3ds（可多选，分号分隔）。"""
        fs = filedialog.askopenfilenames(
            title="选择人工导出的矿界 .3ds（可多选：左边界/与综合图边界/右边界/右上边界…）",
            filetypes=[("3DMine 字符串", "*.3ds"), ("所有文件", "*.*")])
        if fs:
            self.var_outline.set(";".join(str(x) for x in fs))

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

    # ---------- 自查：参数台账 / 一键验收 ----------
    def _run_stream(self, name, cmd, on_done=None):
        """跑一个子进程，把输出**流式**打到日志区（台账、验收这类自查都用它）。"""
        self.set_busy(True)
        self.log.delete("1.0", "end")
        self.log_line("== %s ==" % name)
        self.log_line("-" * 68)

        def job():
            ok = True
            try:
                p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     text=True, encoding="utf-8", errors="replace",
                                     creationflags=CREATE_NO_WINDOW)
                for line in p.stdout:
                    self.log_line(line.rstrip())
                p.wait(timeout=7200)
                ok = (p.returncode == 0)
            except Exception as ex:
                self.log_line("[异常] %s" % ex)
                ok = False
            if on_done:
                on_done(ok)
            self.set_busy(False)

        threading.Thread(target=job, daemon=True).start()

    def start_params_report(self):
        """参数台账：谁覆盖了什么、值多少、依据是什么（只看日志，不动参数）。"""
        if self.busy:
            return
        plat = self.var_platform.get().strip()
        cmd = [PY, "-X", "utf8", str(PARAMS_REPORT)] + ([plat] if plat else [])
        self._run_stream("参数台账（params_report.py）", cmd)

    def start_accept(self, quick: bool):
        """一键验收：圈矿闸门 + 报告口径 + 成果图实体自检 + 精确模式自检。"""
        if self.busy:
            return
        cmd = [PY, "-X", "utf8", str(ACCEPT_ALL)] + (["--quick"] if quick else [])

        def done(ok):
            self.var_res.set("一键验收：%s\n报告：%s" %
                             ("通过 ✓" if ok else "**有未通过项**，见日志", ACCEPT_REPORT))
            self.btn_report.config(state="normal")

        self._run_stream("一键验收（accept_all.py%s）" % ("，快检" if quick else "，全量"),
                         cmd, done)

    def open_accept_report(self):
        if ACCEPT_REPORT.exists():
            try:
                os.startfile(str(ACCEPT_REPORT))
            except Exception:
                pass

    def set_busy(self, busy):
        self.busy = busy
        self.btn_start.config(state="disabled" if busy else "normal")
        self.btn_batch.config(state="disabled" if busy else "normal")
        self.btn_merge.config(state="disabled" if busy else "normal")
        self.btn_cal.config(state="disabled" if busy else "normal")
        self.btn_apply.config(state="disabled" if busy else "normal")

    # ---------- 主流程 ----------
    def start_apply(self):
        """把"并入后的副本"正式替换原件——**先自动备份**，并弹窗确认要改哪些文件。"""
        if self.busy:
            return
        comp = self.var_comp.get().strip()
        init = str(Path(comp).parent) if comp else None
        merged = filedialog.askopenfilename(
            title="选择要启用的「并入后的副本」DWG（文件名形如 …_并入1008.dwg）",
            initialdir=init, filetypes=[("DWG", "*.dwg")])
        if not merged:
            return
        if not messagebox.askyesno(
                "确认替换原件",
                "将执行：\n"
                "① 原综合图改名备份为 «原名_原版_时间戳.dwg»（不删除）\n"
                "② 把\n  %s\n复制成原综合图的名字\n"
                "③ 出问题可把备份改回原名即可回退\n\n"
                "确认继续？" % Path(merged).name):
            self.log_line("已取消替换。")
            return
        self.set_busy(True)
        self.log.delete("1.0", "end")
        self.log_line("替换原件：%s" % merged)
        self.log_line("-" * 68)

        def job():
            ok = True
            try:
                p = subprocess.Popen([PY, "-X", "utf8", str(APPLY_MERGE), merged],
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     text=True, encoding="utf-8", errors="replace",
                                     creationflags=CREATE_NO_WINDOW)
                for line in p.stdout:
                    self.log_line(line.rstrip())
                p.wait(timeout=600)
                ok = p.returncode == 0
            except Exception as ex:
                self.log_line("[异常] %s" % ex)
                ok = False
            self.log_line("-" * 68)
            self.var_res.set("已替换原件（备份见日志）" if ok else "（替换未完成，详见日志）")
            self.set_busy(False)

        threading.Thread(target=job, daemon=True).start()

    def start_calibrate(self):
        """拿一张人工圈矿图，自动标出该炮区的"外推距离 + 左右链"并写进参数。"""
        if self.busy:
            return
        plat = self.var_platform.get().strip()
        date = self.var_date.get().strip()
        if not (plat and date):
            messagebox.showwarning("缺少参数", "平台号和日期都要填（如 3940 / 1008）。")
            return
        dwg = filedialog.askopenfilename(
            title="选择该炮区的人工圈矿图 DWG",
            initialdir=str(Path(self.var_xls.get()).parent) if self.var_xls.get() else None,
            filetypes=[("DWG", "*.dwg")])
        if not dwg:
            return
        self.set_busy(True)
        self.log.delete("1.0", "end")
        self.log_line("标定炮区 %s-%s，人工图 %s" % (plat, date, dwg))
        self.log_line("-" * 68)

        def job():
            ok = True
            try:
                # 原来没传 --platform，calibrate 会默认按 3940 找数据库/写参数
                # （3960 的炮区就会标错平台）；现在按界面上的平台号传进去
                p = subprocess.Popen([PY, "-X", "utf8", str(CALIBRATE), date, dwg,
                                      "--platform", plat, "--write"],
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     text=True, encoding="utf-8", errors="replace",
                                     creationflags=CREATE_NO_WINDOW)
                for line in p.stdout:
                    self.log_line(line.rstrip())
                p.wait(timeout=3600)
                ok = p.returncode == 0
            except Exception as ex:
                self.log_line("[异常] %s" % ex)
                ok = False
            self.log_line("-" * 68)
            if ok:
                self.refresh_params()
                self.var_res.set("标定完成，参数已写入 圈矿参数.json（见日志）")
            else:
                self.var_res.set("（标定未完成，详见日志）")
            self.set_busy(False)

        threading.Thread(target=job, daemon=True).start()

    def start_merge(self):
        """把当天的矿块边界并进综合图的一个副本（原件不动）。"""
        if self.busy:
            return
        comp = self.var_comp.get().strip()
        if not comp or not Path(comp).exists():
            comp = filedialog.askopenfilename(
                title="选择综合图 DWG", filetypes=[("DWG", "*.dwg")])
            if not comp:
                return
            self.var_comp.set(comp)
        out = self.var_out.get().strip()
        guess = Path(out) / "矿块边界线.3ds" if out else None
        init = str(Path(out)) if out and Path(out).exists() else str(Path(comp).parent)
        tds = filedialog.askopenfilename(
            title="选择本日的矿块边界线 .3ds（一般在当天成果目录里）",
            initialdir=init, filetypes=[("3DS", "*.3ds")])
        if not tds:
            return
        self.set_busy(True)
        self.log.delete("1.0", "end")
        self.log_line("并入副本：综合图 %s" % comp)
        self.log_line("矿块边界线：%s" % tds)
        self.log_line("-" * 68)

        def job():
            ok = True
            try:
                p = subprocess.Popen([PY, "-X", "utf8", str(MERGE_COMP), comp, tds],
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     text=True, encoding="utf-8", errors="replace",
                                     creationflags=CREATE_NO_WINDOW)
                for line in p.stdout:
                    self.log_line(line.rstrip())
                p.wait(timeout=1800)
                ok = p.returncode == 0
            except Exception as ex:
                self.log_line("[异常] %s" % ex)
                ok = False
            self.log_line("-" * 68)
            self.log_line("原件始终没动；复核副本没问题后，你再决定要不要替换原件。")
            self.var_res.set("（副本见上方日志；原件未改动）" if ok else "（并入失败，详见日志）")
            self.set_busy(False)

        threading.Thread(target=job, daemon=True).start()

    def start_batch(self):
        """选一个"装着多个单日炮区"的父目录，一次跑完并出横向汇总。"""
        if self.busy:
            return
        parent = filedialog.askdirectory(
            title="选择父目录（里面每个子目录是一天的炮区）")
        if not parent:
            return
        comp = self.var_comp.get().strip()
        if not comp or not Path(comp).exists():
            comp = filedialog.askopenfilename(
                title="选择该平台的综合图 DWG", filetypes=[("DWG", "*.dwg")])
            if not comp:
                return
            self.var_comp.set(comp)
        out = str(Path(parent) / "_批量汇总")
        self.var_out.set(out)
        Path(out).mkdir(parents=True, exist_ok=True)
        self.set_busy(True)
        self.log.delete("1.0", "end")
        self.log_line("批量模式：父目录 %s" % parent)
        self.log_line("综合图：%s" % comp)
        self.log_line("-" * 68)

        def job():
            ok = True
            self.log_line("== 批量圈矿 ==")
            try:
                p = subprocess.Popen([PY, "-X", "utf8", str(RUN_BATCH), parent, comp, out],
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     text=True, encoding="utf-8", errors="replace",
                                     creationflags=CREATE_NO_WINDOW)
                for line in p.stdout:
                    self.log_line(line.rstrip())
                p.wait(timeout=3600)
                ok = p.returncode == 0
            except Exception as ex:
                self.log_line("[异常] %s" % ex)
                ok = False
            self.log_line("-" * 68)
            if ok:
                self.var_res.set(
                    "批量汇总：%s\n%s\n%s"
                    % (Path(out) / "批量汇总.xlsx", Path(out) / "批量汇总.png",
                       Path(out) / "批量总览.png"))
                self.btn_open.config(state="normal")
            else:
                self.var_res.set("（批量流程未成功，详见日志）")
            self.set_busy(False)

        threading.Thread(target=job, daemon=True).start()

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
            if not _acad_running():
                self.log_line("（AutoCAD 没在运行，正在拉起它——首次启动约 30~60 秒，请稍等）")
            if not run("第 2 步 DXF → DWG 2010（AutoCAD）",
                       [PY, "-X", "utf8", str(DXF2DWG), str(dxf), "--start"]):
                self.log_line("（DWG 转换没成功：最常见是 AutoCAD 起不来或停在对话框里。"
                              "DXF 已保留——在 CAD 里手工打开它另存为 2010 即可；"
                              "也可以在界面上取消勾选“转 DWG 2010”跳过这一步）")

        tds = Path(out) / ("%s矿块边界线.3ds" % tag)
        merged = None
        if ok_all and self.var_merge.get() and tds.exists():
            if not _acad_running():
                self.log_line("（AutoCAD 没在运行，正在拉起它——首次启动约 30~60 秒，请稍等）")
            if run("第 3 步 并入综合图副本（原件不动）",
                   [PY, "-X", "utf8", str(MERGE_COMP), comp, str(tds), "--start"]):
                for line in str(self.log.get("1.0", "end")).splitlines():
                    if "_并入" in line and ".dwg" in line:
                        merged = line.strip().split("->")[-1].strip()
                self.log_line("（副本可复核后再自己决定是否替换原件）")
            else:
                self.log_line("（并入副本没成功：多半是 AutoCAD 起不来或停在对话框里。"
                              "副本文件其实已经复制出来了，等 CAD 空闲后单独重跑这一步即可；"
                              "也可以在界面上取消勾选“圈完顺手并入综合图副本”）")

        self.log_line("-" * 68)
        if ok_all:
            xlsx = Path(out) / ("%s炮孔数据报告.xlsx" % tag)
            png = Path(out) / ("%s炮孔数据报告.png" % tag)
            lines = ["1) 报告：%s   （图片版 %s）" % (xlsx, png),
                     "2) 成果图：%s" % (dwg if dwg.exists() else dxf),
                     "3) 边界线 .3ds：%s" % tds]
            if merged:
                lines.append("4) 并入后的综合图副本：%s（预览见同名 _预览.png）" % merged)
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
