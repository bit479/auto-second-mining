# -*- coding: utf-8 -*-
"""页面基类：统一页头（标题 + 说明 + 页级动作）+ 可滚动内容区 + 后台任务订阅。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget,
)

from .. import theme
from ..components import widgets as W
from ..services import context as C
from ..services.runner import runner


class Page(QWidget):
    TITLE = ""
    SUB = ""
    ICON = ""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ctx = C.context()
        self.runner = runner()
        self.setObjectName("page")
        self.setAttribute(Qt.WA_StyledBackground, True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ---------------- 页头（固定，不随内容滚动）
        self.header = QWidget()
        self.header.setObjectName("pageHeader")
        head = QHBoxLayout(self.header)
        head.setContentsMargins(theme.CONTENT_PAD_X, 18, theme.CONTENT_PAD_X, 4)
        head.setSpacing(12)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(3)
        self.title = QLabel(self.TITLE)
        self.title.setObjectName("h1")
        text_col.addWidget(self.title)
        self.subtitle = QLabel(self.SUB)
        self.subtitle.setObjectName("pageSub")
        self.subtitle.setWordWrap(True)
        text_col.addWidget(self.subtitle)
        head.addLayout(text_col, 1)

        self._actions: list[QWidget] = []
        self.action_row = QHBoxLayout()
        self.action_row.setContentsMargins(0, 0, 0, 0)
        self.action_row.setSpacing(8)
        self.action_row.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        head.addLayout(self.action_row)
        outer.addWidget(self.header)

        # ---------------- 内容区
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.content = QWidget()
        self.content.setObjectName("pageContent")
        self.body = QVBoxLayout(self.content)
        self.body.setContentsMargins(theme.CONTENT_PAD_X, 12,
                                     theme.CONTENT_PAD_X, theme.CONTENT_PAD_Y)
        self.body.setSpacing(theme.GAP)
        self.scroll.setWidget(self.content)
        outer.addWidget(self.scroll, 1)

        self._build()
        for w in self._actions:
            self.action_row.addWidget(w)

    # ---- 子类实现 ----

    def _build(self) -> None:      # pragma: no cover - 由子类覆盖
        pass

    # ---- 辅助 ----

    def add_action(self, w: QWidget) -> None:
        """页级动作（放在页头右侧；避免与顶栏信息挤在一起）。"""
        self._actions.append(w)

    def add(self, w) -> None:
        if isinstance(w, QWidget):
            self.body.addWidget(w)
        else:
            self.body.addLayout(w)

    def add_stretch(self) -> None:
        from PySide6.QtWidgets import QSizePolicy, QSpacerItem

        self.body.addItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))

    def two_columns(self) -> tuple[QVBoxLayout, QVBoxLayout]:
        row = QHBoxLayout()
        row.setSpacing(theme.GAP)
        left = QVBoxLayout()
        left.setSpacing(theme.GAP)
        right = QVBoxLayout()
        right.setSpacing(theme.GAP)
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
