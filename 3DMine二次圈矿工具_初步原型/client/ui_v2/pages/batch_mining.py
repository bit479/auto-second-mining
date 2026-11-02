# -*- coding: utf-8 -*-
"""批量处理：扫目录 → 勾选 → 队列执行 → 单个日志 / 重试 / 打开成果。"""

from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QHBoxLayout, QLabel, QMessageBox, QSplitter, QVBoxLayout, QWidget,
)

from .. import theme
from ..components import widgets as W
from ..services import files, paths
from .base import Page


class BatchMiningPage(Page):
    TITLE = "批量处理"
    SUB = "选父目录 → 勾选炮区 → 逐个圈矿（原批量+汇总保留）"

    def __init__(self, parent=None):
        self.tasks: list[files.DayTask] = []
        self.queue: list[int] = []
        self.current: int | None = None
        self._running = False
        super().__init__(parent)

    def _build(self) -> None:
        self.runner.finished.connect(self._on_finished)

        card = W.Card()
        card.add(W.SectionTitle("1", "目录", ""))
        self.row_parent = W.FileRow("单日数据父目录", "如 …\\7、单日数据", mode="dir",
                                    title="选择父目录", must_exist=True)
        card.add(self.row_parent)
        self.row_comp = W.FileRow("平台综合图 DWG", "整个批次共用的综合图",
                                  file_filter="DWG (*.dwg)", title="选择综合图")
        card.add(self.row_comp)

        bar = QHBoxLayout()
        bar.setSpacing(8)
        bar.addWidget(W.icon_button("refresh", "扫描炮区", kind="primary", on_click=self.scan))
        self.ck_all = QCheckBox("全选")
        self.ck_all.setChecked(True)
        self.ck_all.stateChanged.connect(self._toggle_all)
        bar.addWidget(self.ck_all)
        bar.addWidget(W.icon_button("folder", "打开父目录", kind="ghost",
                                    on_click=lambda: paths.open_path(self.row_parent.value())))
        bar.addStretch(1)
        self.lb_scan = QLabel("还没有扫描。")
        self.lb_scan.setObjectName("muted")
        bar.addWidget(self.lb_scan)
        card.add(bar)
        self.add(card)

        run = QHBoxLayout()
        run.setSpacing(8)
        self.btn_run = W.icon_button("play", "开始批量圈矿", kind="primary", on_click=self.run_queue)
        self.btn_run.setMinimumHeight(38)
        run.addWidget(self.btn_run)
        self.btn_orig = W.icon_button("layers", "跑原批量流程（含汇总表）", on_click=self.run_original)
        run.addWidget(self.btn_orig)
        self.btn_cancel = W.icon_button("x", "中止队列", on_click=self.cancel_queue)
        self.btn_cancel.setEnabled(False)
        run.addWidget(self.btn_cancel)
        self.btn_retry = W.icon_button("refresh", "重试失败项", kind="ghost", on_click=self.retry_failed)
        run.addWidget(self.btn_retry)
        run.addStretch(1)
        self.lb_progress = QLabel("0 / 0")
        self.lb_progress.setObjectName("muted")
        run.addWidget(self.lb_progress)
        self.add(run)

        split = QSplitter(Qt.Vertical)
        split.setChildrenCollapsible(False)

        tcard = W.Card("任务列表", "勾选要跑的行；状态实时刷新")
        self.table = W.make_table(
            ["", "平台", "炮区", "数据库文件", "圈矿模式", "状态", "开始", "完成", "说明"],
            [34, 70, 70, 260, 90, 80, 70, 70, 240], 260)
        self.table.itemChanged.connect(self._on_item_changed)
        tcard.add(self.table)
        split.addWidget(tcard)

        lcard = W.Card("任务日志", "点一行看它的日志")
        self.log = W.LogView()
        self.log.setMinimumHeight(150)
        lcard.add(self.log)
        split.addWidget(lcard)
        split.setSizes([420, 200])
        self.add(split)

        self._logs: dict[int, list[str]] = {}
        self.runner.log.connect(self._collect_log)

    # ------------------------------------------------------------ 扫描

    def scan(self) -> None:
        parent = Path(self.row_parent.value())
        if not parent.is_dir():
            QMessageBox.information(self, "扫描", "先选一个存在的父目录。")
            return
        self.tasks = files.scan_day_folders(parent)
        self._fill_table()
        self.lb_scan.setText("扫到 %d 个炮区" % len(self.tasks))
        if self.tasks and not self.row_comp.value():
            for t in self.tasks:
                if t.composite:
                    self.row_comp.set_value(str(t.composite))
                    break

    def _fill_table(self) -> None:
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        for i, t in enumerate(self.tasks):
            r = self.table.rowCount()
            self.table.insertRow(r)
            chk = W.cell("")
            chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk.setCheckState(Qt.Checked)
            chk.setData(Qt.UserRole, i)
            self.table.setItem(r, 0, chk)
            self.table.setItem(r, 1, W.cell(t.platform))
            self.table.setItem(r, 2, W.cell(t.date))
            self.table.setItem(r, 3, W.cell(t.xls.name if t.xls else "—",
                                            theme.TEXT_MUTED if not t.xls else None))
            self.table.setItem(r, 4, W.cell("自动圈矿"))
            self.table.setItem(r, 5, self._status_item(t.status))
            self.table.setItem(r, 6, W.cell(t.started, theme.TEXT_MUTED))
            self.table.setItem(r, 7, W.cell(t.ended, theme.TEXT_MUTED))
            self.table.setItem(r, 8, W.cell(t.message, theme.TEXT_MUTED))
        self.table.blockSignals(False)
        self.lb_progress.setText("0 / %d" % len(self.tasks))

    def _status_item(self, status: str):
        fg, _bg = theme.status_color(status)
        return W.cell(status, fg, True)

    def _toggle_all(self, state) -> None:
        checked = Qt.Checked if state == Qt.Checked else Qt.Unchecked
        self.table.blockSignals(True)
        for r in range(self.table.rowCount()):
            self.table.item(r, 0).setCheckState(checked)
        self.table.blockSignals(False)

    def _on_item_changed(self, item) -> None:
        if item.column() != 0:
            return
        self.table.blockSignals(True)
        i = item.data(Qt.UserRole)
        if isinstance(i, int) and 0 <= i < len(self.tasks):
            self.tasks[i].status = "待执行" if item.checkState() == Qt.Checked else "跳过"
            self.table.setItem(item.row(), 5, self._status_item(self.tasks[i].status))
        self.table.blockSignals(False)

    # ------------------------------------------------------------ 执行（队列）

    def run_queue(self) -> None:
        if self._running:
            QMessageBox.information(self, "正在执行", "队列还在跑，先等它结束或点「中止队列」。")
            return
        if not self.tasks:
            self.scan()
        if not self.tasks:
            return
        comp = self.row_comp.value()
        if not comp or not Path(comp).exists():
            QMessageBox.warning(self, "缺少综合图", "批量需要指定综合图 DWG。")
            return
        self.queue = [i for i, t in enumerate(self.tasks)
                      if self.table.item(i, 0).checkState() == Qt.Checked and t.xls]
        if not self.queue:
            QMessageBox.information(self, "队列", "没有勾选任何炮区。")
            return
        self._running = True
        self.btn_run.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self._done_count = 0
        self._next()

    def _next(self) -> None:
        if not self.queue:
            self._running = False
            self.btn_run.setEnabled(True)
            self.btn_cancel.setEnabled(False)
            self.lb_progress.setText("%d / %d 完成" % (self._done_count, self._done_count))
            self.lb_scan.setText("批量结束：%d 个炮区" % self._done_count)
            self.ctx.changed.emit()
            return
        idx = self.queue.pop(0)
        self.current = idx
        t = self.tasks[idx]
        plat, date = t.platform, t.date
        t.status = "运行中"
        t.started = time.strftime("%H:%M:%S")
        self._refresh_row(idx)
        out = t.folder / ("二次圈矿成果_%s_%s" % (plat or "?", date or "?"))
        t.message = str(out)
        self.log.clear()
        self.log.append_line("== %s ==" % t.name)
        args = [str(t.xls), plat, date, str(out), self.row_comp.value()]
        section = self.ctx.section
        if section and section != "auto":
            args += ["--grades", section]
        self._tid = self.runner.run("批量：%s" % t.name, "core/run_strip.py", args,
                                    key="run_strip", cwd=str(paths.bundle_root()))
        self.lb_progress.setText("%d / %d" % (self._done_count + 1, self._done_count + len(self.queue) + 1))

    def _on_finished(self, tid: str, code: int) -> None:
        if tid != getattr(self, "_tid", None):
            return
        idx = self.current
        if idx is None:
            return
        t = self.tasks[idx]
        t.ended = time.strftime("%H:%M:%S")
        t.status = "完成" if code == 0 else "失败"
        if code != 0:
            t.message = "退出码 %s（详见日志）" % code
        self._refresh_row(idx)
        self.ctx.record("批量 %s" % t.name, t.status, t.message, str(t.folder))
        self._done_count += 1
        self.current = None
        self._next()

    def _refresh_row(self, i: int) -> None:
        self.table.blockSignals(True)
        row = i
        if 0 <= row < self.table.rowCount():
            self.table.setItem(row, 5, self._status_item(self.tasks[i].status))
            self.table.setItem(row, 6, W.cell(self.tasks[i].started, theme.TEXT_MUTED))
            self.table.setItem(row, 7, W.cell(self.tasks[i].ended, theme.TEXT_MUTED))
            self.table.setItem(row, 8, W.cell(self.tasks[i].message, theme.TEXT_MUTED))
        self.table.blockSignals(False)

    def cancel_queue(self) -> None:
        self.queue.clear()
        if getattr(self, "_tid", None):
            self.runner.cancel(self._tid)
        self._running = False
        self.btn_run.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.lb_scan.setText("已中止；已开始的炮区会跑完当前这一步")

    def retry_failed(self) -> None:
        failed = [i for i, t in enumerate(self.tasks) if t.status == "失败"]
        if not failed:
            QMessageBox.information(self, "重试", "没有失败的任务。")
            return
        for i in failed:
            self.tasks[i].status = "待执行"
            self.table.item(i, 0).setCheckState(Qt.Checked)
            self._refresh_row(i)
        self.run_queue()

    # ------------------------------------------------------------ 原批量流程

    def run_original(self) -> None:
        parent = self.row_parent.value()
        comp = self.row_comp.value()
        if not Path(parent).is_dir():
            QMessageBox.information(self, "批量", "先选父目录。")
            return
        if not Path(comp).is_file():
            QMessageBox.warning(self, "缺少综合图", "请指定综合图 DWG。")
            return
        out = str(Path(parent) / "_批量汇总")
        Path(out).mkdir(parents=True, exist_ok=True)
        self.log.clear()
        args = [parent, comp, out]
        if self.ctx.section != "auto":
            args += ["--grades", self.ctx.section]
        self._tid_orig = self.runner.run("原批量流程（含汇总表）", "core/run_batch.py", args,
                                         key="run_batch", cwd=str(paths.bundle_root()))
        self.lb_scan.setText("正在跑原批量流程，产物在 %s" % out)

    # ------------------------------------------------------------ 日志

    def _collect_log(self, tid: str, line: str) -> None:
        if tid in (getattr(self, "_tid", None), getattr(self, "_tid_orig", None)):
            self.log.append_line(line)

    def on_show(self) -> None:
        if not self.row_parent.value() and self.ctx.xls:
            self.row_parent.set_value(str(Path(self.ctx.xls).parent.parent))
