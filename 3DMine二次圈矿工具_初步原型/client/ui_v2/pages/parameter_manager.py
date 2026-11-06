# -*- coding: utf-8 -*-
"""参数管理：全局 / 平台 / 炮区三层 + 覆盖关系 + 参数台账。"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QMessageBox, QTextEdit, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget,
)

from .. import theme
from ..components import widgets as W
from ..services import config, paths
from .base import Page


class ParameterManagerPage(Page):
    TITLE = "参数管理"
    SUB = "三层覆盖关系 + 参数台账（只读展示）"

    def _build(self) -> None:
        self.runner.finished.connect(self._on_finished)
        row = QHBoxLayout()
        row.setSpacing(14)
        left = QVBoxLayout()
        left.setSpacing(10)
        right = QVBoxLayout()
        right.setSpacing(10)
        row.addLayout(left, 2)
        row.addLayout(right, 3)
        self.add(row)

        tc = W.Card("参数层级", "点一层看它覆盖了什么")
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["层级 / 参数", "值"])
        self.tree.setColumnWidth(0, 210)
        self.tree.setAlternatingRowColors(True)
        self.tree.setFocusPolicy(Qt.NoFocus)
        self.tree.setIndentation(14)
        self.tree.setUniformRowHeights(True)
        self.tree.itemSelectionChanged.connect(self._on_select)
        tc.add(self.tree)
        tbar = QHBoxLayout()
        tbar.setSpacing(6)
        tbar.addWidget(W.icon_button("refresh", "刷新", kind="ghost", on_click=self.reload))
        tbar.addWidget(W.icon_button("file", "打开 JSON", kind="ghost",
                                     on_click=lambda: paths.open_path(paths.params_json())))
        tbar.addWidget(W.icon_button("sliders", "参数台账（终端输出）", kind="ghost",
                                     on_click=self.run_ledger))
        tbar.addStretch(1)
        tc.add(tbar)
        left.addWidget(tc)

        dc = W.Card("该层内容", "原始 JSON，便于核对")
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setObjectName("log")
        self.detail.setMinimumHeight(240)
        dc.add(self.detail)
        right.addWidget(dc)

        sc = W.Card("覆盖关系", "每个参数最终由谁决定")
        self.tb = W.make_table(["参数", "全局默认", "平台", "炮区", "生效值", "来源"],
                               [186, 84, 74, 74, 92], 300)
        sc.add(self.tb)
        self.lb_plat = QLabel("")
        self.lb_plat.setObjectName("muted")
        sc.add(self.lb_plat)
        right.addWidget(sc)

        lc = W.Card("台账输出", "")
        self.log = W.LogView()
        self.log.setMinimumHeight(120)
        lc.add(self.log)
        self.add(lc)

    # ------------------------------------------------------------ 数据

    def on_show(self) -> None:
        self.reload()

    def reload(self) -> None:
        cfg = config.load_params()
        self.tree.clear()
        flat = {k: v for k, v in cfg.items() if not isinstance(v, dict)}
        it_global = QTreeWidgetItem(["全局默认", "%d 项" % len(flat)])
        it_global.setData(0, Qt.UserRole, ("global", None))
        for k, v in flat.items():
            it_global.addChild(QTreeWidgetItem([k, _fmt(v)]))
        self.tree.addTopLevelItem(it_global)

        for plat, layer in (cfg.get("platforms") or {}).items():
            it = QTreeWidgetItem(["平台 %s" % plat,
                                  "%d 项覆盖" % len([k for k in layer if not k.startswith("_")])])
            it.setData(0, Qt.UserRole, ("platform", plat))
            for k, v in layer.items():
                if k.startswith("_"):
                    continue
                it.addChild(QTreeWidgetItem([k, _fmt(v)]))
            self.tree.addTopLevelItem(it)

        for key, layer in (cfg.get("blasts") or {}).items():
            it = QTreeWidgetItem(["炮区 %s" % key,
                                  "%d 项覆盖" % len([k for k in layer if not k.startswith("_")])])
            it.setData(0, Qt.UserRole, ("blast", key))
            for k, v in layer.items():
                if k.startswith("_"):
                    continue
                it.addChild(QTreeWidgetItem([k, _fmt(v)]))
            self.tree.addTopLevelItem(it)

        self.tree.setCurrentItem(it_global)
        self._fill_relation()
        self._on_select()

    def _on_select(self) -> None:
        items = self.tree.selectedItems()
        if not items:
            return
        it = items[0]
        parent = it.parent()
        data = parent.data(0, Qt.UserRole) if parent is not None else it.data(0, Qt.UserRole)
        cfg = config.load_params()
        scope, key = (data if data else (None, None))
        if scope == "global":
            payload = {k: v for k, v in cfg.items() if not isinstance(v, dict)}
        elif scope == "platform":
            payload = (cfg.get("platforms") or {}).get(key, {})
        elif scope == "blast":
            payload = (cfg.get("blasts") or {}).get(key, {})
        else:
            payload = cfg
        self.detail.setPlainText(json.dumps(payload, ensure_ascii=False, indent=2))

    def _fill_relation(self) -> None:
        plat = self.ctx.platform
        date = self.ctx.date
        src = config.param_sources(plat, date)
        eff = config.params_for(plat, date)
        cfg = config.load_params()
        plat_layer = (cfg.get("platforms") or {}).get(plat, {}) if plat else {}
        blast_layer = (cfg.get("blasts") or {}).get("%s-%s" % (plat, date), {}) if (plat and date) else {}
        self.tb.setRowCount(0)
        for key, cn, unit, _is_int, _tip in config.PARAM_SPECS:
            r = self.tb.rowCount()
            self.tb.insertRow(r)
            self.tb.setItem(r, 0, W.cell("%s（%s）" % (cn, unit) if unit else cn, bold=True))
            self.tb.setItem(r, 1, W.cell(_fmt(cfg.get(key)), theme.TEXT_MUTED))
            self.tb.setItem(r, 2, W.cell(_fmt(plat_layer.get(key)), theme.TEXT_MUTED))
            self.tb.setItem(r, 3, W.cell(_fmt(blast_layer.get(key)), theme.TEXT_MUTED))
            self.tb.setItem(r, 4, W.cell(_fmt(eff.get(key))))
            self.tb.setItem(r, 5, W.cell(src.get(key, ""), theme.PRIMARY_DARK))
        self.lb_plat.setText(
            "当前上下文：平台 %s / 日期 %s ｜ 只有「炮区 %s-%s」或「平台 %s」里出现过的键才会覆盖上一层"
            % (plat or "—", date or "—", plat or "?", date or "?", plat or "?"))

    # ------------------------------------------------------------ 台账

    def run_ledger(self) -> None:
        self.log.append_line("== 参数台账（_probe/params_report.py）==")
        self._tid = self.runner.run("参数台账", "_probe/params_report.py", [],
                                    key="params_report", cwd=str(paths.bundle_root()))

    def _on_finished(self, tid: str, code: int) -> None:
        if tid == getattr(self, "_tid", None):
            self.log.append_line("[结束] 退出码 %s" % code)


def _fmt(v) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "是" if v else "否"
    if isinstance(v, float):
        return "%g" % v
    if isinstance(v, (list, tuple)):
        return ";".join(str(x) for x in v)
    return str(v)
