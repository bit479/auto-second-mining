"""Excel 差异对比工具 —— 图形界面 (tkinter)。

支持: 选文件A/B、选输出路径、一键对比、日志显示、完成后打开报告。
新增: 可直接把 Excel/CSV 文件拖入窗口(自动填入 A/B)；应用图标(标题栏/任务栏/界面)。
无参数运行 main.py 即进入本界面。
"""
from __future__ import annotations

import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app_icon
import dragdrop


def _ensure_openpyxl():
    try:
        import openpyxl  # noqa: F401
        return True
    except ImportError:
        pass
    try:
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "openpyxl"],
                       check=True)
        import openpyxl  # noqa: F401
        return True
    except Exception:
        return False


def _import_core():
    from compare import compare_workbooks, diff_count
    from reader import read_workbook
    from writer import write_report
    return compare_workbooks, diff_count, read_workbook, write_report


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("Excel 差异对比工具")
        root.geometry("700x500")
        try:
            root.call("tk", "scaling", 1.25)
        except Exception:
            pass

        frm = ttk.Frame(root, padding=12)
        frm.pack(fill="both", expand=True)

        self._build_header(frm)

        ttk.Label(
            frm,
            text="提示：可直接把 Excel / CSV 文件拖入本窗口，自动填入 A / B。",
            foreground="#667085").grid(row=1, column=0, sticky="w", pady=(0, 6))

        in_frm = ttk.Frame(frm)
        in_frm.grid(row=2, column=0, sticky="ew")

        self.var_a = tk.StringVar()
        self.var_b = tk.StringVar()
        self.var_out = tk.StringVar()

        self._row(in_frm, 0, "文件 A:", self.var_a, True)
        self._row(in_frm, 1, "文件 B:", self.var_b, True)
        self._row(in_frm, 2, "输出报告:", self.var_out, False)

        btn_frm = ttk.Frame(frm)
        btn_frm.grid(row=3, column=0, columnspan=3, pady=8)
        ttk.Button(btn_frm, text="开始对比", command=self.on_run).pack(side="left", padx=4)
        ttk.Button(btn_frm, text="打开报告", command=self.on_open).pack(side="left", padx=4)
        ttk.Button(btn_frm, text="退出", command=root.destroy).pack(side="left", padx=4)

        self.log = scrolledtext.ScrolledText(frm, height=16, state="disabled")
        self.log.grid(row=4, column=0, columnspan=3, sticky="nsew", pady=(4, 0))
        frm.rowconfigure(4, weight=1)

        self._open_path = None

    def _build_header(self, parent):
        header = ttk.Frame(parent)
        header.grid(row=0, column=0, sticky="w", pady=(0, 6))
        logo = self._load_logo()
        if logo is not None:
            ttk.Label(header, image=logo).pack(side="left", padx=(0, 8))
            self._logo = logo  # 防止被 GC
        ttk.Label(header, text="Excel 差异对比工具",
                  font=("Microsoft YaHei", 14, "bold")).pack(side="left")

    def _load_logo(self):
        path = app_icon.get_logo_path()
        if not path:
            return None
        try:
            from PIL import Image, ImageTk
            im = Image.open(path).convert("RGBA").resize((40, 40), Image.LANCZOS)
            return ImageTk.PhotoImage(im)
        except Exception:
            return None

    def _row(self, parent, r, label, var, is_input):
        ttk.Label(parent, text=label).grid(row=r, column=0, sticky="e", padx=4, pady=3)
        ttk.Entry(parent, textvariable=var, width=60).grid(row=r, column=1, padx=4, pady=3)
        if is_input:
            ttk.Button(parent, text="浏览...",
                       command=lambda v=var: self._pick(v)).grid(
                row=r, column=2, padx=4, pady=3)
        else:
            ttk.Button(parent, text="浏览...",
                       command=lambda v=var: self._pick_out(v)).grid(
                row=r, column=2, padx=4, pady=3)

    def _auto_out(self, p):
        if not self.var_out.get():
            base = os.path.splitext(os.path.basename(p))[0]
            self.var_out.set(os.path.join(os.path.dirname(p), f"对比报告_{base}.xlsx"))

    def _pick(self, var):
        p = filedialog.askopenfilename(
            title="选择 Excel 文件",
            filetypes=[("Excel", "*.xlsx *.xlsm *.xls"), ("CSV", "*.csv"), ("全部", "*.*")])
        if p:
            var.set(p)
            self._auto_out(p)

    def _pick_out(self, var):
        p = filedialog.asksaveasfilename(
            title="保存报告", defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")])
        if p:
            var.set(p)

    def _on_drop(self, files):
        """拖入文件时自动填入 A / B。"""
        excels = dragdrop.filter_excel(files)
        if not excels:
            self._log("提示: 拖入的不是 Excel/CSV 文件，已忽略。")
            return
        a = self.var_a.get().strip()
        b = self.var_b.get().strip()
        if not a:
            self.var_a.set(excels[0])
            self._auto_out(excels[0])
            if len(excels) > 1 and not b:
                self.var_b.set(excels[1])
        elif not b:
            self.var_b.set(excels[0])
        else:
            # 两框都已填: 替换 A，若拖入两个则再替换 B；否则保持 B 不变
            self.var_a.set(excels[0])
            self._auto_out(excels[0])
            if len(excels) > 1:
                self.var_b.set(excels[1])
        self._log(f"已拖入 {len(excels)} 个文件，已自动填入 A / B。")

    def _log(self, msg):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.configure(state="disabled")
        self.log.see("end")
        self.root.update_idletasks()

    def on_run(self):
        path_a, path_b, out = self.var_a.get(), self.var_b.get(), self.var_out.get()
        if not path_a or not path_b:
            messagebox.showwarning("提示", "请先选择文件 A 和文件 B（也可直接拖入窗口）。")
            return
        if not out:
            messagebox.showwarning("提示", "请指定输出报告路径。")
            return
        if not _ensure_openpyxl():
            messagebox.showerror("缺少依赖", "未安装 openpyxl，请先执行: pip install openpyxl")
            return
        threading.Thread(target=self._worker, args=(path_a, path_b, out), daemon=True).start()

    def _worker(self, path_a, path_b, out):
        try:
            self._log(f"读取文件A: {path_a}")
            compare_workbooks, diff_count, read_workbook, write_report = _import_core()
            wb_a = read_workbook(path_a)
            self._log(f"读取文件B: {path_b}")
            wb_b = read_workbook(path_b)
            self._log("逐单元格对比中...")
            result = compare_workbooks(wb_a, wb_b)
            write_report(result, path_a, path_b, out, source_a=wb_a, source_b=wb_b)
            t = result["totals"]
            n = diff_count(result)
            self._log("-" * 40)
            self._log(f"比较非空单元格: {t['compared']}  相等: {t['equal']}")
            self._log(f"差异合计: {n}  (修改 {t['changed']} / 仅A {t['only_a']} / 仅B {t['only_b']})")
            self._log(f"报告已生成: {out}")
            self._open_path = out
            self.root.after(0, lambda: messagebox.showinfo(
                "完成", f"对比完成，差异 {n} 处。\n报告: {out}"))
        except Exception as e:
            self._log(f"运行出错: {e}")
            self.root.after(0, lambda: messagebox.showerror("运行出错", str(e)))

    def on_open(self):
        if self._open_path and os.path.exists(self._open_path):
            os.startfile(self._open_path)
        else:
            messagebox.showinfo("提示", "还没有生成报告，请先「开始对比」。")


def main():
    try:
        import tkinter  # 提前探测
    except ImportError:
        messagebox.showerror("环境缺失", "当前 Python 没有 tkinter，无法启动图形界面。\n"
                                         "请使用带 tkinter 的 Python（如官方安装版）。")
        sys.exit(1)
    app_icon.set_app_user_model_id()  # 必须在 Tk() 之前
    root = tk.Tk()
    app = App(root)
    app_icon.set_window_icon(root)   # 标题栏左上角 + 任务栏图标
    try:
        dragdrop.enable_drop(root, app._on_drop)
    except Exception:
        pass
    root.mainloop()


if __name__ == "__main__":
    main()
