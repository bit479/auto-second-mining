"""图形界面：两个标签页。

* **炮孔数据报告汇总** —— 把若干份 3DMine 报告汇总成一份炮孔数据报告；
* **单日数据并入总表** —— 把某一天的 xls / mdb / 报告 并入 2026 年三份总表。

不带命令行参数运行 main.py 会自动打开本界面；``--tab daily`` 直达第二个标签页。
"""

from __future__ import annotations

import ctypes
import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.blast_report.builder import MergeOptions, merge_reports  # noqa: E402
from src.excel_core.reader import find_input_files, natural_key_compat  # noqa: E402

# 任务栏图标：Windows 默认按 python.exe 归组，必须显式声明 AppUserModelID
# 才能让任务栏显示我们自己的图标而不是 Python 的蛇标。
APP_USER_MODEL_ID = "BlastReport.MergeTool.1"
ICON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "app.ico")


def set_app_user_model_id() -> None:
    """必须在创建任何窗口之前调用，任务栏才会用我们自己的图标分组。"""
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:  # noqa: BLE001 - 非 Windows 或接口缺失时静默跳过
        pass


def set_window_icon(root: tk.Tk) -> None:
    """设置窗口左上角图标。"""
    if os.path.exists(ICON_PATH):
        try:
            # -default 形式才会接受 .ico，并同时作为标题栏与后续窗口的默认图标
            root.iconbitmap(default=ICON_PATH)
        except Exception:  # noqa: BLE001
            pass


def apply_app_icon(root: tk.Tk) -> None:
    """兼容入口：先声明 AppUserModelID，再设窗口图标。"""
    set_app_user_model_id()
    set_window_icon(root)


FILE_TYPES = [("Excel 文件", "*.xlsx;*.xlsm;*.xls;*.csv"), ("所有文件", "*.*")]

_PAD = {"padx": 8, "pady": 4}


# ==========================================================================
# 标签页一：炮孔数据报告汇总
# ==========================================================================

