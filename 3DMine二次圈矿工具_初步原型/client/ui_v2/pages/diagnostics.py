# -*- coding: utf-8 -*-
"""验收与诊断：一键全量 / 快检，逐项状态、日志、验收报告。"""

from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtWidgets import QHBoxLayout, QLabel, QMessageBox, QVBoxLayout

from .. import theme
from ..components import widgets as W
from ..services import paths
from .base import Page

# 验收项名称由脚本自己给（含平台/炮区），这里不预设，跑到哪项就记哪项


class DiagnosticsPage(Page):
    TITLE = "验收与诊断"
    SUB = "跑原生验收脚本，逐项看状态"

    def _build(self) -> None:
        self.runner.finished.connect(self._on_finished)
        self.rows: dict[str, int] = {}

        card = W.Card()
        card.add(W.SectionTitle("1", "执行验收", "全量约 3 分钟；快检只挑代表炮区"))
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(W.icon_button("shield", "一键全量验收", kind="primary",
                                    on_click=lambda: self.run(False)))
        row.addWidget(W.icon_button("play", "快速验收", on_click=lambda: self.run(True)))
        row.addWidget(W.icon_button("file", "打开验收报告", kind="ghost", on_click=self.open_report))
        row.addWidget(W.icon_button("folder", "打开 _probe 目录", kind="ghost",
                                    on_click=lambda: paths.open_path(paths.probe_dir())))
        row.addStretch(1)
        self.lb_state = QLabel("未执行")
        self.lb_state.setObjectName("muted")
        row.addWidget(self.lb_state)
        card.add(row)
        self.banner = W.Banner(
            "验收脚本会真跑圈矿闸门、报告口径、DXF 实体、精确模式、Excel 工具、数据库生成等项目；"
            "它只写 _probe/ 下的中间产物与 验收报告.md，不动生产数据。", "info")
        card.add(self.banner)
        self.add(card)

        tcard = W.TableCard(
            "验收项", "状态随日志实时更新", ["验收项", "状态", "说明"], [340, 90], 320,
            empty_icon="clipboard", empty_title="还没有验收记录",
            empty_desc="点上方「一键全量验收」或「快速验收」，逐项结果会实时出现在这里。")
        self.tb = tcard.table
        self.tc_items = tcard
        self.rows = {}
        self.tc_items.set_empty()
        self.add(tcard)

        lc = W.Card("日志", "")
        self.log = W.LogView()
        self.log.setMinimumHeight(220)
        lc.add(self.log)
        bar = QHBoxLayout()
        bar.addWidget(W.icon_button("refresh", "清空", kind="ghost", on_click=self.log.clear))
        bar.addWidget(W.icon_button("save", "另存日志", kind="ghost", on_click=self.save_log))
        bar.addStretch(1)
        lc.add(bar)
        self.add(lc)

        self.runner.log.connect(self._on_log)

    # ------------------------------------------------------------ 执行

    def run(self, quick: bool) -> None:
        if self.runner.running("accept_all"):
            QMessageBox.information(self, "验收", "已经在跑了，等它结束。")
            return
        self.log.clear()
        self.tb.setRowCount(0)
        self.rows = {}
        self.tc_items.set_empty()
        args = ["--no-open"] + (["--quick"] if quick else [])
        self.lb_state.setText("正在跑%s验收…" % ("快速" if quick else "全量"))
        self._tid = self.runner.run("一键验收（%s）" % ("快检" if quick else "全量"),
                                    "_probe/accept_all.py", args,
                                    key="accept_all", cwd=str(paths.bundle_root()))

    def _on_log(self, tid: str, line: str) -> None:
        if tid != getattr(self, "_tid", None):
            return
        self.log.append_line(line)
        m = re.match(r"^\s{2}(.+?)\s{2,}(通过|\*\*没通过\*\*)(.*)$", line)
        if m:
            name = m.group(1).strip()
            ok = "通过" in m.group(2)
            self._mark(name, "通过" if ok else "失败", m.group(3).strip())
        if line.startswith("结论："):
            self.lb_state.setText(line.strip())

    def _mark(self, name: str, status: str, note: str) -> None:
        fg, _ = theme.status_color(status)
        idx = self.rows.get(name)
        if idx is None:
            idx = self.tb.rowCount()
            self.tb.insertRow(idx)
            self.tb.setItem(idx, 0, W.cell(name))
            self.rows[name] = idx
        self.tb.setItem(idx, 1, W.cell(status, fg, True))
        self.tb.setItem(idx, 2, W.cell(note, theme.TEXT_MUTED))
        self.tc_items.set_empty()

    def _on_finished(self, tid: str, code: int) -> None:
        if tid != getattr(self, "_tid", None):
            return
        if code == 0:
            self.lb_state.setText("验收完成：全部通过 ✓")
            self.banner.set_text("验收全部通过。报告已写入 验收报告.md。")
            self.ctx.record("一键验收", "通过", "全部通过", str(paths.bundle_root()))
        else:
            self.lb_state.setText("验收未全部通过（退出码 %s）" % code)
            self.banner.set_text("有项目没通过，详见下面日志与 验收报告.md。")
            self.ctx.record("一键验收", "失败", "退出码 %s" % code, str(paths.bundle_root()))
            for name, i in self.rows.items():
                if self.tb.item(i, 1).text() in ("排队中", "未执行"):
                    self.tb.setItem(i, 1, W.cell("未执行", theme.TEXT_MUTED))

    # ------------------------------------------------------------ 上次结果

    def on_show(self) -> None:
        """打开页面就把「最近一次验收」读出来，别让表格空着。"""
        if not self.rows and not self.runner.running("accept_all"):
            self._load_last_report()

    def _load_last_report(self) -> None:
        p = paths.bundle_root() / "验收报告.md"
        if not p.exists():
            self.lb_state.setText("未执行（还没有 验收报告.md）")
            return
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return
        stamp = ""
        m = re.search(r"时间：([0-9:\- ]+)", text)
        if m:
            stamp = m.group(1).strip()
        for raw in text.splitlines():
            m = re.match(r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$", raw)
            if not m:
                continue
            name, verdict = m.group(1).strip(), m.group(2).strip()
            if name in ("项", "---") or verdict in ("结果",):
                continue
            if verdict.startswith("通过"):
                self._mark(name, "通过", "（上次验收）")
            elif "没通过" in verdict or "失败" in verdict:
                self._mark(name, "失败", verdict.replace("**", ""))
        concl = re.search(r"结论：\*\*(.+?)\*\*", text)
        head = "上次验收 %s" % (stamp or "")
        if concl:
            head += "：%s" % concl.group(1)
        self.lb_state.setText(head)

    def open_report(self) -> None:
        p = paths.bundle_root() / "验收报告.md"
        if p.exists():
            paths.open_path(p)
        else:
            QMessageBox.information(self, "验收报告", "还没有生成报告，先跑一次验收。")

    def save_log(self) -> None:
        p = paths.bundle_root() / "验收日志.txt"
        p.write_text(self.log.plain(), encoding="utf-8")
        self.lb_state.setText("日志已保存：%s" % p)
