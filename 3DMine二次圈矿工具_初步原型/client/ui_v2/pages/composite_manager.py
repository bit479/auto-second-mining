# -*- coding: utf-8 -*-
"""综合图管理：只读扫描 / 生成合并副本 / 谨慎替换原件（二次确认 + 自动备份）。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QWidget

from ..components import widgets as W
from ..services import config, files, paths
from .base import Page


class _ScanSignals(QObject):
    done = Signal(int, float, str)


class _ScanJob(QRunnable):
    def __init__(self, dwg: str):
        super().__init__()
        self.dwg = dwg
        self.sig = _ScanSignals()

    def run(self) -> None:
        try:
            comp = config.core_module("composite")
            blocks = comp.load_composite_blocks(Path(self.dwg))
            area = 0.0
            for item in blocks:
                poly = item[-1] if isinstance(item, (tuple, list)) else item
                try:
                    area += float(poly.area)
                except Exception:
                    continue
            self.sig.done.emit(len(blocks), area, "")
        except Exception as exc:      # noqa: BLE001
            self.sig.done.emit(0, 0.0, str(exc))


class CompositeManagerPage(Page):
    TITLE = "综合图管理"
    SUB = "只读扫描 → 生成副本 → 确认后替换（自动备份）"

    def _build(self) -> None:
        self.pool = QThreadPool.globalInstance()
        self.runner.finished.connect(self._on_finished)

        card = W.Card()
        card.add(W.SectionTitle("1", "平台综合图", "只读扫描历史矿块"))
        self.row_comp = W.FileRow("综合图 DWG", "如 …二次圈矿矿块图-2026综合.dwg",
                                  file_filter="DWG (*.dwg)", title="选择综合图")
        card.add(self.row_comp)
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(W.icon_button("refresh", "只读扫描历史矿块", on_click=self.scan))
        row.addWidget(W.icon_button("image", "打开预览图", kind="ghost", on_click=self.open_preview))
        row.addWidget(W.icon_button("folder", "打开所在目录", kind="ghost",
                                    on_click=lambda: paths.open_path(Path(self.row_comp.value()).parent)))
        row.addStretch(1)
        card.add(row)
        self.lb_scan = QLabel("还没有扫描。")
        self.lb_scan.setObjectName("muted")
        card.add(self.lb_scan)
        self.add(card)

        mcard = W.Card()
        mcard.add(W.SectionTitle("2", "生成本次合并副本", "原件不动，只出新副本 + 预览 PNG"))
        self.row_tds = W.FileRow("矿块边界线 .3ds", "一般在该炮区成果目录里",
                                 file_filter="3DS (*.3ds)", title="选择 .3ds")
        mcard.add(self.row_tds)
        mrow = QHBoxLayout()
        mrow.setSpacing(8)
        mrow.addWidget(W.icon_button("layers", "生成合并副本", kind="primary", on_click=self.merge_copy))
        mrow.addWidget(W.icon_button("folder", "打开成果目录", kind="ghost",
                                     on_click=lambda: paths.open_path(Path(self.row_tds.value()).parent)))
        mrow.addStretch(1)
        mcard.add(mrow)
        self.banner = W.Banner("合并只在副本上做，原件不改。副本文件名形如 …_并入<日期>.dwg。", "info")
        mcard.add(self.banner)
        self.add(mcard)

        dcard = W.Card()
        dcard.add(W.SectionTitle("3", "替换原件（危险操作）", "先备份原件，再覆盖；可回退"))
        self.row_merged = W.FileRow("要启用的副本 DWG", "选 …_并入<日期>.dwg",
                                    file_filter="DWG (*.dwg)", title="选择合并后的副本")
        dcard.add(self.row_merged)
        self.banner_danger = W.Banner(
            "替换前会：① 把原综合图改名备份成 «原名_原版_时间戳.dwg»；② 把副本复制成原综合图的名字。"
            "出问题把备份改回原名即可回退。", "warn")
        dcard.add(self.banner_danger)
        drow = QHBoxLayout()
        drow.setSpacing(8)
        btn = W.icon_button("alert", "确认替换综合图原件…", kind="danger", on_click=self.replace)
        drow.addWidget(btn)
        drow.addStretch(1)
        dcard.add(drow)
        self.add(dcard)

        lc = W.Card("日志", "")
        self.log = W.LogView()
        self.log.setMinimumHeight(160)
        lc.add(self.log)
        lc.add(W.icon_button("save", "另存日志", kind="ghost", on_click=self._save_log))
        self.add(lc)

    def on_show(self) -> None:
        if self.ctx.comp and not self.row_comp.value():
            self.row_comp.set_value(self.ctx.comp)

    # ------------------------------------------------------------ 扫描

    def scan(self) -> None:
        dwg = self.row_comp.value()
        if not Path(dwg).is_file():
            QMessageBox.information(self, "扫描", "先选综合图 DWG。")
            return
        self.log.append_line("[扫描] %s（只读，AutoCAD 未开时也能用缓存）" % Path(dwg).name)
        job = _ScanJob(dwg)
        job.sig.done.connect(self._on_scan)
        self.pool.start(job)

    def _on_scan(self, count: int, area: float, err: str) -> None:
        if err:
            self.lb_scan.setText("扫描失败：%s" % err)
            self.log.append_line("[警告] %s" % err)
            return
        self.lb_scan.setText("历史矿块 %d 个，面积合计 %.2f m²" % (count, area))
        self.log.append_line("[扫描] 历史矿块 %d 个，面积合计 %.2f m²" % (count, area))

    def open_preview(self) -> None:
        dwg = Path(self.row_comp.value())
        for pat in ("*_预览.png", "*预览*.png"):
            for p in dwg.parent.glob(pat):
                paths.open_path(p)
                return
        QMessageBox.information(self, "预览", "没找到预览 PNG（合并后会自动生成同名 _预览.png）。")

    # ------------------------------------------------------------ 合并副本

    def merge_copy(self) -> None:
        comp = self.row_comp.value()
        tds = self.row_tds.value()
        if not Path(comp).is_file():
            QMessageBox.information(self, "合并", "先选综合图 DWG。")
            return
        if not Path(tds).is_file():
            QMessageBox.information(self, "合并", "先选当天的矿块边界线 .3ds。")
            return
        args = [comp, tds, "--start"]
        if self.ctx.section != "auto":
            args += ["--grades", self.ctx.section]
        self.log.append_line("== 生成合并副本 ==")
        self._tid_merge = self.runner.run("并入综合图副本", "core/merge_to_composite.py", args,
                                          key="merge_comp", cwd=str(paths.bundle_root()))

    # ------------------------------------------------------------ 替换原件

    def replace(self) -> None:
        merged = self.row_merged.value()
        if not Path(merged).is_file():
            QMessageBox.information(self, "替换原件", "先选「并入后的副本」DWG。")
            return
        ok = QMessageBox.warning(
            self, "确认替换原件",
            "将执行：\n"
            "① 原综合图改名备份为 «原名_原版_时间戳.dwg»（不删除）\n"
            "② 把\n  %s\n复制成原综合图的名字\n"
            "③ 出问题把备份改回原名即可回退\n\n确认继续？" % Path(merged).name,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if ok != QMessageBox.Yes:
            self.log.append_line("[取消] 未替换原件")
            return
        self.log.append_line("== 替换原件：%s ==" % Path(merged).name)
        self._tid_replace = self.runner.run("替换综合图原件", "core/apply_merge.py", [merged],
                                            key="apply_merge", cwd=str(paths.bundle_root()))

    # ------------------------------------------------------------ 日志

    def _on_finished(self, tid: str, code: int) -> None:
        if tid in (getattr(self, "_tid_merge", None), getattr(self, "_tid_replace", None)):
            self.log.append_line("[结束] 退出码 %s" % code)
            if code == 0:
                self.banner.set_text("完成。副本已生成/原件已替换（备份见日志）。")
            else:
                self.banner.set_text("未成功，详见日志（常见原因：AutoCAD 起不来或停在对话框）。")

    def _save_log(self) -> None:
        p = Path(self.row_comp.value() or ".").parent / "综合图操作日志.txt"
        p.write_text(self.log.plain(), encoding="utf-8")
        self.lb_scan.setText("日志已保存：%s" % p)
