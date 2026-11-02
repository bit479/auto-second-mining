# -*- coding: utf-8 -*-
"""工作台首页：最近任务、最近成果、项目信息、快捷入口、品位分级图例。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from .. import icons, theme
from ..components import widgets as W
from ..services import config, paths
from .base import Page


def _short_time(text: str) -> str:
    """2026-11-02 17:49 这类时间，表格里只留 11-02 17:49（列宽有限）。"""
    t = str(text or "").strip()
    if len(t) >= 16 and t[4] == "-" and t[7] == "-":
        return t[5:16]
    return t


QUICK_ACTIONS = [
    ("single", "target", "新建圈矿任务", "选数据库 → 一键出三件套"),
    ("batch", "layers", "批量圈矿", "整个目录一次跑完"),
    ("manual", "crosshair", "人工图标定", "自动标定外推与左右链"),
    ("excel", "table", "Excel 报告汇总", "多份报告合成一份"),
    ("database", "database", "炮孔数据库生成", "坐标 TXT + 品位表"),
    ("params", "sliders", "参数台账", "谁改了哪个参数"),
]


class DashboardPage(Page):
    TITLE = "工作台"
    SUB = "今天的活儿从这儿开始：新建圈矿、批量处理、数据汇总、参数与验收都在这儿。"

    request_page = Signal(str)

    def _build(self) -> None:
        # 统计条
        stats = QHBoxLayout()
        stats.setSpacing(12)
        self.tile_tasks = W.StatTile("最近任务", "0", "本机执行记录")
        self.tile_files = W.StatTile("成果文件", "0", "可在下方直接打开")
        self.tile_platform = W.StatTile("当前平台", "—", "从当前输入识别")
        self.tile_section = W.StatTile("当前矿段", "—", "品位分级来源")
        for t in (self.tile_tasks, self.tile_files, self.tile_platform, self.tile_section):
            stats.addWidget(t, 1)
        self.add(stats)

        # 快捷入口
        qcard = W.Card("快捷操作", "常用六件事，一键直达")
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        for i, (key, ic, title, desc) in enumerate(QUICK_ACTIONS):
            btn = QPushButton()
            btn.setCursor(Qt.PointingHandCursor)
            btn.setMinimumHeight(74)
            btn.setStyleSheet(
                "QPushButton{background:%s;border:1px solid %s;border-radius:10px;"
                "text-align:left;padding:10px 12px;}"
                "QPushButton:hover{border-color:%s;background:#F7FAFC;}"
                % (theme.CARD, theme.BORDER, theme.PRIMARY))
            lay = QVBoxLayout(btn)
            lay.setContentsMargins(10, 8, 10, 8)
            lay.setSpacing(2)
            top = QHBoxLayout()
            top.setSpacing(7)
            ic_lab = QLabel()
            ic_lab.setPixmap(icons.pixmap(ic, theme.PRIMARY_DARK, 17))
            ic_lab.setStyleSheet("border:none;")
            t = QLabel(title)
            t.setStyleSheet("font-weight:600;font-size:13px;border:none;")
            top.addWidget(ic_lab)
            top.addWidget(t)
            top.addStretch(1)
            lay.addLayout(top)
            d = QLabel(desc)
            d.setStyleSheet("color:%s;font-size:11px;border:none;" % theme.TEXT_MUTED)
            lay.addWidget(d)
            btn.clicked.connect(lambda _=False, k=key: self.request_page.emit(k))
            grid.addWidget(btn, i // 3, i % 3)
        qcard.add(grid)
        self.add(qcard)

        # 最近任务 + 最近成果
        row = QHBoxLayout()
        row.setSpacing(14)
        left = QVBoxLayout()
        left.setSpacing(14)
        right = QVBoxLayout()
        right.setSpacing(14)
        row.addLayout(left, 3)
        row.addLayout(right, 2)
        self.add(row)

        tc = W.Card("最近任务", "双击一行打开成果目录")
        self.tb_tasks = W.make_table(["时间", "任务", "状态", "说明"], [100, 250, 80, 300], 190)
        self.tb_tasks.doubleClicked.connect(self._open_task_dir)
        tc.add(self.tb_tasks)
        left.addWidget(tc)

        oc = W.Card("最近成果文件", "双击打开")
        self.tb_outputs = W.make_table(["时间", "文件", "位置"], [100, 230, 330], 190)
        self.tb_outputs.doubleClicked.connect(self._open_output)
        oc.add(self.tb_outputs)
        left.addWidget(oc)

        gc = W.Card("品位分级（当前配置）", "唯一来源：grade_profiles.json")
        self.grade_box = QVBoxLayout()
        self.grade_box.setSpacing(6)
        gc.add(self.grade_box)
        right.addWidget(gc)

        pc = W.Card("项目与配置", "真实路径，便于核对环境")
        self.path_box = QVBoxLayout()
        self.path_box.setSpacing(6)
        pc.add(self.path_box)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        btn_row.addWidget(W.icon_button("folder", "项目目录", kind="ghost",
                                        on_click=lambda: paths.open_path(paths.app_dir())))
        btn_row.addWidget(W.icon_button("file", "参数文件", kind="ghost",
                                        on_click=lambda: paths.open_path(paths.params_json())))
        btn_row.addWidget(W.icon_button("shield", "验收报告", kind="ghost",
                                        on_click=self._open_accept))
        btn_row.addStretch(1)
        pc.add(btn_row)
        right.addWidget(pc)
        right.addStretch(1)

        self._refresh()

    # ------------------------------------------------------------ 刷新

    def on_show(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        tasks = self.ctx.state.tasks()
        outputs = self.ctx.state.outputs()
        self.tile_tasks.set_value(str(len(tasks)))
        self.tile_files.set_value(str(len(outputs)))
        self.tile_platform.set_value(self.ctx.platform or "—",
                                     "%s %s" % (self.ctx.platform, self.ctx.date) if self.ctx.platform else "选数据库后自动带出")
        prof = self.ctx.current_profile()
        self.tile_section.set_value(prof.name.split("（")[0],
                                    "自动识别 → %s" % prof.name if self.ctx.section == "auto" else "手动指定")

        self.tb_tasks.setRowCount(0)
        for t in tasks[:12]:
            r = self.tb_tasks.rowCount()
            self.tb_tasks.insertRow(r)
            self.tb_tasks.setItem(r, 0, W.cell(_short_time(t.get("time", "")), theme.TEXT_MUTED))
            self.tb_tasks.setItem(r, 1, W.cell(t.get("name", "")))
            fg, _bg = theme.status_color(t.get("status", ""))
            self.tb_tasks.setItem(r, 2, W.cell(t.get("status", ""), fg, True))
            self.tb_tasks.setItem(r, 3, W.cell(t.get("detail", ""), theme.TEXT_MUTED))
            self.tb_tasks.item(r, 1).setData(Qt.UserRole, t.get("out_dir", ""))

        self.tb_outputs.setRowCount(0)
        for o in outputs[:12]:
            r = self.tb_outputs.rowCount()
            self.tb_outputs.insertRow(r)
            self.tb_outputs.setItem(r, 0, W.cell(_short_time(o.get("time", "")), theme.TEXT_MUTED))
            self.tb_outputs.setItem(r, 1, W.cell(Path(o["path"]).name))
            self.tb_outputs.setItem(r, 2, W.cell(str(Path(o["path"]).parent), theme.TEXT_MUTED))
            self.tb_outputs.item(r, 1).setData(Qt.UserRole, o["path"])

        # 品位图例
        while self.grade_box.count():
            w = self.grade_box.takeAt(0).widget()
            if w is not None:
                w.deleteLater()
        head = QLabel(prof.name)
        head.setStyleSheet("font-weight:600;")
        self.grade_box.addWidget(head)
        for b in reversed(prof.bands):
            row = QWidget()
            hl = QHBoxLayout(row)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.setSpacing(8)
            sw = QLabel()
            sw.setFixedSize(14, 14)
            sw.setStyleSheet("background:%s;border:1px solid rgba(0,0,0,0.12);border-radius:3px;" % b.color)
            hl.addWidget(sw)
            lab = QLabel("%s  %s" % (b.label, b.short))
            hl.addWidget(lab)
            hl.addStretch(1)
            hint = QLabel("≥%.2f" % b.low if b.high is None else "%.2f~%.2f" % (b.low, b.high))
            hint.setObjectName("muted")
            hl.addWidget(hint)
            self.grade_box.addWidget(row)
        cut = QLabel("工业品位下限 %.2f g/t；低于它的孔按废孔处理" % prof.cutoff)
        cut.setObjectName("muted")
        self.grade_box.addWidget(cut)

        # 路径
        while self.path_box.count():
            w = self.path_box.takeAt(0).widget()
            if w is not None:
                w.deleteLater()
        for label, p in (("程序目录", paths.app_dir()),
                         ("圈矿参数", paths.params_json()),
                         ("品位分级配置", paths.grade_config())):
            row = QWidget()
            hl = QHBoxLayout(row)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.setSpacing(6)
            lab = QLabel(label)
            lab.setObjectName("fieldLabel")
            lab.setFixedWidth(96)
            hl.addWidget(lab)
            full = str(p)
            shown = full if len(full) <= 64 else (full[:26] + " … " + full[-34:])
            val = QLabel(shown)
            val.setObjectName("mono")
            val.setToolTip(full)
            val.setMinimumWidth(1)
            hl.addWidget(val, 1)
            self.path_box.addWidget(row)
        for box in (self.grade_box, self.path_box):
            box.invalidate()
            box.activate()
        self.content.adjustSize()

    # ------------------------------------------------------------ 打开

    def _open_task_dir(self, index) -> None:
        item = self.tb_tasks.item(index.row(), 1)
        if item is None:
            return
        d = item.data(Qt.UserRole)
        if d and Path(d).exists():
            paths.open_path(d)

    def _open_output(self, index) -> None:
        item = self.tb_outputs.item(index.row(), 1)
        if item is None:
            return
        p = item.data(Qt.UserRole)
        if p:
            paths.open_path(p)

    def _open_accept(self) -> None:
        report = paths.bundle_root() / "验收报告.md"
        if report.exists():
            paths.open_path(report)
        else:
            self.request_page.emit("diagnostics")
