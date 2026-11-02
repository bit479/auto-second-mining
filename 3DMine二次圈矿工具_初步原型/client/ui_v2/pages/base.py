# -*- coding: utf-8 -*-
"""页面基类：统一标题区 + 可滚动内容区 + 后台任务订阅。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget,
)

from ..components import widgets as W
from ..services import context as C
from ..services.runner import runner
from .. import theme


class Page(QWidget):
    TITLE = ""
    SUB = ""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ctx = C.context()
        self.runner = runner()
        self.setObjectName("page")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 标题与副标题统一显示在顶栏（避免"顶栏一个标题、页面又一个标题"）
        self.title = QLabel(self.TITLE)
        self.title.setVisible(False)
        self.subtitle = QLabel(self.SUB)
        self.subtitle.setVisible(False)
        self._actions: list[QWidget] = []

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.content = QWidget()
        self.body = QVBoxLayout(self.content)
        self.body.setContentsMargins(22, 16, 22, 20)
        self.body.setSpacing(14)
        self.scroll.setWidget(self.content)
        outer.addWidget(self.scroll, 1)

        self._build()

    # ---- 子类实现 ----

    def _build(self) -> None:      # pragma: no cover - 由子类覆盖
        pass

    # ---- 辅助 ----

    def add_action(self, w: QWidget) -> None:
        """页面级动作按钮：由主窗口放到顶栏右侧（不在页面里重复一排）。"""
        self._actions.append(w)

    def add(self, w) -> None:
        if isinstance(w, QWidget):
            self.body.addWidget(w)
        else:
            self.body.addLayout(w)

    def two_columns(self) -> tuple[QVBoxLayout, QVBoxLayout]:
        row = QHBoxLayout()
        row.setSpacing(14)
        left = QVBoxLayout()
        left.setSpacing(14)
        right = QVBoxLayout()
        right.setSpacing(14)
        row.addLayout(left, 3)
        row.addLayout(right, 2)
        self.body.addLayout(row)
        return left, right

    def page_banner(self, text: str, tone: str = "info") -> W.Banner:
        b = W.Banner(text, tone)
        self.add(b)
        return b

    # ---- 生命周期 ----

    def on_show(self) -> None:
        pass

    def bind_task(self, log_view: W.LogView, on_done=None):
        """把日志台接到 runner；返回 connect 后的 tid 跟踪器。"""
        state = {"tid": None, "done": on_done}

        def _log(tid, line):
            if state["tid"] in (None, tid):
                log_view.append_line(line)

        def _fin(tid, code):
            if state["tid"] == tid and state["done"]:
                state["done"](code)

        self.runner.log.connect(_log)
        self.runner.finished.connect(_fin)
        return state
