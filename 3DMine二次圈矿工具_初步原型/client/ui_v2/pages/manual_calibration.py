# -*- coding: utf-8 -*-
"""人工圈矿与参数标定：人工图 vs 自动结果对比 + 自动标定（写参数前必须确认）。"""

from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from PySide6.QtWidgets import (
    QFileDialog, QGridLayout, QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QWidget,
)

from .. import theme
from ..components import widgets as W
from ..services import files, paths
from .base import Page


class _ScanSignals(QObject):
    done = Signal(int, float, str)      # 块数, 面积合计, 错误


class _ScanJob(QRunnable):
    """在后台读人工图里的块轮廓（AutoCAD COM，只读）。"""

    def __init__(self, dwg: str):
        super().__init__()
        self.dwg = dwg
        self.sig = _ScanSignals()

    def run(self) -> None:
        try:
            from ..services import config
            comp = config.core_module("composite")
            blocks = comp.load_composite_blocks(Path(self.dwg))
            if not blocks:
                self.sig.done.emit(0, 0.0, "人工图里没读到块轮廓（可能是空图，或 AutoCAD 不可用）")
                return
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


class ManualCalibrationPage(Page):
    TITLE = "人工圈矿与参数标定"
    SUB = "人工结果 vs 自动结果；标定写参数前必确认"

    def __init__(self, parent=None):
        self.manual_blocks = 0
        self.manual_area = 0.0
        self.auto_stats: dict[str, float] = {}
        super().__init__(parent)

    def _build(self) -> None:
        self.pool = QThreadPool.globalInstance()
        self.runner.finished.connect(self._on_finished)

        card = W.Card()
        card.add(W.SectionTitle("1", "输入", "人工图 = 该炮区在 CAD 里画好的矿块图（.dwg）"))
        self.row_xls = W.FileRow("炮孔数据库 Excel", "与单炮区页共用：在这里选也会同步",
                                 file_filter="Excel (*.xls *.xlsx)", title="选择数据库")
        self.row_xls.changed.connect(self._on_xls)
        card.add(self.row_xls)
        self.row_dwg = W.FileRow("人工圈矿图 DWG", "人工画的矿块图（只读扫描，不改它）",
                                 file_filter="DWG (*.dwg)", title="选择人工圈矿图")
        card.add(self.row_dwg)
        self.row_comp = W.FileRow("平台综合图 DWG", "自动圈矿要用的综合图",
                                  file_filter="DWG (*.dwg)", title="选择综合图")
        card.add(self.row_comp)
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(W.icon_button("refresh", "读取人工图块", on_click=self.scan_manual))
        row.addWidget(W.icon_button("pick", "自动标定（演练，不写参数）", on_click=lambda: self.calibrate(False)))
        row.addWidget(W.icon_button("save", "自动标定并写入参数", kind="accent",
                                    on_click=lambda: self.calibrate(True)))
        row.addWidget(W.icon_button("play", "跑一次自动圈矿", on_click=self.run_auto))
        row.addStretch(1)
        card.add(row)
        self.banner = W.Banner("提示：标定会用人工图反推「外推距离 + 左右链」，写入的是 "
                              "圈矿参数.json 的 blasts[平台-炮区]，不会动其它炮区。", "info")
        card.add(self.banner)
        self.add(card)

        row2 = QHBoxLayout()
        row2.setSpacing(14)
        left = QVBoxLayout()
        left.setSpacing(10)
        right = QVBoxLayout()
        right.setSpacing(10)
        row2.addLayout(left, 1)
        row2.addLayout(right, 1)
        self.add(row2)

        self.card_manual = W.Card("人工圈矿结果", "只读自人工 DWG")
        self.manual_box = QVBoxLayout()
        self.manual_box.setSpacing(4)
        self.card_manual.add(self.manual_box)
        self._manual_hint = QLabel("还没有读取人工图 —— 选好 DWG 后点「读取人工图块」。")
        self._manual_hint.setObjectName("muted")
        self.manual_box.addWidget(self._manual_hint)
        left.addWidget(self.card_manual)
        left.addStretch(1)

        self.card_auto = W.Card("程序自动圈矿结果", "来自成果报告 xlsx")
        self.auto_box = QVBoxLayout()
        self.auto_box.setSpacing(4)
        self.card_auto.add(self.auto_box)
        self._auto_hint = QLabel("还没有自动结果 —— 点「跑一次自动圈矿」，或选已有成果报告。")
        self._auto_hint.setObjectName("muted")
        self.auto_box.addWidget(self._auto_hint)
        right.addWidget(self.card_auto)
        right.addStretch(1)

        cc = W.Card("对比", "能算的才显示，缺数据留 —")
        self.tb = W.make_table(["指标", "人工", "自动", "差异"], [170, 150, 160], 300)
        cc.add(self.tb)
        self.add(cc)

        lc = W.Card("标定日志", "")
        self.log = W.LogView()
        self.log.setMinimumHeight(150)
        lc.add(self.log)
        self.add(lc)
        self._fill_compare()

    # ------------------------------------------------------------ 输入

    def on_show(self) -> None:
        if self.ctx.xls and not self.row_xls.value():
            self.row_xls.set_value(self.ctx.xls)
        if self.ctx.comp and not self.row_comp.value():
            self.row_comp.set_value(self.ctx.comp)

    def _on_xls(self, text: str) -> None:
        p = Path(text.strip())
        if p.is_file():
            self.ctx.set_xls(p)
            if not self.row_comp.value() and self.ctx.comp:
                self.row_comp.set_value(self.ctx.comp)

    def _plat_date(self) -> tuple[str, str]:
        p = Path(self.row_xls.value())
        plat, date = files.parse_platform_date(p.name)
        return plat or self.ctx.platform, date or self.ctx.date

    # ------------------------------------------------------------ 人工图

    def scan_manual(self) -> None:
        dwg = self.row_dwg.value()
        if not Path(dwg).is_file():
            QMessageBox.information(self, "读取人工图", "先选一张人工圈矿图 DWG。")
            return
        self.log.append_line("[读取] 人工图 %s（只读扫描，通常几秒）" % Path(dwg).name)
        job = _ScanJob(dwg)
        job.sig.done.connect(self._on_scan_done)
        self.pool.start(job)

    def _on_scan_done(self, count: int, area: float, err: str) -> None:
        self.manual_blocks, self.manual_area = count, area
        if err:
            self.log.append_line("[警告] %s" % err)
        else:
            self.log.append_line("[读取] 人工图 %d 块，矿块面积合计 %.2f m²" % (count, area))
        self._fill_manual()
        self._fill_compare()

    def _fill_manual(self) -> None:
        _clear(self.manual_box)
        rows = [("矿块数量", "%d 块" % self.manual_blocks if self.manual_blocks else "—"),
                ("矿块面积合计", "%.2f m²" % self.manual_area if self.manual_area else "—")]
        for k, v in rows:
            self.manual_box.addWidget(_kv(k, v))

    # ------------------------------------------------------------ 自动

    def run_auto(self) -> None:
        xls = self.row_xls.value()
        comp = self.row_comp.value()
        if not Path(xls).is_file():
            QMessageBox.information(self, "自动圈矿", "先选炮孔数据库。")
            return
        plat, date = self._plat_date()
        if not (plat and date):
            QMessageBox.information(self, "自动圈矿", "平台/日期没识别出来，请先在「单炮区」页填好。")
            return
        out = self.ctx.out_dir or str(files.default_out_dir(Path(xls), plat, date))
        args = [xls, plat, date, out, comp] if comp else [xls, plat, date, out]
        if self.ctx.section != "auto":
            args += ["--grades", self.ctx.section]
        self._auto_plat, self._auto_date, self._auto_out = plat, date, Path(out)
        self.log.append_line("== 自动圈矿（用于对比）==")
        self._tid = self.runner.run("标定用自动圈矿", "core/run_strip.py", args,
                                    key="run_strip", cwd=str(paths.bundle_root()))

    def _on_finished(self, tid: str, code: int) -> None:
        if tid == getattr(self, "_tid_cal", None):
            self._on_calibrate_done(code)
            return
        if tid != getattr(self, "_tid", None):
            return
        if code != 0:
            self.log.append_line("[失败] 自动圈矿退出码 %s" % code)
            return
        p = files.output_paths(self._auto_out, self._auto_plat, self._auto_date)["xlsx"]
        self._read_report(p)

    def _read_report(self, xlsx: Path) -> None:
        try:
            from openpyxl import load_workbook

            ws = load_workbook(xlsx, data_only=True).active
            blocks, volume, tonnage, metal = 0, 0.0, 0.0, 0.0
            for row in ws.iter_rows(min_row=3, max_col=6, values_only=True):
                if not row or not isinstance(row[2], (int, float)):
                    continue
                if str(row[0]).strip() in ("小计", "合计", "总计"):
                    continue
                blocks += 1
                volume += float(row[2] or 0)
                tonnage += float(row[3] or 0)
                metal += float(row[5] or 0)
            grade = (metal * 100.0 / tonnage) if tonnage else 0.0
            self.auto_stats = {"blocks": blocks, "volume": volume, "tonnage": tonnage,
                               "grade": grade, "metal": metal}
            self.log.append_line("[读取] 自动成果：%d 块 / %.1f m³ / %.1f t / %.3f g/t / %.3f 百克"
                                 % (blocks, volume, tonnage, grade, metal))
            self._fill_auto()
            self._fill_compare()
        except Exception as exc:      # noqa: BLE001
            self.log.append_line("[警告] 读报告失败：%s" % exc)

    def _fill_auto(self) -> None:
        _clear(self.auto_box)
        s = self.auto_stats
        if not s:
            self.auto_box.addWidget(_kv("状态", "还没有跑过自动圈矿"))
            return
        for k, v in (("矿块数量", "%d 块" % s["blocks"]),
                     ("体积", "%.2f m³" % s["volume"]),
                     ("重量", "%.2f t" % s["tonnage"]),
                     ("平均品位", "%.3f g/t" % s["grade"]),
                     ("金属量", "%.3f 百克" % s["metal"])):
            self.auto_box.addWidget(_kv(k, v))

    # ------------------------------------------------------------ 对比表

    def _fill_compare(self) -> None:
        rows: list[tuple[str, str, str, str]] = []
        s = self.auto_stats
        rows.append(("矿块数量", "%d 块" % self.manual_blocks if self.manual_blocks else "—",
                     "%d 块" % s["blocks"] if s else "—", "—"))
        rows.append(("矿块面积合计", "%.2f m²" % self.manual_area if self.manual_area else "—",
                     "—（报告里不含面积）", "—"))
        rows.append(("体积", "—", "%.2f m³" % s["volume"] if s else "—", "—"))
        rows.append(("重量", "—", "%.2f t" % s["tonnage"] if s else "—", "—"))
        rows.append(("平均品位", "—", "%.3f g/t" % s["grade"] if s else "—", "—"))
        rows.append(("金属量", "—", "%.3f 百克" % s["metal"] if s else "—", "—"))
        self.tb.setRowCount(0)
        for i, (a, b, c, d) in enumerate(rows):
            self.tb.insertRow(i)
            self.tb.setItem(i, 0, W.cell(a, bold=True))
            self.tb.setItem(i, 1, W.cell(b))
            self.tb.setItem(i, 2, W.cell(c))
            self.tb.setItem(i, 3, W.cell(d, theme.TEXT_MUTED))

    # ------------------------------------------------------------ 标定

    def calibrate(self, write: bool) -> None:
        dwg = self.row_dwg.value()
        if not Path(dwg).is_file():
            QMessageBox.information(self, "标定", "先选人工圈矿图 DWG。")
            return
        plat, date = self._plat_date()
        if not (plat and date):
            QMessageBox.information(self, "标定", "平台/日期没识别出来。")
            return
        if write:
            ok = QMessageBox.question(
                self, "确认写参数",
                "标定结果将写入 圈矿参数.json 的 blasts[\"%s-%s\"]：\n"
                " · extrude_m（外推距离）\n · chain_left / chain_right（左右链孔号）\n\n"
                "只会改这个炮区的这几个键，其它炮区与平台参数不动。\n继续？" % (plat, date),
                QMessageBox.Yes | QMessageBox.No)
            if ok != QMessageBox.Yes:
                return
        args = [date, dwg, "--platform", plat] + (["--write"] if write else [])
        self.log.append_line("== 标定 %s-%s（%s）==" % (plat, date, "写入参数" if write else "只演练"))
        self._tid_cal = self.runner.run("人工图标定", "core/calibrate.py", args,
                                        key="calibrate", cwd=str(paths.bundle_root()))

    def _on_calibrate_done(self, code: int) -> None:
        if code == 0:
            self.banner.set_text("标定完成。若是演练，满意后再点「自动标定并写入参数」。")
        else:
            self.banner.set_text("标定未成功，见下方日志（常见原因：找不到该炮区的数据库目录、"
                                 "或 AutoCAD 不可用）。")


def _kv(k: str, v: str) -> QWidget:
    row = QWidget()
    hl = QHBoxLayout(row)
    hl.setContentsMargins(0, 0, 0, 0)
    hl.setSpacing(8)
    a = QLabel(k)
    a.setObjectName("fieldLabel")
    a.setFixedWidth(96)
    b = QLabel(v)
    hl.addWidget(a)
    hl.addWidget(b, 1)
    return row


def _clear(layout) -> None:
    while layout.count():
        w = layout.takeAt(0).widget()
        if w is not None:
            w.deleteLater()
