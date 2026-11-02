# -*- coding: utf-8 -*-
"""炮孔数据库生成：坐标 TXT + 粘贴品位表 → .xls / .mdb（模板与字段完全沿用原有实现）。"""

from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QVBoxLayout, QWidget,
)

from .. import theme
from ..components import widgets as W
from ..services import config, files, paths
from .base import Page

SAMPLE = """工程号\tAu
BS-3940-0915-P1\t1.23
BS-3940-0915-P2\t0.86
…（直接从 Excel 复制两列粘进来即可，制表符/逗号/空格分隔都认）"""


class DatabaseBuilderPage(Page):
    TITLE = "炮孔数据库生成"
    SUB = "坐标 TXT + 品位表 → .xls / .mdb（口径不变）"

    def _build(self) -> None:
        self.runner.finished.connect(self._on_finished)

        card = W.Card()
        card.add(W.SectionTitle("1", "坐标与品位", "TXT 里是「工程号,,E,N,R」；品位表两列"))
        self.row_txt = W.FileRow("坐标 TXT", "如 BS-3940-0915-P1-P47.txt / 3570取样1023.txt",
                                 file_filter="文本 (*.txt *.dat)", title="选择坐标 TXT")
        self.row_txt.changed.connect(self._on_txt)
        card.add(self.row_txt)

        lbl = QLabel("品位表（粘贴）")
        lbl.setObjectName("fieldLabel")
        card.add(lbl)
        self.paste = QPlainTextEdit()
        self.paste.setObjectName("paste")
        self.paste.setPlaceholderText(SAMPLE)
        self.paste.setMinimumHeight(150)
        card.add(self.paste)
        self.add(card)

        info = W.Card()
        info.add(W.SectionTitle("2", "参数", "平台/日期从文件名或第一行工程号自动识别"))
        row = QHBoxLayout()
        row.setSpacing(10)
        row.addWidget(_lab("平台高程"))
        self.ed_plat = QLineEdit()
        self.ed_plat.setFixedWidth(90)
        row.addWidget(self.ed_plat)
        row.addWidget(_lab("日期/炮区号"))
        self.ed_date = QLineEdit()
        self.ed_date.setFixedWidth(90)
        row.addWidget(self.ed_date)
        row.addWidget(_lab("台阶高度(m)"))
        self.ed_bench = QLineEdit("10")
        self.ed_bench.setFixedWidth(70)
        row.addWidget(self.ed_bench)
        row.addStretch(1)
        info.add(row)
        self.row_out = W.FileRow("输出目录", "留空 = TXT 同目录", mode="dir",
                                 title="选择输出目录", must_exist=False)
        info.add(self.row_out)
        self.add(info)

        run = QHBoxLayout()
        run.setSpacing(8)
        run.addWidget(W.icon_button("refresh", "解析预览", on_click=self.preview))
        self.btn_make = W.icon_button("database", "生成 .xls / .mdb", kind="primary", on_click=self.make)
        self.btn_make.setMinimumHeight(36)
        run.addWidget(self.btn_make)
        run.addStretch(1)
        self.lb_state = QLabel("")
        self.lb_state.setObjectName("muted")
        run.addWidget(self.lb_state)
        self.add(run)

        tcard = W.Card("解析预览", "只显示前 200 行")
        self.tb = W.make_table(["工程号", "E", "N", "R", "Au"], [190, 120, 120, 110, 90], 240)
        tcard.add(self.tb)
        self.lb_check = QLabel("还没有解析。")
        self.lb_check.setObjectName("muted")
        self.lb_check.setWordWrap(True)
        tcard.add(self.lb_check)
        self.add(tcard)

        lc = W.Card("日志", "")
        self.log = W.LogView()
        self.log.setMinimumHeight(120)
        lc.add(self.log)
        self.add(lc)

    # ------------------------------------------------------------ 交互

    def _on_txt(self, text: str) -> None:
        p = Path(text.strip())
        if not p.is_file():
            return
        plat, date = files.parse_platform_date(p.name)
        try:
            # 以原工具的解析为准（会读第一条工程号，比只看文件名可靠）：
            # 3570取样1023.txt 里 plat/date 要的是 3570/1023，别把 3570 当日期。
            md = config.core_module("make_database")
            p2, d2 = md.parse_tag_from_txt(p)
            if p2 and d2:
                plat, date = p2, d2
            else:
                plat, date = plat or p2, date or d2
        except Exception:
            pass
        self.ed_plat.setText(plat)
        self.ed_date.setText(date)
        if not self.row_out.value():
            self.row_out.set_value(str(p.parent))
        if not self.paste.toPlainText().strip():
            self.lb_check.setText("已识别：平台 %s / 日期 %s。把 Excel 里的工程号+品位两列粘到上面。"
                                  % (plat or "?", date or "?"))

    def _parse(self):
        md = config.core_module("make_database")
        txt = Path(self.row_txt.value())
        if not txt.is_file():
            raise ValueError("先选坐标 TXT")
        holes = md.parse_txt(txt)
        grades = md.parse_grades(self.paste.toPlainText(), holes)
        return holes, grades

    def preview(self) -> None:
        try:
            holes, grades = self._parse()
        except Exception as exc:
            QMessageBox.warning(self, "解析失败", str(exc))
            return
        self.tb.setRowCount(0)
        for i, h in enumerate(holes[:200]):
            g = grades.grades.get(h.hid)
            self.tb.insertRow(i)
            self.tb.setItem(i, 0, W.cell(h.hid))
            self.tb.setItem(i, 1, W.cell("%.3f" % h.e, theme.TEXT_MUTED))
            self.tb.setItem(i, 2, W.cell("%.3f" % h.n, theme.TEXT_MUTED))
            self.tb.setItem(i, 3, W.cell("%.3f" % h.r, theme.TEXT_MUTED))
            self.tb.setItem(i, 4, W.cell("—" if g is None else "%.*f" % (grades.decimals, g),
                                         theme.DANGER if g is None else theme.TEXT, g is None))
        msgs = ["TXT %d 孔；品位表 %d 行、匹配 %d 孔"
                % (len(holes), grades.n_rows, len(grades.grades))]
        if grades.missing:
            msgs.append("缺品位 %d 个：%s" % (len(grades.missing), "、".join(grades.missing[:8])))
        if grades.extra:
            msgs.append("多出 %d 个（会被忽略）：%s" % (len(set(grades.extra)),
                                                     "、".join(sorted(set(grades.extra))[:8])))
        if grades.duplicates:
            msgs.append("同一工程号品位冲突：%s" % "；".join(grades.duplicates[:5]))
        if not grades.missing and not grades.duplicates:
            msgs.append("✓ 品位表与 TXT 工程号完全对应")
        self.lb_check.setText(" ｜ ".join(msgs))
        self.lb_check.setStyleSheet("color:%s;" % (
            theme.SUCCESS if not grades.missing and not grades.duplicates else theme.WARNING))
        self.log.append_line("[解析] " + msgs[0])
        for m in msgs[1:]:
            self.log.append_line("        " + m)

    def make(self) -> None:
        try:
            holes, grades = self._parse()
        except Exception as exc:
            QMessageBox.warning(self, "解析失败", str(exc))
            return
        if grades.missing:
            QMessageBox.warning(self, "品位表不全",
                                "缺少 %d 个工程号：\n%s" % (len(grades.missing),
                                                         "、".join(grades.missing[:20])))
            return
        if grades.duplicates:
            QMessageBox.warning(self, "品位冲突", "同一工程号出现不同品位：\n%s"
                                % "；".join(grades.duplicates[:8]))
            return
        plat = self.ed_plat.text().strip()
        date = self.ed_date.text().strip()
        if not (plat and date):
            QMessageBox.information(self, "缺平台/日期", "请填写平台高程和日期编号。")
            return
        txt = Path(self.row_txt.value())
        out = Path(self.row_out.value() or txt.parent)
        out.mkdir(parents=True, exist_ok=True)
        exist = [p.name for p in (out / ("1、%s平台 炮孔数据库%s.xls" % (plat, date)),
                                  out / ("2、%s平台炮孔数据库%s.mdb" % (plat, date))) if p.exists()]
        force = False
        if exist:
            if QMessageBox.question(self, "文件已存在",
                                    "以下文件已存在：\n%s\n\n先备份到 bak\\ 再覆盖？"
                                    % "\n".join(exist)) != QMessageBox.Yes:
                return
            force = True
        tmp = Path(tempfile.gettempdir()) / ("sm_grades_%s.txt" % date)
        tmp.write_text(self.paste.toPlainText(), encoding="utf-8")
        args = [str(txt), "--grades-file", str(tmp), "--out-dir", str(out),
                "--platform", plat, "--date", date,
                "--bench-height", self.ed_bench.text().strip() or "10"]
        if force:
            args.append("--force")
        self.log.append_line("== 生成炮孔数据库（%s 孔）==" % len(holes))
        self.lb_state.setText("正在生成…")
        self._tid = self.runner.run("生成炮孔数据库", "core/make_database.py", args,
                                    key="make_db", cwd=str(paths.bundle_root()))

    def _on_finished(self, tid: str, code: int) -> None:
        if tid != getattr(self, "_tid", None):
            return
        if code == 0:
            self.lb_state.setText("生成完成")
            self.ctx.record("炮孔数据库生成", "完成", "%s / %s" % (self.ed_plat.text(), self.ed_date.text()),
                            self.row_out.value())
        else:
            self.lb_state.setText("生成失败（退出码 %s），见日志" % code)
            self.ctx.record("炮孔数据库生成", "失败", "退出码 %s" % code, self.row_out.value())


def _lab(text: str) -> QLabel:
    l = QLabel(text)
    l.setObjectName("fieldLabel")
    return l
