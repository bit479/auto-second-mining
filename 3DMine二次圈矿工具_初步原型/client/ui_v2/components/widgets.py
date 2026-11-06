# -*- coding: utf-8 -*-
"""公共组件库（v1.16）：卡片、统计块、快捷卡、空状态、表格卡、徽章、表单行、参数格。

所有尺寸与颜色都取自 ``theme`` 的设计令牌，页面里不再手写 hex 与像素。
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable

from PySide6.QtCore import QPointF, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QPlainTextEdit, QPushButton, QSizePolicy,
    QTableWidget, QTableWidgetItem, QToolButton, QVBoxLayout, QWidget,
)

from .. import icons, theme


# ---------------------------------------------------------------- 基础容器

class Card(QFrame):
    """白底卡片，可选标题行（标题 + 说明 + 右侧自定义件）。"""

    def __init__(self, title: str = "", subtitle: str = "", parent: QWidget | None = None,
                 tight: bool = False):
        super().__init__(parent)
        self.setObjectName("cardTight" if tight else "card")
        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(18, 15, 18, 16)
        self._outer.setSpacing(12)
        self.header = None
        if title:
            row = QHBoxLayout()
            row.setSpacing(9)
            self.title_label = QLabel(title)
            self.title_label.setObjectName("cardTitle")
            row.addWidget(self.title_label)
            if subtitle:
                self.sub_label = QLabel(subtitle)
                self.sub_label.setObjectName("muted")
                row.addWidget(self.sub_label)
            row.addStretch(1)
            self.header = row
            self._outer.addLayout(row)
        self.body = QVBoxLayout()
        self.body.setSpacing(10)
        self._outer.addLayout(self.body)
        self._outer.setStretch(self._outer.count() - 1, 1)

    def add(self, w) -> None:
        if isinstance(w, QPushButton):
            # 按钮默认横向撑满，卡片里应保持自然宽度并左对齐
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.addWidget(w)
            row.addStretch(1)
            self.body.addLayout(row)
        elif isinstance(w, QWidget):
            self.body.addWidget(w)
        else:
            self.body.addLayout(w)

    def add_header_widget(self, w: QWidget) -> None:
        if self.header is not None:
            self.header.addWidget(w)


def hline() -> QFrame:
    f = QFrame()
    f.setObjectName("hline")
    f.setFrameShape(QFrame.NoFrame)
    return f


def vline() -> QFrame:
    f = QFrame()
    f.setObjectName("vline")
    f.setFrameShape(QFrame.NoFrame)
    return f


class SectionTitle(QWidget):
    """「01 输入数据」这种带序号的小标题。"""

    def __init__(self, no: str, title: str, hint: str = "", parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        badge = QLabel(no if len(no) > 1 else "0" + no)
        badge.setObjectName("sectionNo")
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedSize(26, 22)
        lay.addWidget(badge)
        t = QLabel(title)
        t.setObjectName("h2")
        lay.addWidget(t)
        if hint:
            h = QLabel(hint)
            h.setObjectName("muted")
            lay.addWidget(h)
        lay.addStretch(1)


# ---------------------------------------------------------------- 状态徽章

class Badge(QLabel):
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignCenter)
        self.set_state(text or "—")

    def set_state(self, text: str, tone: str | None = None) -> None:
        self.setText(text)
        fg, bg = theme.status_color(text) if tone is None else _tone(tone)
        self.setStyleSheet(
            "QLabel{color:%s;background:%s;border-radius:9px;padding:1px 9px;"
            "font-size:%dpx;font-weight:600;}" % (fg, bg, theme.FS_CAPTION))
        self.setFixedHeight(20)


def _tone(tone: str) -> tuple[str, str]:
    return {
        "ok": (theme.SUCCESS, theme.SUCCESS_BG),
        "warn": (theme.WARNING, theme.WARNING_BG),
        "error": (theme.DANGER, theme.DANGER_BG),
        "info": (theme.PRIMARY_DARK, theme.PRIMARY_LIGHT),
        "accent": (theme.ACCENT_DARK, theme.ACCENT_LIGHT),
        "muted": (theme.TEXT_MUTED, theme.NEUTRAL_BG),
    }.get(tone, (theme.TEXT_MUTED, theme.NEUTRAL_BG))


class Chip(QLabel):
    def __init__(self, text: str = "", primary: bool = False, parent=None):
        super().__init__(text, parent)
        self.setObjectName("chipPrimary" if primary else "chip")


# ---------------------------------------------------------------- 统计块

class StatTile(QFrame):
    """概览统计块：图标 + 数值 + 标签 + 说明。数值一律来自真实数据。"""

    def __init__(self, label: str, value: str = "—", hint: str = "", parent=None,
                 icon: str = "", tone: str = "info"):
        super().__init__(parent)
        self.setObjectName("statCard")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(0)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(8)
        self.label = QLabel(label)
        self.label.setObjectName("statLabel")
        top.addWidget(self.label)
        top.addStretch(1)
        self.icon = QLabel()
        self.icon.setFixedSize(18, 18)
        self.icon.setAlignment(Qt.AlignCenter)
        if icon:
            fg, _bg = _tone(tone)
            self.icon.setPixmap(icons.pixmap(icon, fg, 18))
        top.addWidget(self.icon)
        lay.addLayout(top)
        lay.addSpacing(6)

        value_row = QHBoxLayout()
        value_row.setContentsMargins(0, 0, 0, 0)
        value_row.setSpacing(5)
        self.value = QLabel(value)
        self.value.setObjectName("statValue")
        value_row.addWidget(self.value)
        self.unit = QLabel("")
        self.unit.setObjectName("kpiUnit")
        self.unit.setAlignment(Qt.AlignBottom)
        value_row.addWidget(self.unit)
        value_row.addStretch(1)
        lay.addLayout(value_row)
        lay.addSpacing(2)

        self.hint = QLabel(hint)
        self.hint.setObjectName("statHint")
        self.hint.setVisible(bool(hint))
        lay.addWidget(self.hint)
        self.setMinimumWidth(150)

    def set_value(self, text: str, hint: str | None = None, unit: str | None = None) -> None:
        self.value.setText(text)
        # 无数据时用弱化的占位样式，避免 24px 的「—」被误读成一条分隔线
        placeholder = text in ("—", "", "-")
        self.value.setStyleSheet(
            "font-size:%dpx;font-weight:600;color:%s;"
            % (theme.FS_H2 if placeholder else theme.FS_DISPLAY,
               theme.TEXT_MUTED if placeholder else theme.TEXT))
        if hint is not None:
            self.hint.setText(hint)
            self.hint.setVisible(bool(hint))
        if unit is not None:
            self.unit.setText(unit)
            self.unit.setVisible(bool(unit))


class QuickCard(QFrame):
    """快捷功能卡：浅色图标底板 + 标题 + 一句说明 + hover/按下反馈。"""

    clicked = Signal()

    def __init__(self, icon_name: str, title: str, desc: str = "", parent=None,
                 tone: str = "info"):
        super().__init__(parent)
        self.setObjectName("quickCard")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(88)
        self.setMinimumWidth(156)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(12)

        self.tile = QLabel()
        self.tile.setFixedSize(36, 36)
        self.tile.setAlignment(Qt.AlignCenter)
        fg, bg = _tone(tone)
        self.tile.setPixmap(icons.pixmap(icon_name, fg, theme.ICON_CARD))
        self.tile.setStyleSheet(
            "background:%s;border:1px solid %s;border-radius:8px;" % (bg, theme.mix(bg, fg, 0.16)))
        lay.addWidget(self.tile, 0, Qt.AlignVCenter)

        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(3)
        self.title = QLabel(title)
        self.title.setStyleSheet("font-size:13px;font-weight:600;color:%s;background:transparent;"
                                 % theme.TEXT)
        self._desc_full = desc
        self.desc = QLabel(desc)
        self.desc.setStyleSheet("font-size:%dpx;color:%s;background:transparent;"
                                % (theme.FS_CAPTION + 1, theme.TEXT_MUTED))
        self.desc.setWordWrap(False)
        self.desc.setMinimumWidth(1)
        col.addWidget(self.title)
        col.addWidget(self.desc)
        lay.addLayout(col, 1)
        self.setToolTip("%s\n%s" % (title, desc) if desc else title)

    def set_desc(self, text: str) -> None:
        self._desc_full = text
        self._elide_desc()

    def _elide_desc(self) -> None:
        fm = self.desc.fontMetrics()
        self.desc.setText(fm.elidedText(self._desc_full, Qt.ElideRight,
                                        max(40, self.desc.width())))

    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        self._elide_desc()

    def mouseReleaseEvent(self, e) -> None:
        if e.button() == Qt.LeftButton and self.rect().contains(e.position().toPoint()):
            self.clicked.emit()

    def enterEvent(self, _e) -> None:
        self.setProperty("hover", "true")
        self._repolish()

    def leaveEvent(self, _e) -> None:
        self.setProperty("hover", "false")
        self._repolish()

    def _repolish(self) -> None:
        self.style().unpolish(self)
        self.style().polish(self)


# ---------------------------------------------------------------- 空状态

class EmptyState(QWidget):
    """设计完整的空状态：图标 + 标题 + 说明 +（可选）动作。"""

    def __init__(self, icon_name: str = "info", title: str = "暂无数据",
                 desc: str = "", action_text: str = "", on_action: Callable | None = None,
                 parent=None, compact: bool = False):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 18 if compact else 34, 0, 18 if compact else 34)
        lay.setSpacing(0)
        lay.setAlignment(Qt.AlignCenter)

        self.ic = QLabel()
        self.ic.setFixedSize(40, 40)
        self.ic.setAlignment(Qt.AlignCenter)
        self.ic.setPixmap(icons.pixmap(icon_name, theme.TEXT_FAINT, 34))
        lay.addWidget(self.ic, 0, Qt.AlignHCenter)
        lay.addSpacing(10)

        self.t = QLabel(title)
        self.t.setStyleSheet("font-size:13px;font-weight:600;color:%s;" % theme.TEXT_SUB)
        self.t.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.t)

        self.d = QLabel(desc)
        self.d.setObjectName("muted")
        self.d.setAlignment(Qt.AlignCenter)
        self.d.setWordWrap(True)
        self.d.setVisible(bool(desc))
        lay.addWidget(self.d)

        if action_text:
            lay.addSpacing(12)
            row = QHBoxLayout()
            row.addStretch(1)
            b = QPushButton(action_text)
            b.setProperty("kind", "ghost")
            b.setCursor(Qt.PointingHandCursor)
            if on_action:
                b.clicked.connect(on_action)
            row.addWidget(b)
            row.addStretch(1)
            lay.addLayout(row)


# ---------------------------------------------------------------- 表格卡

class TableCard(QFrame):
    """卡片 + 表格 + 空状态（无数据时不留一片空白）。"""

    def __init__(self, title: str, hint: str = "", headers: Iterable[str] = (),
                 widths: list[int] | None = None, height: int = 200,
                 empty_icon: str = "file-text", empty_title: str = "暂无记录",
                 empty_desc: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 15, 18, 16)
        lay.setSpacing(12)

        head = QHBoxLayout()
        head.setSpacing(9)
        t = QLabel(title)
        t.setObjectName("cardTitle")
        head.addWidget(t)
        if hint:
            self.hint_label = QLabel(hint)
            self.hint_label.setObjectName("muted")
            head.addWidget(self.hint_label)
        head.addStretch(1)
        self.head = head
        lay.addLayout(head)

        self.table = make_table(list(headers), widths, height)
        lay.addWidget(self.table)

        self.empty = EmptyState(empty_icon, empty_title, empty_desc, compact=True)
        self.empty.setVisible(False)
        lay.addWidget(self.empty)
        self._has_rows = False

    def add_header_widget(self, w: QWidget) -> None:
        self.head.addWidget(w)

    def set_empty(self, title: str | None = None, desc: str | None = None) -> None:
        """根据行数自动切换表格 / 空状态。"""
        self._has_rows = self.table.rowCount() > 0
        if title is not None:
            self.empty.t.setText(title)
        if desc is not None:
            self.empty.d.setText(desc)
            self.empty.d.setVisible(bool(desc))
        self.table.setVisible(self._has_rows)
        self.empty.setVisible(not self._has_rows)


def make_table(headers: list[str], stretches: list[int] | None = None,
               height: int | None = None) -> QTableWidget:
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.verticalHeader().setVisible(False)
    t.verticalHeader().setDefaultSectionSize(theme.ROW_H)
    t.setAlternatingRowColors(True)
    t.setSelectionBehavior(QAbstractItemView.SelectRows)
    t.setSelectionMode(QAbstractItemView.SingleSelection)
    t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.setShowGrid(False)
    t.setWordWrap(False)
    t.setFocusPolicy(Qt.NoFocus)
    t.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
    t.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
    t.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    t.setTextElideMode(Qt.ElideRight)
    hh = t.horizontalHeader()
    hh.setFixedHeight(theme.HEADER_H)
    hh.setSectionResizeMode(QHeaderView.Interactive)
    hh.setStretchLastSection(True)
    hh.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    hh.setHighlightSections(False)
    hh.setMinimumSectionSize(48)
    if stretches:
        for i, w in enumerate(stretches):
            t.setColumnWidth(i, w)
    t.setMinimumHeight(height or 200)
    return t


def cell(text, color: str | None = None, bold: bool = False, align=None) -> QTableWidgetItem:
    item = QTableWidgetItem("" if text is None else str(text))
    if color:
        item.setForeground(QColor(color))
    if bold:
        f = item.font()
        f.setBold(True)
        item.setFont(f)
    if align is not None:
        item.setTextAlignment(align)
    item.setToolTip("" if text is None else str(text))
    return item


# ---------------------------------------------------------------- 文件选择行

class FileRow(QWidget):
    """一行：标签 + 路径 + 浏览 + 状态。支持拖放。"""

    changed = Signal(str)

    def __init__(self, label: str, placeholder: str = "", mode: str = "open",
                 file_filter: str = "所有文件 (*.*)", parent=None,
                 title: str = "选择文件", must_exist: bool = True, browse: bool = True):
        super().__init__(parent)
        self.mode = mode
        self.filter = file_filter
        self.title = title
        self.must_exist = must_exist
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        self.label = QLabel(label)
        self.label.setObjectName("fieldLabel")
        self.label.setFixedWidth(112)
        lay.addWidget(self.label)

        self.edit = QLineEdit()
        self.edit.setPlaceholderText(placeholder)
        self.edit.setFixedHeight(theme.CTRL_H)
        self.edit.textChanged.connect(self._on_text)
        lay.addWidget(self.edit, 1)

        self.btn = QPushButton("浏览")
        self.btn.setIcon(icons.icon("folder", theme.TEXT_MUTED, theme.ICON_BTN))
        self.btn.setIconSize(QSize(theme.ICON_BTN, theme.ICON_BTN))
        self.btn.setFixedHeight(theme.CTRL_H)
        self.btn.clicked.connect(self.browse)
        self.btn.setVisible(browse)
        lay.addWidget(self.btn)

        self.state = QLabel("")
        self.state.setFixedSize(18, 18)
        self.state.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.state)

        self.setAcceptDrops(True)

    # ---- 值 ----

    def value(self) -> str:
        return self.edit.text().strip()

    def path(self) -> Path | None:
        v = self.value()
        return Path(v) if v else None

    def set_value(self, text) -> None:
        self.edit.setText(str(text or ""))

    def set_state(self, ok: bool | None, tip: str = "") -> None:
        if ok is None:
            self.state.setPixmap(icons.pixmap("info", theme.TEXT_FAINT, 15))
        elif ok:
            self.state.setPixmap(icons.pixmap("check", theme.SUCCESS, 15))
        else:
            self.state.setPixmap(icons.pixmap("alert", theme.DANGER, 15))
        self.state.setToolTip(tip)
        self.edit.setProperty("state", "" if ok is None else ("ok" if ok else "error"))
        self.edit.style().unpolish(self.edit)
        self.edit.style().polish(self.edit)

    def _on_text(self, text: str) -> None:
        p = Path(text.strip()) if text.strip() else None
        if p is None:
            self.set_state(None)
        elif not p.exists() and self.must_exist:
            self.set_state(False, "路径不存在")
        else:
            self.set_state(True, "")
        self.changed.emit(text)

    # ---- 浏览 ----

    def browse(self) -> None:
        cur = self.value()
        start = str(Path(cur).parent) if cur else ""
        if self.mode == "dir":
            picked = QFileDialog.getExistingDirectory(self, self.title, start)
        elif self.mode == "save":
            picked, _ = QFileDialog.getSaveFileName(self, self.title, cur, self.filter)
        else:
            picked, _ = QFileDialog.getOpenFileName(self, self.title, start, self.filter)
        if picked:
            self.set_value(picked)

    # ---- 拖放 ----

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        urls = e.mimeData().urls()
        if urls:
            self.set_value(urls[0].toLocalFile())
            e.acceptProposedAction()


# ---------------------------------------------------------------- 日志台

class LogView(QPlainTextEdit):
    """等宽日志；按关键字着色（失败红、警告橙、成功绿）。"""

    def __init__(self, parent=None, max_lines: int = 4000):
        super().__init__(parent)
        self.setObjectName("log")
        self.setReadOnly(True)
        self.setMaximumBlockCount(max_lines)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        f = QFont("Cascadia Mono")
        f.setStyleHint(QFont.Monospace)
        f.setPointSize(9)
        self.setFont(f)
        self.setStyleSheet("QPlainTextEdit{line-height:150%;}")

    def append_line(self, text: str) -> None:
        t = text.rstrip("\n")
        low = t.lower()
        color = theme.TEXT_SUB
        if "[错误]" in t or "[失败]" in t or "traceback" in low or "error" in low:
            color = theme.DANGER
        elif "[警告]" in t or "[提示]" in t or "[缺" in t:
            color = theme.WARNING
        elif t.startswith("[完成]") or "结论：全部" in t or "✓" in t:
            color = theme.SUCCESS
        elif t.startswith("==") or t.startswith("[开始]") or t.startswith("[命令]"):
            color = theme.PRIMARY_DARK
        safe = (t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                .replace(" ", "&nbsp;"))
        self.appendHtml('<span style="color:%s">%s</span>' % (color, safe))
        bar = self.verticalScrollBar()
        bar.setValue(bar.maximum())

    def plain(self) -> str:
        return self.toPlainText()


def copy_text(widget: QWidget, text: str) -> None:
    QGuiApplication.clipboard().setText(text)


# ---------------------------------------------------------------- 参数编辑

class ParamGrid(QWidget):
    """参数编辑格：标签 + 输入 + "来源"角标（全局/平台/炮区）。"""

    def __init__(self, specs: Iterable[tuple], columns: int = 3, parent=None):
        super().__init__(parent)
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(10)
        self.edits: dict[str, QLineEdit] = {}
        self.source_labels: dict[str, QLabel] = {}
        for i, (key, cn, unit, is_int, tip) in enumerate(specs):
            r, c = divmod(i, columns)
            box = QVBoxLayout()
            box.setSpacing(4)
            top = QHBoxLayout()
            top.setSpacing(5)
            lab = QLabel(cn)
            lab.setObjectName("fieldLabel")
            top.addWidget(lab)
            if unit:
                u = QLabel(unit)
                u.setStyleSheet("color:%s;font-size:%dpx;" % (theme.TEXT_MUTED, theme.FS_MICRO))
                top.addWidget(u)
            top.addStretch(1)
            src = QLabel("")
            src.setStyleSheet("color:%s;font-size:%dpx;" % (theme.TEXT_MUTED, theme.FS_MICRO))
            top.addWidget(src)
            box.addLayout(top)
            ed = QLineEdit()
            ed.setPlaceholderText("空 = 用默认")
            ed.setToolTip(tip)
            ed.setFixedHeight(theme.CTRL_H)
            box.addWidget(ed)
            self.edits[key] = ed
            self.source_labels[key] = src
            holder = QWidget()
            holder.setLayout(box)
            grid.addWidget(holder, r, c)
        for c in range(columns):
            grid.setColumnStretch(c, 1)

    def set_values(self, values: dict, sources: dict | None = None) -> None:
        for key, ed in self.edits.items():
            v = values.get(key)
            ed.setText("" if v is None else ("%g" % float(v)))
            src = self.source_labels.get(key)
            if src is not None:
                src.setText((sources or {}).get(key, ""))

    def values(self) -> dict:
        out = {}
        for key, ed in self.edits.items():
            s = ed.text().strip()
            if not s:
                continue
            try:
                out[key] = int(float(s)) if key == "isolated_min_holes" else float(s)
            except ValueError:
                continue
        return out


# ---------------------------------------------------------------- 提示条

class Banner(QFrame):
    """页面顶部的说明/告警条。"""

    def __init__(self, text: str = "", tone: str = "info", parent=None):
        super().__init__(parent)
        fg, bg = _tone(tone)
        self.setStyleSheet("QFrame{background:%s;border:1px solid %s;border-radius:8px;}"
                           % (bg, theme.mix(bg, fg, 0.22)))
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 9, 12, 9)
        lay.setSpacing(9)
        self.icon = QLabel()
        self.icon.setFixedSize(16, 16)
        self.icon.setAlignment(Qt.AlignCenter)
        self.icon.setPixmap(icons.pixmap(
            {"ok": "check", "warn": "alert", "error": "x-circle"}.get(tone, "info"), fg, 16))
        self.icon.setStyleSheet("background:transparent;border:none;")
        lay.addWidget(self.icon, 0, Qt.AlignTop)
        self.label = QLabel(text)
        self.label.setWordWrap(True)
        self.label.setStyleSheet("color:%s;font-size:%dpx;background:transparent;border:none;"
                                 % (fg, theme.FS_SMALL))
        lay.addWidget(self.label, 1)

    def set_text(self, text: str) -> None:
        self.label.setText(text)


def _mix(color: str) -> str:
    return theme.mix(color, "#FFFFFF", 0.55)


def icon_button(name: str, text: str = "", kind: str = "", tip: str = "",
                on_click: Callable | None = None, color: str = theme.TEXT,
                size: int = theme.ICON_BTN) -> QPushButton:
    b = QPushButton(text)
    b.setIcon(icons.icon(name, "#FFFFFF" if kind in ("primary", "accent") else color, size))
    b.setIconSize(QSize(size, size))
    b.setFixedHeight(theme.BTN_PRIMARY_H if kind in ("primary", "accent") else theme.CTRL_H)
    if kind:
        b.setProperty("kind", kind)
    if tip:
        b.setToolTip(tip)
    b.setCursor(Qt.PointingHandCursor)
    if on_click:
        b.clicked.connect(on_click)
    return b


def tool_button(name: str, tip: str, on_click: Callable | None = None,
                color: str = theme.TEXT_MUTED) -> QToolButton:
    b = QToolButton()
    b.setIcon(icons.icon(name, color, theme.ICON_BTN))
    b.setIconSize(QSize(theme.ICON_BTN, theme.ICON_BTN))
    b.setFixedSize(26, 26)
    b.setToolTip(tip)
    b.setCursor(Qt.PointingHandCursor)
    if on_click:
        b.clicked.connect(on_click)
    return b


class Combo(QComboBox):
    """统一外观的下拉框：自绘 chevron，避免 QSS 覆盖后箭头丢失。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(theme.CTRL_H)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.setMinimumContentsLength(10)

    def paintEvent(self, _event) -> None:
        from PySide6.QtWidgets import QStyle, QStyleOptionComboBox, QStylePainter

        painter = QStylePainter(self)
        opt = QStyleOptionComboBox()
        self.initStyleOption(opt)
        painter.drawComplexControl(QStyle.CC_ComboBox, opt)
        # 文本由 CE_ComboBoxLabel 单独绘制（QComboBox::paintEvent 也是这么做的）
        painter.drawControl(QStyle.CE_ComboBoxLabel, opt)

        rect = self.style().subControlRect(QStyle.CC_ComboBox, opt,
                                           QStyle.SC_ComboBoxArrow, self)
        painter.fillRect(rect.adjusted(-3, -1, 0, 0), QColor(theme.CARD))
        pm = icons.pixmap("chevron-down", theme.TEXT_MUTED, 14)
        dpr = pm.devicePixelRatio() or 1.0
        w, h = pm.width() / dpr, pm.height() / dpr
        painter.drawPixmap(QPointF(rect.center().x() - w / 2 + 1,
                                   rect.center().y() - h / 2), pm)
        painter.end()