class ReportTab(ttk.Frame):
    """选文件 → 定输出 → 一键汇总。"""

    def __init__(self, master):
        super().__init__(master)
        self.root = master.winfo_toplevel()

        self.files: list[str] = []
        self.output_var = tk.StringVar()
        self.title_var = tk.StringVar()
        self.appendix_var = tk.BooleanVar(value=True)
        self.formula_var = tk.BooleanVar(value=True)

        self._build_ui()

    # ---------- 界面 ----------

    def _build_ui(self):
        box = ttk.LabelFrame(self, text="输入：3DMine 炮孔数据库报告")
        box.pack(fill="both", expand=True, **_PAD)

        self.listbox = tk.Listbox(box, activestyle="none")
        self.listbox.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        scroll = ttk.Scrollbar(box, orient="vertical", command=self.listbox.yview)
        scroll.pack(side="left", fill="y", pady=8)
        self.listbox.configure(yscrollcommand=scroll.set)

        btns = ttk.Frame(box)
        btns.pack(side="left", fill="y", padx=8, pady=8)
        for text, cmd in (("添加文件", self.add_files),
                          ("添加目录", self.add_dir),
                          ("移除选中", self.remove_selected),
                          ("上移", lambda: self.move(-1)),
                          ("下移", lambda: self.move(1)),
                          ("清空", self.clear)):
            ttk.Button(btns, text=text, command=cmd, width=10).pack(pady=3)

        out = ttk.LabelFrame(self, text="输出")
        out.pack(fill="x", **_PAD)
        ttk.Label(out, text="输出文件：").grid(row=0, column=0, sticky="w", padx=8, pady=4)
        ttk.Entry(out, textvariable=self.output_var).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(out, text="浏览", command=self.choose_output, width=8).grid(row=0, column=2, padx=8)
        ttk.Label(out, text="报告标题：").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        ttk.Entry(out, textvariable=self.title_var).grid(row=1, column=1, sticky="ew", padx=4)
        ttk.Label(out, text="（留空则取输出文件名）").grid(row=1, column=2, sticky="w", padx=8)
        out.columnconfigure(1, weight=1)

        opts = ttk.Frame(out)
        opts.grid(row=2, column=0, columnspan=3, sticky="w", padx=8, pady=4)
        ttk.Checkbutton(opts, text="在下方追加各源文件原始报告",
                        variable=self.appendix_var).pack(side="left", padx=(0, 16))
        ttk.Checkbutton(opts, text="小计/合计写公式",
                        variable=self.formula_var).pack(side="left")

        run_bar = ttk.Frame(self)
        run_bar.pack(fill="x", **_PAD)
        self.run_btn = ttk.Button(run_bar, text="开始汇总", command=self.run)
        self.run_btn.pack(side="left")
        ttk.Button(run_bar, text="打开输出目录", command=self.open_dir).pack(side="left", padx=8)

        self.log = tk.Text(self, height=9, state="disabled")
        self.log.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    # ---------- 交互 ----------

    def log_line(self, text: str):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def add_files(self):
        picked = filedialog.askopenfilenames(title="选择报告文件", filetypes=FILE_TYPES)
        for p in picked:
            if p not in self.files:
                self.files.append(p)
        self.refresh()

    def add_dir(self):
        d = filedialog.askdirectory(title="选择包含报告的目录")
        if not d:
            return
        found = find_input_files(directory=d, pattern="*.xls*")
        found.extend(find_input_files(directory=d, pattern="*.csv"))
        for p in found:
            if p not in self.files:
                self.files.append(p)
        self.refresh()

    def remove_selected(self):
        for i in reversed(self.listbox.curselection()):
            self.files.pop(i)
        self.refresh()

    def clear(self):
        self.files.clear()
        self.refresh()

    def move(self, delta):
        sel = self.listbox.curselection()
        if not sel:
            return
        i = sel[0]
        j = i + delta
        if j < 0 or j >= len(self.files):
            return
        self.files[i], self.files[j] = self.files[j], self.files[i]
        self.refresh()
        self.listbox.selection_set(j)

    def refresh(self):
        self.listbox.delete(0, "end")
        for f in self.files:
            self.listbox.insert("end", os.path.basename(f) + "   (" + os.path.dirname(f) + ")")

    def choose_output(self):
        p = filedialog.asksaveasfilename(title="保存为", defaultextension=".xlsx",
                                         filetypes=[("Excel 工作簿", "*.xlsx")])
        if p:
            self.output_var.set(p)
            if not self.title_var.get():
                self.title_var.set(os.path.splitext(os.path.basename(p))[0])

    def open_dir(self):
        path = self.output_var.get()
        if path and os.path.exists(path):
            os.startfile(os.path.dirname(os.path.abspath(path)))

    def run(self):
        if not self.files:
            messagebox.showwarning("提示", "请先添加输入文件")
            return
        output = self.output_var.get().strip()
        if not output:
            messagebox.showwarning("提示", "请先指定输出文件")
            return

        self.run_btn.configure(state="disabled")
        self.log_line("[开始] 共 %d 个输入文件" % len(self.files))

        options = MergeOptions(
            title=self.title_var.get().strip() or None,
            with_appendix=self.appendix_var.get(),
            use_formula=self.formula_var.get(),
        )
        files = sorted(self.files, key=natural_key_compat)

        def work():
            try:
                result = merge_reports(files, output, options)
            except Exception as exc:  # noqa: BLE001
                self.root.after(0, lambda: self._done(False, str(exc)))
                return
            self.root.after(0, lambda: self._done(True, result))

        threading.Thread(target=work, daemon=True).start()

    def _done(self, ok, payload):
        self.run_btn.configure(state="normal")
        if not ok:
            self.log_line("[失败] %s" % payload)
            messagebox.showerror("汇总失败", payload)
            return
        t = payload["total"]
        self.log_line("[输出] %s" % payload["output"])
        self.log_line("[汇总] 矿块明细 %d 条，品位档：%s"
                      % (payload["blocks"], " / ".join(payload["tiers"])))
        self.log_line("[合计] 体积 %.3f m3 | 重量 %.3f t | 平均品位 %.4f g/t | 金属量 %.3f 百克"
                      % (t["体积"], t["重量"], t["平均品位"] or 0, t["金属量"]))
        messagebox.showinfo("完成", "已生成：\n%s" % payload["output"])


# ==========================================================================
# 标签页二：单日数据并入总表
# ==========================================================================

