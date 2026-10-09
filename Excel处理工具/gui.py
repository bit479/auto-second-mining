"""图形界面：选文件 → 定输出 → 一键汇总。

不带命令行参数运行 main.py 会自动打开本界面。
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


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("炮孔数据报告汇总工具")
        root.geometry("760x560")
        root.minsize(680, 480)

        self.files: list[str] = []
        self.output_var = tk.StringVar()
        self.title_var = tk.StringVar()
        self.appendix_var = tk.BooleanVar(value=True)
        self.formula_var = tk.BooleanVar(value=True)

        self._build_ui()

    # ---------- 界面 ----------

    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}

        # 输入文件区
        box = ttk.LabelFrame(self.root, text="输入：3DMine 炮孔数据库报告")
        box.pack(fill="both", expand=True, **pad)

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

        # 输出区
        out = ttk.LabelFrame(self.root, text="输出")
        out.pack(fill="x", **pad)
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

        # 执行区
        run_bar = ttk.Frame(self.root)
        run_bar.pack(fill="x", **pad)
        self.run_btn = ttk.Button(run_bar, text="开始汇总", command=self.run)
        self.run_btn.pack(side="left")
        ttk.Button(run_bar, text="打开输出目录", command=self.open_dir).pack(side="left", padx=8)

        self.log = tk.Text(self.root, height=10, state="disabled")
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


def launch() -> int:
    set_app_user_model_id()      # 必须在 Tk() 之前，否则任务栏仍显示 python 图标
    root = tk.Tk()
    set_window_icon(root)
    App(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(launch())