def combo(items: Iterable[tuple[str, str]] = (), parent=None) -> Combo:
    """``[(data, 文本), …]`` → 统一样式的下拉框。"""
    c = Combo(parent)
    for data, text in items:
        c.addItem(text, data)
    return c


class CheckRow(QCheckBox):
    """自绘勾选框：QSS 里设置 indicator 背景会吃掉勾，这里直接画。"""

    def __init__(self, text: str, checked: bool = True, hint: str = "", parent=None):
        super().__init__(text, parent)
        self.setChecked(checked)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)
        self._hover = False
        self.setStyleSheet("QCheckBox{background:transparent;}"
                           "QCheckBox::indicator{width:0;height:0;}")
        if hint:
            self.setToolTip(hint)

    def sizeHint(self) -> QSize:
        fm = self.fontMetrics()
        return QSize(22 + fm.horizontalAdvance(self.text()) + 4, 22)

    def enterEvent(self, _e) -> None:
        self._hover = True
        self.update()

    def leaveEvent(self, _e) -> None:
        self._hover = False
        self.update()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        checked = self.isChecked()
        enabled = self.isEnabled()
        box = QRect(0, (self.height() - 15) // 2, 15, 15)

        border = theme.BORDER_STRONG
        if checked:
            border = theme.PRIMARY if enabled else "#A9C3D3"
        elif self._hover and enabled:
            border = theme.FOCUS
        p.setPen(QPen(QColor(border), 1))
        p.setBrush(QColor("#FFFFFF" if not checked else (theme.PRIMARY if enabled
                                                        else "#A9C3D3")))
        p.drawRoundedRect(box.adjusted(0, 0, -1, -1), 3, 3)

        if checked:
            p.setPen(QPen(QColor("#FFFFFF"), 1.7, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawLine(box.left() + 4, box.top() + 8, box.left() + 6, box.top() + 10)
            p.drawLine(box.left() + 6, box.top() + 10, box.left() + 11, box.top() + 5)

        p.setPen(QColor(theme.TEXT_SUB if enabled else theme.TEXT_FAINT))
        p.setFont(self.font())
        text_rect = QRect(22, 0, max(0, self.width() - 24), self.height())
        text = self.fontMetrics().elidedText(self.text(), Qt.ElideRight, text_rect.width())
        p.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, text)
        p.end()


def expander(text: str = "高级参数") -> tuple[QPushButton, QWidget]:
    """返回 (切换按钮, 内容容器)；内容默认隐藏。"""
    holder = QWidget()
    btn = QPushButton(text)
    btn.setCheckable(True)
    btn.setProperty("kind", "ghost")
    btn.setCursor(Qt.PointingHandCursor)
    btn.setIcon(icons.icon("chevron", theme.PRIMARY_DARK, 14))
    btn.setIconSize(QSize(14, 14))

    def _toggle(on: bool) -> None:
        holder.setVisible(on)
        btn.setIcon(icons.icon("chevron-down" if on else "chevron", theme.PRIMARY_DARK, 14))

    btn.toggled.connect(_toggle)
    holder.setVisible(False)
    return btn, holder


# ---------------------------------------------------------------- 键值行

def kv_row(label: str, value: str, label_width: int = 92, mono: bool = False,
           elide: bool = False, tip: str = "") -> QWidget:
    row = QWidget()
    hl = QHBoxLayout(row)
    hl.setContentsMargins(0, 0, 0, 0)
    hl.setSpacing(10)
    a = QLabel(label)
    a.setObjectName("fieldLabel")
    a.setFixedWidth(label_width)
    b = QLabel(value)
    b.setObjectName("mono" if mono else "body")
    if not mono:
        b.setStyleSheet("font-size:%dpx;color:%s;" % (theme.FS_SMALL, theme.TEXT))
    b.setTextInteractionFlags(Qt.TextSelectableByMouse)
    if elide:
        b.setMinimumWidth(1)
        b.setWordWrap(False)
        b.setToolTip(tip or value)
    else:
        b.setWordWrap(True)
    hl.addWidget(a)
    hl.addWidget(b, 1)
    return row