class DailyTab(ttk.Frame):
    """选单日目录 → 自动识别六个文件 → 一键并入三份总表。"""

    def __init__(self, master):
        super().__init__(master)
        self.root = master.winfo_toplevel()

        self.day_var = tk.StringVar()
        self.master_var = tk.StringVar()
        self.skip_dup_var = tk.BooleanVar(value=True)
        self.backup_var = tk.BooleanVar(value=True)
        self.dry_run_var = tk.BooleanVar(value=False)
        self.appendix_var = tk.BooleanVar(value=False)

        self.plan = None
        self._build_ui()

    # ---------- 界面 ----------

    def _build_ui(self):
        src = ttk.LabelFrame(self, text="单日数据")
        src.pack(fill="x", **_PAD)
        ttk.Label(src, text="单日目录：").grid(row=0, column=0, sticky="w", padx=8, pady=4)
        ttk.Entry(src, textvariable=self.day_var).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(src, text="浏览", width=8,
                   command=self.choose_day_dir).grid(row=0, column=2, padx=8)

        ttk.Label(src, text="总表目录：").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        ttk.Entry(src, textvariable=self.master_var).grid(row=1, column=1, sticky="ew", padx=4)
        ttk.Button(src, text="浏览", width=8,
                   command=self.choose_master_dir).grid(row=1, column=2, padx=8)
        ttk.Label(src, text="（留空则从单日目录自动向上定位）",
                  foreground="#888888").grid(row=2, column=1, sticky="w", padx=4)
        src.columnconfigure(1, weight=1)

        pair_box = ttk.LabelFrame(self, text="识别到的文件对")
        pair_box.pack(fill="both", expand=False, **_PAD)
        self.tree = ttk.Treeview(pair_box, columns=("kind", "day", "master"),
                                 show="headings", height=3)
        for col, text, width in (("kind", "类型", 150), ("day", "单日文件", 300),
                                 ("master", "总表文件", 300)):
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor="w")
        self.tree.pack(fill="x", padx=8, pady=8)

        opts = ttk.Frame(self)
        opts.pack(fill="x", **_PAD)
        ttk.Checkbutton(opts, text="跳过已存在的工程号",
                        variable=self.skip_dup_var).pack(side="left", padx=(0, 14))
        ttk.Checkbutton(opts, text="写入前备份总表",
                        variable=self.backup_var).pack(side="left", padx=(0, 14))
        ttk.Checkbutton(opts, text="仅预演（不写盘）",
                        variable=self.dry_run_var).pack(side="left", padx=(0, 14))
        ttk.Checkbutton(opts, text="报告连同附录",
                        variable=self.appendix_var).pack(side="left")

        bar = ttk.Frame(self)
        bar.pack(fill="x", **_PAD)
        ttk.Button(bar, text="扫描识别", command=self.scan).pack(side="left")
        self.run_btn = ttk.Button(bar, text="开始并入", command=self.run)
        self.run_btn.pack(side="left", padx=8)
        ttk.Button(bar, text="还原备份", command=self.restore).pack(side="left")
        ttk.Button(bar, text="打开总表目录", command=self.open_master_dir).pack(side="left", padx=8)

        self.log = tk.Text(self, height=10, state="disabled")
        self.log.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    # ---------- 交互 ----------

    def log_line(self, text: str):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def choose_day_dir(self):
        d = filedialog.askdirectory(title="选择单日数据目录（如 …\\7、单日数据\\北部山头3940平台-1008）")
        if d:
            self.day_var.set(d)
            self.scan()

    def choose_master_dir(self):
        d = filedialog.askdirectory(title="选择总表目录（含 1、2、3、三份总表）")
        if d:
            self.master_var.set(d)
            self.scan()

    def _merge_options(self, dry_run=None):
        from src.daily_merge.pipeline import DailyMergeOptions

        return DailyMergeOptions(
            day_dir=self.day_var.get().strip() or None,
            master_dir=self.master_var.get().strip() or None,
            skip_duplicates=self.skip_dup_var.get(),
            with_report_appendix=self.appendix_var.get(),
            backup=self.backup_var.get(),
            dry_run=self.dry_run_var.get() if dry_run is None else dry_run,
        )

    def scan(self):
        from src.daily_merge.pipeline import resolve_plan

        self.tree.delete(*self.tree.get_children())
        day_dir = self.day_var.get().strip()
        if not day_dir:
            self.log_line("[提示] 请先选择单日数据目录")
            return None
        try:
            plan = resolve_plan(self._merge_options())
        except Exception as exc:  # noqa: BLE001
            self.log_line("[失败] %s" % exc)
            self.plan = None
            return None

        self.plan = plan
        from src.daily_merge.schema import KIND_LABELS, KINDS

        for kind in KINDS:
            src, dst = plan.src.get(kind), plan.dst.get(kind)
            self.tree.insert("", "end", values=(
                KIND_LABELS[kind],
                os.path.basename(src) if src else "— 未找到 —",
                os.path.basename(dst) if dst else "— 未找到 —",
            ))
        self.log_line("[识别] 日期代号 %s；总表目录 %s"
                      % (plan.day_code or "未识别", plan.master_dir or "未定位"))
        if plan.missing:
            for item in plan.missing:
                self.log_line("[缺口] %s" % item)
        else:
            self.log_line("[识别] 三对文件齐备 ✓")
        return plan

    def run(self):
        from src.daily_merge.pipeline import run

        plan = self.scan()
        if plan is None or not plan.executable:
            messagebox.showwarning("提示", "没有找到可执行的文件对，请检查目录。")
            return

        self.run_btn.configure(state="disabled")
        options = self._merge_options()

        def work():
            try:
                report = run(options)
            except Exception as exc:  # noqa: BLE001
                self.root.after(0, lambda: self._done(False, str(exc)))
                return
            self.root.after(0, lambda: self._done(True, report))

        threading.Thread(target=work, daemon=True).start()

    def _done(self, ok, payload):
        from src.daily_merge.pipeline import summarize

        self.run_btn.configure(state="normal")
        if not ok:
            self.log_line("[失败] %s" % payload)
            messagebox.showerror("并入失败", payload)
            return
        for line in summarize(payload):
            self.log_line(line)
        if payload["errors"]:
            messagebox.showwarning("部分失败", "有 %d 类数据未完成，请看日志。" % len(payload["errors"]))
        else:
            messagebox.showinfo("完成", "已并入 %d 类数据到总表。" % len(payload["results"]))

    def restore(self):
        from src.daily_merge.pipeline import restore

        master_dir = self.master_var.get().strip()
        if not master_dir:
            master_dir = (self.plan.master_dir if self.plan else "") or ""
        if not master_dir:
            messagebox.showwarning("提示", "请先指定总表目录。")
            return
        if not messagebox.askyesno("确认还原", "将从 *_并入*.bak 还原三份总表，\n"
                                              "当前文件会另存为 *_还原前<时间>.bak。\n\n继续？"):
            return
        try:
            done = restore(master_dir, None)
        except Exception as exc:  # noqa: BLE001
            self.log_line("[失败] %s" % exc)
            messagebox.showerror("还原失败", str(exc))
            return
        if not done:
            self.log_line("[提示] 没有找到可用的备份。")
            return
        for kind, line in done.items():
            self.log_line("[还原] %s" % line)

    def open_master_dir(self):
        path = self.master_var.get().strip() or (self.plan.master_dir if self.plan else "")
        if path and os.path.isdir(path):
            os.startfile(path)
        else:
            messagebox.showwarning("提示", "还没有可打开的总表目录。")


# ==========================================================================
# 主窗口
# ==========================================================================

class App:
    def __init__(self, root: tk.Tk, tab: str = "report"):
        self.root = root
        root.title("炮孔数据工具")
        root.geometry("880x660")
        root.minsize(760, 560)

        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True, padx=6, pady=6)

        self.report_tab = ReportTab(notebook)
        self.daily_tab = DailyTab(notebook)
        notebook.add(self.report_tab, text=" 炮孔数据报告汇总 ")
        notebook.add(self.daily_tab, text=" 单日数据并入总表 ")
        notebook.select(1 if tab == "daily" else 0)


def launch(tab: str = "report") -> int:
    set_app_user_model_id()      # 必须在 Tk() 之前，否则任务栏仍显示 python 图标
    root = tk.Tk()
    set_window_icon(root)
    App(root, tab=tab)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(launch())
