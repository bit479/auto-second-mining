# -*- coding: utf-8 -*-
"""工作台首页：运行概览 / 快捷入口 / 最近任务与成果 / 矿段品位 / 项目配置。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from .. import icons, theme
from ..components import widgets as W
from ..services import paths
from .base import Page


def _short_time(text: str) -> str:
    """2026-11-05 17:49 → 11-05 17:49（表格列宽有限）。"""
    t = str(text or "").strip()
    if len(t) >= 16 and t[4] == "-" and t[7] == "-":
        return t[5:16]
    return t


QUICK_ACTIONS = [
    ("single", "target", "新建圈矿任务", "数据库 → 一键出三件套", "info", True),
    ("batch", "layers", "批量处理", "整个目录一次跑完", "muted", False),
    ("manual", "pen", "人工图标定", "人工图反推外推与左右链", "muted", False),
    ("excel", "spreadsheet", "报告汇总", "多份报告合成一份", "muted", False),
    ("database", "database", "炮孔数据库", "坐标 TXT + 品位表生成", "muted", False),
    ("params", "sliders", "参数台账", "三层覆盖关系核对", "muted", False),
]


class DashboardPage(Page):
    TITLE = "工作台"
    SUB = "今日作业入口：新建圈矿、批量处理、数据汇总与参数核对都在这里。"
    ICON = "dashboard"

    request_page = Signal(str)

    def _build(self) -> None:
        # ---------------- 页头动作
        self.add_action(W.icon_button("folder", "打开成果目录", kind="ghost",
                                      on_click=lambda: paths.open_path(paths.data_home())))
        self.add_action(W.icon_button("layers", "批量处理",
                                      on_click=lambda: self.request_page.emit("batch")))
        self.add_action(W.icon_button("play", "新建圈矿任务", kind="primary",
                                      on_click=lambda: self.request_page.emit("single")))

        # ---------------- 概览
        stats = QHBoxLayout()
        stats.setSpacing(theme.GAP)
        self.tile_tasks = W.StatTile("最近任务", "0", "本机执行记录", icon="clock", tone="info")
        self.tile_files = W.StatTile("成果文件", "0", "可在下方直接打开", icon="file-text",
                                     tone="muted")
        self.tile_platform = W.StatTile("当前平台", "—", "从当前输入识别", icon="mountain",
                                        tone="muted")
        self.tile_section = W.StatTile("当前矿段", "—", "品位分级来源", icon="target",
                                       tone="accent")
        for t in (self.tile_tasks, self.tile_files, self.tile_platform, self.tile_section):
            stats.addWidget(t, 1)
        self.add(stats)

        # ---------------- 快捷操作 + 矿段品位
        row = QHBoxLayout()
        row.setSpacing(theme.GAP)
        left = QVBoxLayout()
        left.setSpacing(theme.GAP)
        right = QVBoxLayout()
        right.setSpacing(theme.GAP)
        row.addLayout(left, 3)
        row.addLayout(right, 2)
        self.add(row)

        qcard = W.Card("快捷操作", "常用入口，一键直达")
        qcard.setSizePolicy(qcard.sizePolicy().horizontalPolicy(),
                            qcard.sizePolicy().verticalPolicy().Expanding)
        self.quick_grid = QGridLayout()
        self.quick_grid.setHorizontalSpacing(10)
        self.quick_grid.setVerticalSpacing(10)
        self.quick_cards: list[W.QuickCard] = []
        for key, ic, title, desc, tone, _primary in QUICK_ACTIONS:
            card = W.QuickCard(ic, title, desc, tone=tone)
            card.clicked.connect(lambda k=key: self.request_page.emit(k))
            self.quick_cards.append(card)
        self._quick_cols = 0
        self._relayout_quick(3)
        qcard.add(self.quick_grid)
        left.addWidget(qcard)

        gcard = W.Card("当前矿段与品位分级", "与 CAD 出图同色")
        self.grade_box = QVBoxLayout()
        self.grade_box.setSpacing(0)
        gcard.add(self.grade_box)
        self.btn_grade = W.icon_button("sliders", "查看参数", kind="ghost",
                                       on_click=lambda: self.request_page.emit("params"))
        gcard.add(self.btn_grade)
        right.addWidget(gcard)

        # ---------------- 最近任务 / 成果 + 项目配置
        row2 = QHBoxLayout()
        row2.setSpacing(theme.GAP)
        left2 = QVBoxLayout()
        left2.setSpacing(theme.GAP)
        right2 = QVBoxLayout()
        right2.setSpacing(theme.GAP)
        row2.addLayout(left2, 3)
        row2.addLayout(right2, 2)
        self.add(row2)

        self.tc_tasks = W.TableCard(
            "最近任务", "双击一行打开成果目录",
            ["时间", "任务", "状态", "说明"], [104, 196, 68], 210,
            empty_icon="clock", empty_title="暂无执行记录",
            empty_desc="新建一次圈矿任务后，这里会按时间倒序列出执行结果。")
        self.tc_tasks.table.doubleClicked.connect(self._open_task_dir)
        left2.addWidget(self.tc_tasks)

        self.tc_outputs = W.TableCard(
            "最近成果文件", "双击打开",
            ["时间", "文件", "位置"], [104, 210], 210,
            empty_icon="folder-open", empty_title="还没有成果文件",
            empty_desc="圈矿完成后会生成报告 xlsx / 图 DWG / 边界线 .3ds。")
        self.tc_outputs.table.doubleClicked.connect(self._open_output)
        left2.addWidget(self.tc_outputs)

        pc = W.Card("项目与配置", "真实路径，便于核对环境")
        self.path_box = QVBoxLayout()
        self.path_box.setSpacing(2)
        pc.add(self.path_box)
        actions = QHBoxLayout()
        actions.setSpacing(6)
        actions.addWidget(W.icon_button("folder-open", "项目目录", kind="ghost",
                                        on_click=lambda: paths.open_path(paths.app_dir())))
        actions.addWidget(W.icon_button("file", "参数文件", kind="ghost",
                                        on_click=lambda: paths.open_path(paths.params_json())))
        actions.addWidget(W.icon_button("shield", "验收报告", kind="ghost",
                                        on_click=self._open_accept))
        actions.addStretch(1)
        pc.add(actions)
        right2.addWidget(pc)

        sc = W.Card("运行状态", "本机后台任务")
        self.state_box = QVBoxLayout()
        self.state_box.setSpacing(0)
        sc.add(self.state_box)
        right2.addWidget(sc)
        right2.addStretch(1)

        self._refresh()

    # ------------------------------------------------------------ 响应式

    def _relayout_quick(self, cols: int) -> None:
        """快捷入口按可用宽度在 3 列 / 2 列之间切换，避免说明文字被压成省略号。"""
        if cols == self._quick_cols:
            return
        self._quick_cols = cols
        for i, card in enumerate(self.quick_cards):
            self.quick_grid.addWidget(card, i // cols, i % cols)
        for c in range(3):
            self.quick_grid.setColumnStretch(c, 1 if c < cols else 0)
        rows = (len(self.quick_cards) + cols - 1) // cols
        for r in range(3):
            self.quick_grid.setRowStretch(r, 1 if r < rows else 0)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._relayout_quick(3 if self.width() >= 1080 else 2)

    # ------------------------------------------------------------ 刷新

    def on_show(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        tasks = self.ctx.state.tasks()
        outputs = self.ctx.state.outputs()

        # ---- 概览
        last = tasks[0].get("time", "") if tasks else ""
        self.tile_tasks.set_value(str(len(tasks)),
                                  "最近一次 %s" % _short_time(last) if last else "还没有执行记录")
        self.tile_files.set_value(str(len(outputs)),
                                  "最近 %s" % _short_time(outputs[0].get("time", ""))
                                  if outputs else "还没有成果文件")
        if self.ctx.platform:
            self.tile_platform.set_value(self.ctx.platform,
                                         "炮区日期 %s" % (self.ctx.date or "—"))
        else:
            self.tile_platform.set_value("—", "选择数据库后自动带出")
        prof = self.ctx.current_profile()
        self.tile_section.set_value(prof.name.split("（")[0],
                                    "自动识别" if self.ctx.section == "auto" else "手动指定")

        # ---- 任务表
        tb = self.tc_tasks.table
        tb.setRowCount(0)
        for t in tasks[:12]:
            r = tb.rowCount()
            tb.insertRow(r)
            tb.setItem(r, 0, W.cell(_short_time(t.get("time", "")), theme.TEXT_MUTED))
            tb.setItem(r, 1, W.cell(t.get("name", "")))
            fg, _bg = theme.status_color(t.get("status", ""))
            tb.setItem(r, 2, W.cell(t.get("status", ""), fg, True))
            tb.setItem(r, 3, W.cell(t.get("detail", ""), theme.TEXT_MUTED))
            tb.item(r, 1).setData(Qt.UserRole, t.get("out_dir", ""))
        self.tc_tasks.set_empty()

        # ---- 成果表
        ob = self.tc_outputs.table
        ob.setRowCount(0)
        for o in outputs[:12]:
            r = ob.rowCount()
            ob.insertRow(r)
            ob.setItem(r, 0, W.cell(_short_time(o.get("time", "")), theme.TEXT_MUTED))
            ob.setItem(r, 1, W.cell(Path(o["path"]).name))
            ob.setItem(r, 2, W.cell(str(Path(o["path"]).parent), theme.TEXT_MUTED))
            ob.item(r, 1).setData(Qt.UserRole, o["path"])
        self.tc_outputs.set_empty()

        self._fill_grade(prof)
        self._fill_paths()
        self._fill_state()

    def _fill_grade(self, prof) -> None:
        _clear(self.grade_box)

        head = QHBoxLayout()
        head.setSpacing(8)
        name = QLabel(prof.name)
        name.setStyleSheet("font-size:13px;font-weight:600;")
        head.addWidget(name)
        head.addStretch(1)
        unit = QLabel("Au (g/t)")
        unit.setStyleSheet("font-size:%dpx;color:%s;" % (theme.FS_CAPTION, theme.TEXT_MUTED))
        head.addWidget(unit)
        self.grade_box.addLayout(head)
        self.grade_box.addSpacing(8)

        # 由高到低展示，与图例阅读习惯一致
        for b in reversed(prof.bands):
            row = QWidget()
            hl = QHBoxLayout(row)
            hl.setContentsMargins(0, 3, 0, 3)
            hl.setSpacing(9)
            sw = QLabel()
            sw.setFixedSize(12, 12)
            sw.setStyleSheet("background:%s;border:1px solid #1A000000;border-radius:3px;"
                             % b.color)
            hl.addWidget(sw)
            lab = QLabel(b.label)
            lab.setStyleSheet("font-family:%s;font-size:%dpx;color:%s;"
                              % (theme.FONT_MONO, theme.FS_SMALL, theme.TEXT))
            hl.addWidget(lab)
            hl.addStretch(1)
            hint = QLabel("≥ %.2f" % b.low if b.high is None
                          else "%.2f – %.2f" % (b.low, b.high))
            hint.setStyleSheet("font-size:%dpx;color:%s;"
                               % (theme.FS_CAPTION, theme.TEXT_MUTED))
            hl.addWidget(hint)
            self.grade_box.addWidget(row)

        self.grade_box.addSpacing(8)
        cut = QLabel("工业品位下限 %.2f g/t · 低于它的孔按废孔处理" % prof.cutoff)
        cut.setStyleSheet("font-size:%dpx;color:%s;" % (theme.FS_CAPTION, theme.TEXT_MUTED))
        cut.setWordWrap(True)
        self.grade_box.addWidget(cut)
        src = QLabel("来源 grade_profiles.json · 配置 %s"
                     % ("自动识别" if self.ctx.section == "auto" else "手动指定"))
        src.setStyleSheet("font-size:%dpx;color:%s;" % (theme.FS_CAPTION, theme.TEXT_MUTED))
        self.grade_box.addWidget(src)

    def _fill_paths(self) -> None:
        _clear(self.path_box)
        rows = (("程序目录", paths.app_dir()),
                ("圈矿参数", paths.params_json()),
                ("品位配置", paths.grade_config()))
        for label, p in rows:
            self.path_box.addWidget(_path_row(label, Path(p)))

    def _fill_state(self) -> None:
        _clear(self.state_box)
        from ..services.runner import runner

        running = runner().running_names()
        tasks = self.ctx.state.tasks()
        rows = [("当前状态", "正在执行 · %s" % running[-1] if running else "空闲",
                 theme.WARNING if running else theme.SUCCESS),
                ("后台任务", "%d 个在跑" % len(running) if running else "无排队任务",
                 theme.TEXT)]
        last = tasks[0] if tasks else None
        rows.append(("最近结果", "%s · %s" % (last.get("name", ""), last.get("status", ""))
                     if last else "—", theme.TEXT_MUTED))
        for label, value, color in rows:
            row = QWidget()
            hl = QHBoxLayout(row)
            hl.setContentsMargins(0, 3, 0, 3)
            hl.setSpacing(9)
            lab = QLabel(label)
            lab.setStyleSheet("font-size:%dpx;color:%s;" % (theme.FS_CAPTION, theme.TEXT_MUTED))
            lab.setFixedWidth(64)
            val = QLabel(value)
            val.setStyleSheet("font-size:%dpx;color:%s;" % (theme.FS_SMALL, color))
            val.setToolTip(value)
            hl.addWidget(lab)
            hl.addWidget(val, 1)
            self.state_box.addWidget(row)

    # ------------------------------------------------------------ 打开

    def _open_task_dir(self, index) -> None:
        item = self.tc_tasks.table.item(index.row(), 1)
        if item is None:
            return
        d = item.data(Qt.UserRole)
        if d and Path(d).exists():
            paths.open_path(d)

    def _open_output(self, index) -> None:
        item = self.tc_outputs.table.item(index.row(), 1)
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


def _clear(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w is not None:
            w.deleteLater()
        elif item.layout() is not None:
            _clear(item.layout())


def _path_row(label: str, p: Path) -> QWidget:
    row = QWidget()
    hl = QHBoxLayout(row)
    hl.setContentsMargins(0, 2, 0, 2)
    hl.setSpacing(8)
    lab = QLabel(label)
    lab.setObjectName("fieldLabel")
    lab.setFixedWidth(56)
    hl.addWidget(lab)

    full = str(p)
    val = QLabel()
    val.setStyleSheet("font-family:%s;font-size:%dpx;color:%s;"
                      % (theme.FONT_MONO, theme.FS_CAPTION + 1, theme.TEXT_MUTED))
    fm = val.fontMetrics()
    val.setText(fm.elidedText(full, Qt.ElideMiddle, 168))
    val.setToolTip(full)
    val.setMinimumWidth(1)
    hl.addWidget(val, 1)

    b = W.tool_button("copy", "复制完整路径",
                      on_click=lambda: W.copy_text(row, full))
    b.setFixedSize(22, 22)
    hl.addWidget(b)
    b2 = W.tool_button("external", "打开", on_click=lambda: paths.open_path(p))
    b2.setFixedSize(22, 22)
    hl.addWidget(b2)
    return row
