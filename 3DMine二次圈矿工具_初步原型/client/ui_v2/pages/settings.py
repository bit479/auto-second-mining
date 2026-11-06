# -*- coding: utf-8 -*-
"""系统设置：环境信息、路径、回退到旧版界面、清理记录。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QWidget

from .. import APP_NAME, APP_NAME_EN, APP_VERSION, theme
from ..components import widgets as W
from ..services import config, paths
from .base import Page


class SettingsPage(Page):
    TITLE = "系统设置"
    SUB = "环境信息 / 回退旧版 / 维护"

    def _build(self) -> None:
        info = W.Card("环境", "打包成 exe 后这些值会变")
        self.info_box = QVBoxLayout()
        self.info_box.setSpacing(5)
        info.add(self.info_box)
        self.add(info)

        fb = W.Card("回退与维护", "数据安全优先：这些按钮都不碰生产数据")
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(W.icon_button("external", "打开旧版界面", on_click=self.open_legacy))
        row.addWidget(W.icon_button("folder", "打开数据目录", kind="ghost",
                                    on_click=lambda: paths.open_path(paths.data_home())))
        row.addWidget(W.icon_button("file", "打开配置文件", kind="ghost",
                                    on_click=lambda: paths.open_path(paths.params_json())))
        row.addWidget(W.icon_button("refresh", "重建默认配置（先备份）", kind="ghost",
                                    on_click=self.restore_config))
        row.addWidget(W.icon_button("x", "清空最近记录", kind="ghost", on_click=self.clear_state))
        row.addStretch(1)
        fb.add(row)
        self.lb_msg = QLabel("")
        self.lb_msg.setObjectName("muted")
        self.lb_msg.setWordWrap(True)
        fb.add(self.lb_msg)
        self.add(fb)

        note = W.Card("关于界面", "")
        t = QLabel(
            "%s（%s）\n\n"
            "· 外框 #0E1B2A（标题栏/侧栏）、主色 #2A6F97（操作）、铜褐 #B0774A（品位强调）\n"
            "· 工作面 #F1F4F8，卡片 #FFFFFF，正文 #1B2735\n"
            "· 全部图标为内联 SVG 线性图标（24×24 网格、1.75 描边），不依赖外部图片\n"
            "· 品位分级颜色取自 grade_profiles.json，与成果图一致\n"
            "· 深色主题仅用于图形预览（成果图/预览 PNG 打开时的天然深色背景），主界面固定浅色\n"
            "· 高 DPI：按系统缩放自动适配（PassThrough 取整策略）"
            % (APP_NAME, APP_NAME_EN))
        t.setWordWrap(True)
        t.setStyleSheet("color:%s;line-height:150%%;" % theme.TEXT_MUTED)
        note.add(t)
        self.add(note)
        self.add_stretch()
        self._fill_info()

    def add_stretch(self) -> None:
        from PySide6.QtWidgets import QSpacerItem, QSizePolicy
        self.body.addItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))

    def on_show(self) -> None:
        self._fill_info()

    def _fill_info(self) -> None:
        while self.info_box.count():
            w = self.info_box.takeAt(0).widget()
            if w is not None:
                w.deleteLater()
        rows = [
            ("软件", "%s  %s" % (APP_NAME, APP_VERSION)),
            ("运行方式", "单文件 exe" if paths.is_frozen() else "源码（Python）"),
            ("解释器", sys.executable),
            ("程序目录", str(paths.app_dir())),
            ("可写数据目录", str(paths.data_home())),
            ("圈矿参数", str(paths.params_json())),
            ("品位分级配置", str(paths.grade_config())),
            ("Python 版本", sys.version.split()[0]),
            ("Qt 版本", _qt_version()),
        ]
        for k, v in rows:
            self.info_box.addWidget(_kv(k, v))
        # 动态加行之后要让布局重新算高度，否则卡片高度不跟着长（会压住下一块）
        self.info_box.invalidate()
        self.info_box.activate()
        self.content.adjustSize()

    # ------------------------------------------------------------ 动作

    def open_legacy(self) -> None:
        gui = paths.client_dir() / "gui.py"
        if not gui.exists():
            QMessageBox.information(self, "旧版界面", "找不到 client/gui.py。")
            return
        try:
            import subprocess

            subprocess.Popen([sys.executable, "-X", "utf8", str(gui)],
                             cwd=str(paths.bundle_root()), env=paths.child_env())
            self.lb_msg.setText("已启动旧版 Tkinter 界面（它与新界面共用同一份参数与成果目录）。")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "启动失败", str(exc))

    def restore_config(self) -> None:
        src = paths.bundle_root() / "圈矿参数.json"
        dst = paths.params_json()
        if not src.exists() or src.resolve() == dst.resolve():
            self.lb_msg.setText("当前就是源码目录，没有可重建的默认配置。")
            return
        if QMessageBox.question(self, "重建默认配置",
                                "将用包内默认 圈矿参数.json 覆盖：\n%s\n\n"
                                "当前文件会先备份成 圈矿参数.bak.json。继续？" % dst) != QMessageBox.Yes:
            return
        try:
            if dst.exists():
                dst.with_suffix(".bak.json").write_bytes(dst.read_bytes())
            dst.write_bytes(src.read_bytes())
            self.lb_msg.setText("已重建默认配置（原文件备份为 圈矿参数.bak.json）。")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "重建失败", str(exc))

    def clear_state(self) -> None:
        if QMessageBox.question(self, "清空最近记录",
                                "只清空界面上的「最近任务/最近成果」列表，不动任何成果文件。继续？") \
                != QMessageBox.Yes:
            return
        self.ctx.state.data["tasks"] = []
        self.ctx.state.data["outputs"] = []
        self.ctx.state.save()
        self.lb_msg.setText("已清空最近任务与成果列表。")
        self.ctx.changed.emit()


def _kv(k: str, v: str) -> QWidget:
    row = QWidget()
    hl = QHBoxLayout(row)
    hl.setContentsMargins(0, 0, 0, 0)
    hl.setSpacing(8)
    a = QLabel(k)
    a.setObjectName("fieldLabel")
    a.setFixedWidth(110)
    b = QLabel(v)
    b.setObjectName("mono")
    b.setWordWrap(True)
    b.setTextInteractionFlags(Qt.TextSelectableByMouse)
    hl.addWidget(a)
    hl.addWidget(b, 1)
    return row


def _qt_version() -> str:
    try:
        from PySide6 import QtCore

        return QtCore.qVersion()
    except Exception:
        return "—"
