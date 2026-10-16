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

# 拖拽支持（可选）：装了 tkinterdnd2 就能把文件从资源管理器拖进来
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_OK = True
except Exception:                    # 没装也不影响其它功能，只是不能拖
    DND_FILES = None
    TkinterDnD = None
    DND_OK = False

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
VERSION = "v1.3"            # 界面上会显示——以后一眼就能看出跑的是哪版代码
EXCEL_TOOLS = ROOT / "excel_tools"          # 整合进来的"炮孔数据工具"（报告汇总 + 单日并入总表）
EXCEL_MAIN = EXCEL_TOOLS / "main.py"
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


def count_3ds_lines(paths) -> int:
    """数一下这几个 .3ds 里一共有几条闭合折线——用来帮用户判断该用哪种模式。"""
    try:
        if str(CORE) not in sys.path:
            sys.path.insert(0, str(CORE))
        from strip import read_3ds_polylines
        return sum(len(read_3ds_polylines(p)) for p in paths if Path(p).exists())
    except Exception:
        return 0


class App:
    def __init__(self, root):
        self.root = root
        root.title("二次圈矿工具客户端  %s" % VERSION)
        root.geometry("940x740")
        root.minsize(760, 560)
        self._manual_dwg = None      # 拖进来的"人工圈矿图"，给"标定本炮区"直接用

        # ---- 输入 ----
        frm = tk.LabelFrame(root, text="输入（两个都要给）", padx=10, pady=8)
        frm.pack(fill="x", padx=10, pady=6)

        if DND_OK:
            tk.Label(frm, text="（可以把文件从资源管理器直接拖进来："
                              "数据库 Excel / 综合图 DWG / 人工圈矿图 DWG / 轮廓 .3ds / 输出文件夹）",
                     fg="#0a6", anchor="w").pack(fill="x", pady=(0, 4))
        else:
            tk.Label(frm, text="（想支持「拖进来」就装一下：pip install tkinterdnd2）",
                     fg="#a60", anchor="w").pack(fill="x", pady=(0, 4))

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
        # 三种模式用单选按钮，避免"填了 .3ds 却忘了切换模式"
        self.var_mode = tk.StringVar(value="auto")
        mrow = tk.Frame(pf)
        mrow.grid(row=7, column=0, columnspan=8, sticky="w", pady=(4, 0))
        tk.Label(mrow, text="圈矿模式：", fg="#0a6").pack(side="left")
        for val, txt in (("auto", "① 自动圈矿"),
                         ("manual", "② 人工圈矿（每条闭合线 = 一块）"),
                         ("exact", "③ 精确模式（整条当矿界）")):
            tk.Radiobutton(mrow, text=txt, value=val, variable=self.var_mode,
                           fg="#0a6").pack(side="left", padx=(6, 0))
        tk.Label(pf, text="　　① 程序自己圈；② 你画的 .3ds 每条线一块；③ 整条当矿界、界内按品位分块",
                 fg="#666").grid(row=7, column=4, columnspan=4, sticky="w")
        tk.Button(pf, text="存为该平台默认", command=self.save_params).grid(
            row=8, column=0, padx=(6, 4), pady=(8, 0), sticky="w")
        tk.Button(pf, text="存为该炮区", command=lambda: self.save_params(blast=True)).grid(
            row=8, column=1, padx=4, pady=(8, 0), sticky="w")
        tk.Button(pf, text="刷新参数", command=self.refresh_params).grid(
            row=8, column=2, padx=4, pady=(8, 0), sticky="w")
        tk.Label(pf, text="（默认 外推3.0 / 连接15 / 最小块段40 / 接图8 / 贴合0.5；"
                          "1003 外推 2.5，各炮区另有个别覆盖）",
                 fg="#666").grid(row=9, column=0, columnspan=7, sticky="w", pady=(6, 0))

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

        # ---- Excel 工具（整合进来的"炮孔数据工具"：报告汇总 / 单日并入总表）----
        xt = tk.LabelFrame(root, text="Excel 工具（报告汇总 / 单日数据并入总表）", padx=10, pady=6)
        xt.pack(fill="x", padx=10, pady=(0, 4))
        tk.Button(xt, text="炮孔报告汇总…", padx=10,
                  command=lambda: self.open_excel_tool("report")).pack(side="left")
        tk.Button(xt, text="单日数据并入总表…", padx=10,
                  command=lambda: self.open_excel_tool("daily")).pack(side="left", padx=8)
        tk.Label(xt, text="（上面两个打开完整窗口：选文件/目录、有预演与还原）",
                 fg="#666").pack(side="left", padx=(4, 12))
        tk.Button(xt, text="把数据库所在的那天并入总表（预演）", padx=10,
                  command=lambda: self.merge_day(dry=True)).pack(side="left")
        tk.Button(xt, text="正式并入", padx=10,
                  command=lambda: self.merge_day(dry=False)).pack(side="left", padx=6)

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
        if DND_OK:
            self._setup_dnd()

    # ---------- 拖拽（把文件从资源管理器拖进来）----------
    def _setup_dnd(self):
        """整个窗口和几个输入框都注册成拖放目标；松开鼠标就按扩展名/文件名分流。"""
        targets = [self.root]
        for w in self.root.winfo_children():
            targets.append(w)
        for t in targets:
            for w in ([t] + list(t.winfo_children())):
                try:
                    w.drop_target_register(DND_FILES)
                    w.dnd_bind("<<Drop>>", self.on_drop)
                except Exception:
                    pass

    def on_drop(self, event):
        """把拖进来的东西分流到对应的输入框。

        * 文件夹            → 输出目录
        * .xls/.xlsx        → 炮孔数据库（并自动识别平台/日期、自动找同目录的综合图、设输出目录）
        * .dwg 名字带"综合"  → 综合图
        * .dwg 其它          → 记成"人工圈矿图"，点「用人工图标定本炮区…」时直接用，不再弹选择框
        * .3ds              → 精确模式轮廓文件（可一次拖好几个，分号分隔）
        """
        try:
            paths = [Path(p) for p in self.root.tk.splitlist(event.data)]
        except Exception:
            paths = []
        if not paths:
            return
        notes = []
        outlines = []
        for p in paths:
            if p.is_dir():
                self.var_out.set(str(p))
                notes.append("输出目录 ← %s" % p.name)
                continue
            ext = p.suffix.lower()
            if ext in (".xls", ".xlsx"):
                self._set_xls(p)
                notes.append("炮孔数据库 ← %s" % p.name)
            elif ext == ".dwg":
                if "综合" in p.name:
                    self.var_comp.set(str(p))
                    notes.append("综合图 ← %s" % p.name)
                else:
                    self._manual_dwg = p
                    plat, date = parse_platform_date(p.name)
                    if plat:
                        self.var_platform.set(plat)
                    if date:
                        self.var_date.set(date)
                    notes.append("人工圈矿图 ← %s（点「用人工图标定本炮区…」会直接用它）" % p.name)
            elif ext == ".3ds":
                outlines.append(str(p))
            else:
                notes.append("（没认出来，忽略）%s" % p.name)
        if outlines:
            notes.append("精确模式轮廓 ← %s" % "；".join(Path(x).name for x in outlines))
        self.log.delete("1.0", "end")
        # 注意顺序：refresh_params() 会按"平台+日期"重填轮廓框，所以拖进来的轮廓要**在它之后**写
        self.refresh_params()
        if outlines:
            self.var_outline.set(";".join(outlines))
        self.log_line("拖入 %d 个对象：" % len(paths))
        for n in notes:
            self.log_line("   " + n)

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
        self._set_xls(Path(f))

    def _set_xls(self, f: Path):
        """选/拖到一个数据库之后要做的事：填框、识平台日期、找综合图、设输出目录。"""
        f = Path(f)
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
        # 注意顺序：refresh_params() 会按"平台+日期"重填参数框（含轮廓框），
        # 所以自动取用的 .3ds 必须**在它之后**写。
        # 炮区文件夹里如果有 .3ds（比如"选择集对象.3ds"），**自动填上并选好模式**——
        # 用户 2026-10-15：他的习惯就是把它放这儿，不想每次在界面上找
        threes = sorted(folder.glob("*.3ds"))
        if threes:
            pick = next((c for c in threes if "分品位" in c.name), threes[0])
            n = count_3ds_lines([str(pick)])
            self.var_outline.set(str(pick))
            mode = "exact" if n <= 1 else "manual"
            self.var_mode.set(mode)
            self.log.delete("1.0", "end")
            self.log_line("炮区文件夹里发现 %d 个 .3ds，自动取用：%s（%d 条闭合线）"
                          % (len(threes), pick.name, n))
            self.log_line("   模式自动设为：%s" % ("③ 精确模式（整条当矿界、界内按品位分块）"
                                              if mode == "exact" else
                                              "② 人工圈矿（每条闭合线 = 一块）"))
            self.log_line("   —— 要用别的 .3ds 或改成①自动圈矿，在参数区自己改。")

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

    # ---------- Excel 工具（整合进来的"炮孔数据工具"）----------
    def open_excel_tool(self, tab: str = "report"):
        """打开完整窗口：报告汇总（tab=report）/ 单日并入总表（tab=daily）。"""
        if not EXCEL_MAIN.exists():
            messagebox.showwarning("找不到工具", "没见过 %s" % EXCEL_MAIN)
            return
        try:
            subprocess.Popen([PY, "-X", "utf8", str(EXCEL_MAIN), "--gui", "--tab", tab],
                             cwd=str(EXCEL_TOOLS))
            self.log_line("已打开 Excel 工具：%s（%s）"
                          % ("单日数据并入总表" if tab == "daily" else "炮孔报告汇总", EXCEL_MAIN))
        except Exception as ex:
            messagebox.showerror("打开失败", str(ex))

    def merge_day(self, dry: bool = True):
        """把"当前数据库所在的那个单日文件夹"并入年度总表（调用整合进来的 daily_merge）。"""
        if self.busy:
            return
        xls = self.var_xls.get().strip()
        if not xls or not Path(xls).exists():
            messagebox.showwarning("缺少输入", "先选一个炮孔数据库 Excel——用它所在的文件夹当单日目录。")
            return
        day_dir = str(Path(xls).parent)
        if not dry:
            if not messagebox.askyesno(
                    "确认并入总表",
                    "把这一天的资料并入年度总表：\n%s\n\n"
                    "· 三份文件并入总表（xls / mdb / 综合报告）\n"
                    "· 二次圈矿矿块图复制进总目录的「6、…矿块图」文件夹（去掉「5、」前缀）\n\n"
                    "（总表会先备份成 <原名>_并入<日>.bak；按工程号判重，重复运行安全；\n"
                    " 矿块图已有同名同内容就跳过，不同则先备份成 <原名>.bak 再覆盖）\n\n"
                    "确定现在正式写入吗？" % day_dir):
                return
        cmd = [PY, "-X", "utf8", str(EXCEL_MAIN), "--daily", "--day-dir", day_dir]
        if dry:
            cmd.append("--dry-run")

        def done(ok):
            self.var_res.set("并入总表%s：%s\n日志见上"
                             % ("（预演）" if dry else "（正式）",
                                "完成 ✓" if ok else "有失败项，见日志"))

        self._run_stream("单日数据并入总表（%s）\n单日目录：%s"
                         % ("预演，不写盘" if dry else "正式写入", day_dir), cmd, done)

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
        if self._manual_dwg is not None and Path(self._manual_dwg).exists():
            dwg = str(self._manual_dwg)          # 拖进来的那张，直接用
        else:
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
        # 防呆：填了 .3ds 却选"自动圈矿"——直接问一句，别又白跑一次
        outlines = [x.strip() for x in self.var_outline.get().split(";") if x.strip()]
        mode = self.var_mode.get()
        if outlines and mode == "auto":
            n = count_3ds_lines(outlines)
            # 1 条闭合线 = 多半是"整个矿界"，界内还要按品位分块 → 精确模式；
            # 多条线 = 多半是"一块一条线" → 人工圈矿模式。
            suggest, how = (("exact", "③ 精确模式（整条当矿界、界内按品位再分块）")
                            if n <= 1 else
                            ("manual", "② 人工圈矿（%d 条闭合线 = %d 块，只算量出图）" % (n, n)))
            if messagebox.askyesno(
                    "模式没切",
                    "你填了 .3ds 轮廓（里面 %d 条闭合线）：\n%s\n\n"
                    "但圈矿模式选的是「① 自动圈矿」——那样**不会用你的线**。\n\n"
                    "要不要改用 %s？\n\n"
                    "选「是」= 就按它跑；选「否」= 忽略这个 .3ds、按自动圈矿跑"
                    % (n, "\n".join(outlines[:3]), how)):
                mode = suggest
                self.var_mode.set(suggest)
                self.log_line("（已按提示切到「%s」）" % how)
        self.var_res.set("（生成中...）")
        self.set_busy(True)
        self.log.delete("1.0", "end")
        self.log_line("炮孔数据库：%s" % xls)
        self.log_line("综合图    ：%s" % comp)
        self.log_line("平台=%s  日期=%s" % (platform, date))
        self.log_line("输出目录  ：%s" % out)
        self.log_line("-" * 68)
        threading.Thread(target=self.run_pipeline,
                         args=(xls, platform, date, out, comp,
                               outlines, mode), daemon=True).start()

    def run_pipeline(self, xls, platform, date, out, comp, outlines=None, mode="auto"):
        tag = "%s平台 %s" % (platform, date)
        ok_all = True
        # 人工画线：② 人工圈矿 → --manual-blocks（每条线一块）；③ 精确模式 → --outline（整条当矿界）
        extra = []
        if outlines and mode in ("manual", "exact"):
            extra += (["--manual-blocks", ";".join(outlines)] if mode == "manual"
                      else ["--outline", ";".join(outlines)])
            self.log_line("人工画线：%s（%s）" % (
                "人工圈矿模式：每条闭合线当一块、只算量出图" if mode == "manual"
                else "精确模式：整条当矿界、界内按品位再分块", ";".join(outlines)))
        elif outlines:
            self.log_line("（注意：填了 .3ds 但模式是「自动圈矿」，这次不用你的线）")

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
                     [PY, "-X", "utf8", str(RUN_STRIP), xls, platform, date, out, comp] + extra)

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
    # 支持拖拽就用 TkinterDnD 的根窗口（它继承自 tk.Tk，其余用法一样）
    root = TkinterDnD.Tk() if DND_OK else tk.Tk()
    if app_icon is not None:
        try:
            app_icon.set_window_icon(root)
        except Exception:
            pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
