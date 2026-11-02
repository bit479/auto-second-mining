# -*- coding: utf-8 -*-
"""公共组件：卡片、状态徽章、日志台、文件选择行、统计块、参数表。"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QFileDialog, QFrame, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QPlainTextEdit, QPushButton, QSizePolicy, QTableWidget,
    QTableWidgetItem, QToolButton, QVBoxLayout, QWidget,
)

from .. import icons, theme


# ---------------------------------------------------------------- 基础容器

class Card(QFrame):
    """白底圆角卡片，可选标题行。"""

    def __init__(self, title: str = "", subtitle: str = "", parent: QWidget | None = None,
                 tight: bool = False):
        super().__init__(parent)
        self.setObjectName("cardTight" if tight else "card")
        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(16, 14, 16, 14)
        self._outer.setSpacing(10)
        self.header = None
        if title:
            row = QHBoxLayout()
            row.setSpacing(8)
            self.title_label = QLabel(title)
            self.title_label.setObjectName("cardTitle")
            row.addWidget(self.title_label)
            self.sub_label = QLabel(subtitle)
            self.sub_label.setObjectName("muted")
            row.addWidget(self.sub_label)
            row.addStretch(1)
            self.header = row
            self._outer.addLayout(row)
        self.body = QVBoxLayout()
        self.body.setSpacing(8)
        self._outer.addLayout(self.body)

    def add(self, w) -> None:
        if isinstance(w, QWidget):
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
    """「① 输入数据」这种带序号的小标题。"""

    def __init__(self, no: str, title: str, hint: str = "", parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        badge = QLabel(no)
        badge.setObjectName("sectionNo")
        badge.setAlignment(Qt.AlignCenter)
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
            "QLabel{color:%s;background:%s;border-radius:10px;padding:2px 10px;"
            "font-size:12px;font-weight:600;}" % (fg, bg))


def _tone(tone: str) -> tuple[str, str]:
    return {
        "ok": (theme.SUCCESS, theme.SUCCESS_BG),
        "warn": (theme.WARNING, theme.WARNING_BG),
        "error": (theme.DANGER, theme.DANGER_BG),
        "info": (theme.PRIMARY_DARK, theme.PRIMARY_LIGHT),
        "muted": (theme.TEXT_MUTED, theme.NEUTRAL_BG),
    }.get(tone, (theme.TEXT_MUTED, theme.NEUTRAL_BG))


class Chip(QLabel):
    def __init__(self, text: str = "", primary: bool = False, parent=None):
        super().__init__(text, parent)
        self.setObjectName("chipPrimary" if primary else "chip")


# ---------------------------------------------------------------- 统计块

class StatTile(QFrame):
    def __init__(self, label: str, value: str = "—", hint: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("cardTight")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(2)
        self.value = QLabel(value)
        self.value.setObjectName("statValue")
        self.label = QLabel(label)
        self.label.setObjectName("statLabel")
        lay.addWidget(self.value)
        lay.addWidget(self.label)
        self.hint = QLabel(hint)
        self.hint.setObjectName("muted")
        self.hint.setVisible(bool(hint))
        lay.addWidget(self.hint)
        self.setMinimumWidth(140)

    def set_value(self, text: str, hint: str | None = None) -> None:
        self.value.setText(text)
        if hint is not None:
            self.hint.setText(hint)
            self.hint.setVisible(bool(hint))


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
        self.label.setFixedWidth(118)
        lay.addWidget(self.label)

        self.edit = QLineEdit()
        self.edit.setPlaceholderText(placeholder)
        self.edit.textChanged.connect(self._on_text)
        lay.addWidget(self.edit, 1)

        self.btn = QPushButton("浏览")
        self.btn.setIcon(icons.icon("folder", theme.TEXT_MUTED, 16))
        self.btn.clicked.connect(self.browse)
        self.btn.setVisible(browse)
        lay.addWidget(self.btn)

        self.state = QLabel("")
        self.state.setFixedWidth(18)
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
            self.state.setPixmap(icons.pixmap("info", theme.TEXT_MUTED, 15))
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

    def append_line(self, text: str) -> None:
        t = text.rstrip("\n")
        low = t.lower()
        color = theme.TEXT
        if "[错误]" in t or "[失败]" in t or "traceback" in low or "error" in low:
            color = theme.DANGER
        elif "[警告]" in t or "[提示]" in t or "[缺" in t:
            color = "#B2761E"
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


# ---------------------------------------------------------------- 表格

def make_table(headers: list[str], stretches: list[int] | None = None,
               height: int | None = None) -> QTableWidget:
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.verticalHeader().setVisible(False)
    t.setAlternatingRowColors(True)
    t.setSelectionBehavior(QAbstractItemView.SelectRows)
    t.setSelectionMode(QAbstractItemView.SingleSelection)
    t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.setShowGrid(False)
    t.setWordWrap(False)
    hh = t.horizontalHeader()
    hh.setSectionResizeMode(QHeaderView.Interactive)
    hh.setStretchLastSection(True)
    hh.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    hh.setHighlightSections(False)
    if stretches:
        for i, w in enumerate(stretches):
            t.setColumnWidth(i, w)
    t.verticalHeader().setDefaultSectionSize(30)
    if height:
        t.setMinimumHeight(height)
    return t


def cell(text, color: str | None = None, bold: bool = False, align=None) -> QTableWidgetItem:
    item = QTableWidgetItem("" if text is None else str(text))
    if color:
        from PySide6.QtGui import QColor
        item.setForeground(QColor(color))
    if bold:
        f = item.font()
        f.setBold(True)
        item.setFont(f)
    if align is not None:
        item.setTextAlignment(align)
    item.setToolTip("" if text is None else str(text))
    return item


# ---------------------------------------------------------------- 参数编辑

class ParamGrid(QWidget):
    """参数编辑格：标签 + 输入 + "来源"角标（全局/平台/炮区）。"""

    def __init__(self, specs: Iterable[tuple], columns: int = 3, parent=None):
        super().__init__(parent)
        from PySide6.QtWidgets import QGridLayout

        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(8)
        self.edits: dict[str, QLineEdit] = {}
        self.source_labels: dict[str, QLabel] = {}
        for i, (key, cn, unit, is_int, tip) in enumerate(specs):
            r, c = divmod(i, columns)
            box = QVBoxLayout()
            box.setSpacing(2)
            top = QHBoxLayout()
            top.setSpacing(4)
            lab = QLabel(cn + ("（%s）" % unit if unit else ""))
            lab.setObjectName("fieldLabel")
            top.addWidget(lab)
            src = QLabel("")
            src.setStyleSheet("color:%s;font-size:10px;" % theme.TEXT_MUTED)
            top.addWidget(src)
            top.addStretch(1)
            box.addLayout(top)
            ed = QLineEdit()
            ed.setPlaceholderText("空=用默认")
            ed.setToolTip(tip)
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
                           % (bg, _mix(fg)))
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(8)
        self.icon = QLabel()
        self.icon.setPixmap(icons.pixmap({"ok": "check", "warn": "alert", "error": "x"}.get(tone, "info"), fg, 16))
        lay.addWidget(self.icon)
        self.label = QLabel(text)
        self.label.setWordWrap(True)
        self.label.setStyleSheet("color:%s;font-size:12px;border:none;" % fg)
        lay.addWidget(self.label, 1)

    def set_text(self, text: str) -> None:
        self.label.setText(text)


def _mix(color: str) -> str:
    """把前景色调淡，做边框（简单的往白色插值）。"""
    try:
        c = color.lstrip("#")
        r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
        f = 0.55
        r, g, b = (int(v + (255 - v) * f) for v in (r, g, b))
        return "#%02X%02X%02X" % (r, g, b)
    except Exception:
        return theme.BORDER


def icon_button(name: str, text: str = "", kind: str = "", tip: str = "",
                on_click: Callable | None = None, color: str = theme.TEXT) -> QPushButton:
    b = QPushButton(text)
    b.setIcon(icons.icon(name, "#FFFFFF" if kind == "primary" else color, 16))
    b.setIconSize(QSize(16, 16))
    if kind:
        b.setProperty("kind", kind)
    if tip:
        b.setToolTip(tip)
    if on_click:
        b.clicked.connect(on_click)
    return b


def tool_button(name: str, tip: str, on_click: Callable | None = None,
                color: str = theme.TEXT_MUTED) -> QToolButton:
    b = QToolButton()
    b.setIcon(icons.icon(name, color, 16))
    b.setIconSize(QSize(16, 16))
    b.setToolTip(tip)
    b.setCursor(Qt.PointingHandCursor)
    if on_click:
        b.clicked.connect(on_click)
    return b


class CheckRow(QCheckBox):
    def __init__(self, text: str, checked: bool = True, hint: str = "", parent=None):
        super().__init__(text, parent)
        self.setChecked(checked)
        if hint:
            self.setToolTip(hint)


def expander() -> tuple[QPushButton, QWidget]:
    """返回 (切换按钮, 内容容器)；内容默认隐藏。"""
    holder = QWidget()
    btn = QPushButton("高级参数")
    btn.setCheckable(True)
    btn.setProperty("kind", "ghost")
    btn.setIcon(icons.icon("chevron", theme.PRIMARY_DARK, 14))

    def _toggle(on: bool) -> None:
        holder.setVisible(on)
        btn.setIcon(icons.icon("chevron", theme.PRIMARY_DARK, 14))

    btn.toggled.connect(_toggle)
    holder.setVisible(False)
    return btn, holder
