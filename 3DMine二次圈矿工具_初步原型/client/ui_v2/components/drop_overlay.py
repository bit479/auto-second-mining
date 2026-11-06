# -*- coding: utf-8 -*-
"""全局拖放提示层：拖入时的轻量覆盖提示 + 解析/结果的小卡片。

刻意做得"轻"：
* 拖放态只是把当前页面压暗一档 + 虚线边框，中间一张 520×76 的卡片，
  不遮挡顶部操作区、不弹窗、不抢焦点（``WA_TransparentForMouseEvents``）；
* 解析中/结果态是一张底部居中的小卡片，4 秒后自动消失，不打断操作。
"""

from __future__ import annotations

from PySide6.QtCore import QRect, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from .. import icons, theme

_MODES = ("drop", "busy", "ok", "warn")


class DropOverlay(QWidget):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._mode = "drop"
        self.hide()

        self.card = QFrame(self)
        self.card.setObjectName("dropCard")
        self.card.setAttribute(Qt.WA_StyledBackground, True)
        lay = QHBoxLayout(self.card)
        lay.setContentsMargins(16, 12, 18, 12)
        lay.setSpacing(13)

        self.icon = QLabel(self.card)
        self.icon.setFixedSize(34, 34)
        self.icon.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.icon, 0, Qt.AlignVCenter)

        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(3)
        self.title = QLabel("", self.card)
        self.title.setObjectName("dropTitle")
        self.sub = QLabel("", self.card)
        self.sub.setObjectName("dropSub")
        self.sub.setWordWrap(False)
        col.addWidget(self.title)
        col.addWidget(self.sub)
        lay.addLayout(col, 1)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide_overlay)

        self.card.hide()

    # ------------------------------------------------------------ 对外

    def _sync_geometry(self) -> None:
        """覆盖层始终铺满父窗口（窗口改过大小也不会错位）。"""
        parent = self.parentWidget()
        if parent is not None and parent.rect() != self.rect():
            self.setGeometry(parent.rect())

    def show_drop(self, filename: str) -> None:
        self._timer.stop()
        self._sync_geometry()
        self._mode = "drop"
        self._set_icon("upload", "#8FC7E8")
        self.title.setText("松开鼠标，导入 TXT 坐标文件")
        self.sub.setText(self._elide(filename, 420) or "平台 / 日期会自动识别")
        self.card.resize(560, 78)
        self.card.show()
        self.show()
        self.raise_()
        self._place()
        self.update()

    def show_busy(self, filename: str) -> None:
        self._timer.stop()
        self._sync_geometry()
        self._mode = "busy"
        self._set_icon("refresh", "#8FC7E8")
        self.title.setText("正在解析坐标文件…")
        self.sub.setText(self._elide(filename, 380) + "    ·    按 Esc 可取消")
        self._show_small()

    def show_toast(self, ok: bool, title: str, detail: str = "") -> None:
        self._sync_geometry()
        self._mode = "ok" if ok else "warn"
        self._set_icon("check" if ok else "alert",
                       "#6FD3A2" if ok else "#F0A6A0")
        self.title.setText(self._elide(title, 360))
        self.sub.setText(self._elide(detail, 380))
        self.sub.setVisible(bool(detail))
        self._show_small(ok)
        self._timer.start(5200 if ok else 7000)

    def hide_overlay(self) -> None:
        self._timer.stop()
        self.card.hide()
        self.hide()

    # ------------------------------------------------------------ 内部

    def _show_small(self, ok: bool = True) -> None:
        self.card.setProperty("tone", "ok" if ok else "warn")
        self.card.style().unpolish(self.card)
        self.card.style().polish(self.card)
        self.card.setFixedSize(430, 66 if self.sub.isVisible() else 54)
        self.card.show()
        self.show()
        self.raise_()
        self._place()
        self.update()

    def _set_icon(self, name: str, color: str) -> None:
        self.icon.setPixmap(icons.pixmap(name, color, 26))

    @staticmethod
    def _elide(text: str, width: int) -> str:
        if not text:
            return ""
        fm = QLabel().fontMetrics()
        return fm.elidedText(text, Qt.ElideMiddle, width)

    def _place(self) -> None:
        w, h = self.width(), self.height()
        cw, ch = self.card.width(), self.card.height()
        if self._mode == "drop":
            x, y = (w - cw) // 2, max(80, (h - ch) // 2 - 20)
        else:
            # 放在右下角：避开页面主操作区（多数页面按钮在左侧/中部）
            x, y = max(12, w - cw - 22), max(0, h - ch - 40)
        self.card.move(x, y)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._place()

    def paintEvent(self, _e) -> None:
        if self._mode != "drop":
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.fillRect(self.rect(), QColor(10, 21, 33, 96))
        pen = QPen(QColor("#6FB4E0"), 2, Qt.DashLine)
        pen.setDashPattern([6, 5])
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRect(9, 9, self.width() - 18, self.height() - 18), 12, 12)
        p.end()
