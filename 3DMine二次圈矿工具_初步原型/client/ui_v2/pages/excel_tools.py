# -*- coding: utf-8 -*-
"""Excel 数据工具：炮孔报告汇总 + 单日数据并入总表（调用原有 excel_tools 业务函数）。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QHBoxLayout, QLabel, QListWidget, QMessageBox,
    QPushButton, QTabWidget, QVBoxLayout, QWidget,
)

from ..components import widgets as W
from ..services import config, paths
from .base import Page


class ExcelToolsPage(Page):
    TITLE = "Excel 数据工具"
    SUB = "报告汇总 / 单日并入，口径与原工具一致"

    def _build(self) -> None:
        self.runner.finished.connect(self._on_finished)
        tabs = QTabWidget()
        tabs.addTab(ReportTab(self), "炮孔报告汇总")
        tabs.addTab(DailyTab(self), "单日数据并入总表")
        self.add(tabs)

        lc = W.Card("日志", "")
        self.log = W.LogView()
        self.log.setMinimumHeight(180)
        lc.add(self.log)
        self.add(lc)
        self.runner.log.connect(self._log)

    def _log(self, tid: str, line: str) -> None:
        if tid in (getattr(self, "_tid", None),):
            self.log.append_line(line)

    def run_script(self, name: str, script: str, args: list[str], key: str) -> None:
        self.log.append_line("== %s ==" % name)
        self._tid = self.runner.run(name, script, args, key=key, cwd=str(paths.bundle_root()))

    def _on_finished(self, tid: str, code: int) -> None:
        if tid == getattr(self, "_tid", None):
            self.log.append_line("[结束] 退出码 %s" % code)


class ReportTab(QWidget):
    """多份 3DMine 报告 → 一份炮孔数据报告。"""

    def __init__(self, page: ExcelToolsPage):
        super().__init__()
        self.page = page
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(12)

        card = W.Card("输入报告", "顺序会影响同档内体号顺序（可上移/下移）")
        self.listw = QListWidget()
        self.listw.setMinimumHeight(150)
        self.listw.setAlternatingRowColors(True)
        self.listw.setStyleSheet(
            "QListWidget{background:#FFFFFF;border:1px solid %s;border-radius:8px;}"
            "QListWidget::item{padding:5px 8px;}" % "#E3E8EE")
        card.add(self.listw)
        bar = QHBoxLayout()
        bar.setSpacing(6)
        bar.addWidget(W.icon_button("plus", "添加文件", on_click=self.add_files))
        bar.addWidget(W.icon_button("folder", "添加目录", on_click=self.add_dir))
        bar.addWidget(W.icon_button("x", "移除选中", kind="ghost", on_click=self.remove))
        bar.addWidget(W.icon_button("chevron", "上移", kind="ghost", on_click=lambda: self.move(-1)))
        bar.addWidget(W.icon_button("chevron", "下移", kind="ghost", on_click=lambda: self.move(1)))
        bar.addStretch(1)
        self.lb_count = QLabel("0 个文件")
        self.lb_count.setObjectName("muted")
        bar.addWidget(self.lb_count)
        card.add(bar)
        lay.addWidget(card)

        opt = W.Card("汇总设置", "")
        grid = QHBoxLayout()
        grid.setSpacing(12)
        grid.addWidget(_lab("汇总方式"))
        self.cb_mode = QComboBox()
        self.cb_mode.addItem("按每个文件的「总计」行汇总（新口径）", "total")
        self.cb_mode.addItem("按明细行汇总（旧口径）", "detail")
        grid.addWidget(self.cb_mode)
        grid.addWidget(_lab("品位分级"))
        self.cb_grade = QComboBox()
        for key, name in config.grade_choices():
            self.cb_grade.addItem(name, key)
        grid.addWidget(self.cb_grade)
        grid.addStretch(1)
        opt.add(grid)

        self.row_out = W.FileRow("输出 xlsx", "留空 = 第一个输入文件同目录，按矿名+平台+日期命名",
                                 mode="save", file_filter="Excel (*.xlsx)", must_exist=False)
        opt.add(self.row_out)
        self.row_title = W.FileRow("报告标题", "留空 = 按「矿名+平台+日期」推断",
                                   must_exist=False, browse=False)
        self.row_title.edit.setReadOnly(False)
        opt.add(self.row_title)
        chk = QHBoxLayout()
        chk.setSpacing(16)
        self.ck_appendix = W.CheckRow("在下方追加各源文件原始报告", True)
        self.ck_formula = W.CheckRow("小计/合计写公式", True)
        chk.addWidget(self.ck_appendix)
        chk.addWidget(self.ck_formula)
        chk.addStretch(1)
        opt.add(chk)
        lay.addWidget(opt)

        run = QHBoxLayout()
        run.setSpacing(8)
        b = W.icon_button("play", "开始汇总", kind="primary", on_click=self.run)
        b.setMinimumHeight(36)
        run.addWidget(b)
        run.addStretch(1)
        self.lb_state = QLabel("")
        self.lb_state.setObjectName("muted")
        run.addWidget(self.lb_state)
        lay.addLayout(run)
        lay.addStretch(1)

    # ---- 列表操作 ----

    def _refresh(self) -> None:
        n = self.listw.count()
        self.lb_count.setText("%d 个文件" % n)

    def add_files(self) -> None:
        fs, _ = QFileDialog.getOpenFileNames(self, "选择 3DMine 报告", "",
                                             "Excel (*.xls *.xlsx *.csv)")
        for f in fs:
            self.listw.addItem(f)
        self._refresh()

    def add_dir(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "选择包含报告的目录")
        if not d:
            return
        for p in sorted(Path(d).glob("*.xls*")):
            self.listw.addItem(str(p))
        self._refresh()

    def remove(self) -> None:
        for item in self.listw.selectedItems():
            self.listw.takeItem(self.listw.row(item))
        self._refresh()

    def move(self, delta: int) -> None:
        row = self.listw.currentRow()
        if row < 0:
            return
        new = row + delta
        if 0 <= new < self.listw.count():
            item = self.listw.takeItem(row)
            self.listw.insertItem(new, item)
            self.listw.setCurrentRow(new)

    # ---- 执行 ----

    def run(self) -> None:
        files = [self.listw.item(i).text() for i in range(self.listw.count())]
        if not files:
            QMessageBox.information(self, "汇总", "先添加要汇总的报告。")
            return
        out = self.row_out.value()
        args: list[str] = ["-i"] + files + ["--mode", self.cb_mode.currentData()]
        if out:
            args += ["-o", out]
        title = self.row_title.value()
        if title:
            args += ["-t", title]
        grade = self.cb_grade.currentData()
        if grade and grade != "auto":
            args += ["--grades", grade]
        if not self.ck_appendix.isChecked():
            args.append("--no-appendix")
        if not self.ck_formula.isChecked():
            args.append("--values")
        self.lb_state.setText("正在汇总…")
        self.page.run_script("炮孔报告汇总", "excel_tools/main.py", args, "xl_report")
        self.page.log.append_line("[提示] 输出目录：%s" % (Path(out).parent if out else "输入文件同目录"))


class DailyTab(QWidget):
    """单日数据并入年度总表（判重 / 备份 / 预演 / 还原 / 矿块图同步）。"""

    def __init__(self, page: ExcelToolsPage):
        super().__init__()
        self.page = page
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(12)

        card = W.Card("目录", "单日目录里应有 1、xls / 2、mdb / 报告 / 5、矿块图")
        self.row_day = W.FileRow("单日数据目录", "如 …\\7、单日数据\\北部山头3940平台-1008",
                                 mode="dir", title="选择单日目录")
        card.add(self.row_day)
        self.row_master = W.FileRow("总表目录", "留空 = 从单日目录向上自动定位",
                                    mode="dir", title="选择总表目录", must_exist=False)
        card.add(self.row_master)
        lay.addWidget(card)

        opt = W.Card("并入选项", "默认最安全：判重 + 备份 + 矿块图同步")
        row = QHBoxLayout()
        row.setSpacing(16)
        self.ck_dup = W.CheckRow("跳过已存在的工程号", True)
        self.ck_backup = W.CheckRow("写入前备份总表", True)
        self.ck_map = W.CheckRow("同步二次圈矿矿块图（去前缀复制进 6、）", True)
        for w in (self.ck_dup, self.ck_backup, self.ck_map):
            row.addWidget(w)
        row.addStretch(1)
        opt.add(row)
        lay.addWidget(opt)

        run = QHBoxLayout()
        run.setSpacing(8)
        self.btn_dry = W.icon_button("play", "预演（不写盘）", on_click=lambda: self.run(True))
        self.btn_dry.setMinimumHeight(36)
        run.addWidget(self.btn_dry)
        self.btn_real = W.icon_button("upload", "正式并入", kind="primary", on_click=lambda: self.run(False))
        self.btn_real.setMinimumHeight(36)
        run.addWidget(self.btn_real)
        self.btn_restore = W.icon_button("refresh", "还原备份", kind="ghost", on_click=self.restore)
        run.addWidget(self.btn_restore)
        run.addStretch(1)
        self.lb_state = QLabel("")
        self.lb_state.setObjectName("muted")
        run.addWidget(self.lb_state)
        lay.addLayout(run)

        self.banner = W.Banner(
            "正式并入会写入三份年度总表（xls / mdb / 综合报告），并可能覆盖「6、矿块图」里的同名图。"
            "建议先跑一次「预演」核对计划。", "warn")
        lay.addWidget(self.banner)
        lay.addStretch(1)

    def _args(self, dry: bool) -> list[str] | None:
        day = self.row_day.value()
        if not Path(day).is_dir():
            QMessageBox.information(self, "并入总表", "先选单日数据目录。")
            return None
        args = ["--daily", "--day-dir", day]
        if self.row_master.value():
            args += ["--master-dir", self.row_master.value()]
        if not self.ck_dup.isChecked():
            args.append("--allow-duplicates")
        if not self.ck_backup.isChecked():
            args.append("--no-backup")
        if not self.ck_map.isChecked():
            args.append("--no-map")
        if dry:
            args.append("--dry-run")
        return args

    def run(self, dry: bool) -> None:
        args = self._args(dry)
        if args is None:
            return
        if not dry:
            ok = QMessageBox.question(
                self, "确认正式并入",
                "确定把 %s\n\n并入年度总表吗？\n\n"
                "· 三份总表会先备份成 <原名>_并入<日>.bak\n"
                "· 按工程号判重，重复运行安全\n"
                "· 矿块图同名同内容跳过，不同则先备份再覆盖" % self.row_day.value(),
                QMessageBox.Yes | QMessageBox.No)
            if ok != QMessageBox.Yes:
                return
        self.lb_state.setText("正在%s…" % ("预演" if dry else "并入"))
        self.page.run_script("单日数据并入总表（%s）" % ("预演" if dry else "正式"),
                             "excel_tools/main.py", args, "xl_daily")

    def restore(self) -> None:
        master = self.row_master.value() or self.row_day.value()
        if not master:
            QMessageBox.information(self, "还原", "请先给总表目录（或单日目录）。")
            return
        ok = QMessageBox.question(
            self, "确认还原",
            "将从 *_并入*.bak 还原三份总表；\n当前文件会另存为 *_还原前<时间>.bak。\n\n继续？",
            QMessageBox.Yes | QMessageBox.No)
        if ok != QMessageBox.Yes:
            return
        args = ["--daily", "--restore", "--master-dir", master]
        self.page.run_script("还原总表备份", "excel_tools/main.py", args, "xl_restore")
        self.lb_state.setText("正在还原…")


def _lab(text: str) -> QLabel:
    l = QLabel(text)
    l.setObjectName("fieldLabel")
    return l
