# -*- coding: utf-8 -*-
"""炮孔数据库生成：坐标 TXT + 粘贴品位表 → .xls / .mdb（模板与字段完全沿用原有实现）。

v1.17 起新增「本次导入」卡片：全局拖入 TXT 后由 :mod:`services.drop_manager` 解析，
本页只负责展示与把参数填进原有表单 —— 生成仍然调用原来的 ``core/make_database.py``。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPlainTextEdit,
    QVBoxLayout, QWidget,
)

from .. import icons, theme
from ..components import widgets as W
from ..services import config, files, paths
from .base import Page

SAMPLE = """工程号\tAu
BS-3940-0915-P1\t1.23
BS-3940-0915-P2\t0.86
…（直接从 Excel 复制两列粘进来即可，制表符/逗号/空格分隔都认）"""

_META_LABEL = {"platform": "平台", "date": "日期", "bench": "台阶"}


class DatabaseBuilderPage(Page):
    TITLE = "炮孔数据库生成"
    SUB = "坐标 TXT + 品位表 → .xls / .mdb（口径不变）"

    request_import = Signal(str)      # 交给主窗口的拖放管理器统一处理

    def _build(self) -> None:
        self.runner.finished.connect(self._on_finished)
        self._task = None
        self._conflicts: list[tuple[str, str, str, str]] = []
        self._applying = False
        self._auto_values: dict[str, str] = {}   # 由导入自动写入的值（可被下一次导入替换）

        # ---------------- 本次导入（拖放 / 重选 / 取消）
        self.import_card = W.Card("本次导入", "TXT 拖到窗口任意位置即可自动识别平台/日期")
        self.import_body = QVBoxLayout()
        self.import_body.setSpacing(10)
        self.import_card.add(self.import_body)
        self.add(self.import_card)
        self._render_import(None)

        # ---------------- 输入
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
        for key, widget in (("platform", self.ed_plat), ("date", self.ed_date),
                            ("bench", self.ed_bench)):
            widget.textEdited.connect(lambda _t, k=key: self._auto_values.pop(k, None))
        self.row_out = W.FileRow("输出目录", "留空 = TXT 同目录", mode="dir",
                                 title="选择输出目录", must_exist=False)
        info.add(self.row_out)
        self.add(info)

        run = QHBoxLayout()
        run.setSpacing(8)
        run.addWidget(W.icon_button("refresh", "解析预览", on_click=self.preview))
        self.btn_make = W.icon_button("database", "生成 .xls / .mdb", kind="primary",
                                      on_click=self.make)
        run.addWidget(self.btn_make)
        run.addStretch(1)
        self.lb_state = QLabel("")
        self.lb_state.setObjectName("muted")
        run.addWidget(self.lb_state)
        self.add(run)

        tcard = W.Card("解析预览", "只显示前 200 行")
        self.tb = W.make_table(["工程号", "E", "N", "R", "Au"], [220, 140, 140, 120], 260)
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

        self._refresh_gate()

    # ------------------------------------------------------------ 本次导入卡片

    def apply_import(self, task) -> None:
        """把一次 TXT 拖放导入的结果落进本页（不清空用户已填的参数，冲突只提示）。"""
        if task is None:
            return
        if self._task is task:
            return
        self._task = task
        self._conflicts = []

        self._applying = True
        try:
            self.row_txt.set_value(task.effective_path or task.source_path)
        finally:
            self._applying = False

        # 三级优先级的识别结果 → 表单；与页面上已有值冲突时保留页面值
        for key, widget in (("platform", self.ed_plat), ("date", self.ed_date),
                            ("bench", self.ed_bench)):
            mv = task.meta.get(key)
            if mv is None or not mv.value:
                continue
            cur = widget.text().strip()
            auto = self._auto_values.get(key)
            replaceable = (not cur) or (auto is not None and cur == auto) \
                or (key == "bench" and cur == "10")
            if replaceable:
                if cur != mv.value:
                    widget.setText(mv.value)
                self._auto_values[key] = mv.value
            elif cur != mv.value:
                self._conflicts.append((key, cur, mv.value, mv.source_label))

        if task.source_path:
            self.row_out.set_value(str(Path(task.source_path).parent))

        self._fill_preview(task)
        self._render_import(task)
        self._refresh_gate()
        self.lb_state.setText("已载入 %s（%d 孔）" % (task.source_name, task.valid_rows))
        self.ctx.txt_import = task

    def clear_import(self) -> None:
        self._task = None
        self._conflicts = []
        self.ctx.txt_import = None
        self._applying = True
        try:
            self.row_txt.set_value("")
        finally:
            self._applying = False
        self.tb.setRowCount(0)
        self.lb_check.setText("已取消本次导入；仍可手工选择 TXT 继续。")
        self.lb_check.setStyleSheet("color:%s;" % theme.TEXT_MUTED)
        self.lb_state.setText("")
        self._render_import(None)
        self._refresh_gate()
        self.log.append_line("[导入] 已取消本次 TXT 导入")

    def _adopt_conflicts(self) -> None:
        widgets = {"platform": self.ed_plat, "date": self.ed_date, "bench": self.ed_bench}
        for key, _cur, val, _src in self._conflicts:
            widgets[key].setText(val)
            self._auto_values[key] = val
        adopted = len(self._conflicts)
        self._conflicts = []
        self._render_import(self._task)
        self.lb_state.setText("已采用 %d 项识别值" % adopted)
        self.log.append_line("[导入] 已采用识别值 %d 项" % adopted)

    def _pick_txt(self) -> None:
        start = self.row_txt.value() or str(paths.data_home())
        picked, _ = QFileDialog.getOpenFileName(self, "选择坐标 TXT", start,
                                                "坐标 TXT (*.txt *.dat)")
        if picked:
            self.request_import.emit(picked)

    def _render_import(self, task) -> None:
        _clear(self.import_body)
        if task is None:
            self.import_body.addWidget(W.EmptyState(
                "upload", "还没有导入任务",
                "把坐标 TXT 拖到窗口任意位置 —— 平台/日期与炮孔坐标会自动识别，"
                "识别完自动跳到本页。也可以点下面按钮选择文件。",
                "选择 TXT 文件", self._pick_txt, compact=True))
            return

        # ---- 文件行
        head = QWidget()
        hl = QHBoxLayout(head)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(10)
        ic = icons.label("file-text", theme.PRIMARY_DARK, 18, head)
        hl.addWidget(ic, 0, Qt.AlignVCenter)
        name = QLabel(task.source_name)
        name.setObjectName("importFile")
        name.setToolTip(task.source_path)
        hl.addWidget(name)
        meta = QLabel("%s · %s · %s" % (task.size_text(), task.encoding or "—",
                                        task.layout_note or "—"))
        meta.setObjectName("importMeta")
        hl.addWidget(meta)
        hl.addStretch(1)
        badge = W.Badge("")
        if task.state == "failed":
            badge.set_state("解析失败", "error")
        elif task.errors:
            badge.set_state("%d 处问题" % len(task.errors), "error")
        elif task.warnings:
            badge.set_state("可用 · %d 项提示" % len(task.warnings), "warn")
        else:
            badge.set_state("已就绪", "ok")
        hl.addWidget(badge)
        self.import_body.addWidget(head)

        # ---- 元数据胶囊
        chips = QHBoxLayout()
        chips.setSpacing(8)
        conflict_keys = {c[0] for c in self._conflicts}
        for key in ("platform", "date", "bench"):
            mv = task.meta.get(key)
            chips.addWidget(_meta_chip(_META_LABEL[key],
                                       (mv.value if mv else "") or "—",
                                       (mv.source_label if mv and mv.value else "未识别"),
                                       warn=key in conflict_keys))
        chips.addStretch(1)
        self.import_body.addLayout(chips)

        # ---- 统计
        stats = QLabel("炮孔 %d 条 · 有效 %d · 异常 %d · 重复 %d · 跳过 %d 行%s"
                       % (task.total_rows, task.valid_rows, task.invalid_rows,
                          task.duplicate_rows, task.skipped_lines,
                          " · 已生成规范化副本" if task.normalized else ""))
        stats.setObjectName("importMeta")
        self.import_body.addWidget(stats)

        # ---- 冲突 / 问题
        if self._conflicts:
            desc = "；".join("%s：页面 %s，识别 %s（%s）"
                             % (_META_LABEL[k], cur, val, src)
                             for k, cur, val, src in self._conflicts)
            banner = W.Banner("参数冲突，已保留页面上的值 —— " + desc, "warn")
            btn = W.icon_button("check", "采用识别值", kind="ghost", size=14,
                                on_click=self._adopt_conflicts)
            banner.layout().addWidget(btn)
            self.import_body.addWidget(banner)

        problems = task.errors + task.warnings
        if problems:
            shown = [p.text for p in problems[:3]]
            more = len(problems) - len(shown)
            text = "；".join(shown) + ("；另有 %d 条" % more if more else "")
            if task.errors:
                text = "必须先处理（本次已禁止生成）：" + text
            self.import_body.addWidget(
                W.Banner(text, "error" if task.errors else "warn"))

        if task.normalized:
            note = QLabel(task.normalize_note)
            note.setObjectName("importMeta")
            note.setWordWrap(True)
            self.import_body.addWidget(note)

        # ---- 动作
        acts = QHBoxLayout()
        acts.setSpacing(8)
        acts.addWidget(W.icon_button("folder", "重新选择文件", kind="ghost",
                                     on_click=self._pick_txt))
        acts.addWidget(W.icon_button("x", "取消本次导入", kind="ghost",
                                     on_click=self.clear_import))
        acts.addStretch(1)
        self.import_body.addLayout(acts)

    def _refresh_gate(self) -> None:
        blocked = bool(self._task is not None and getattr(self._task, "blocked", False))
        self.btn_make.setEnabled(not blocked)
        self.btn_make.setToolTip("本次导入有必须修正的问题，处理后才能生成"
                                 if blocked else "")

    def _fill_preview(self, task) -> None:
        self.tb.setRowCount(0)
        for i, row in enumerate(task.rows[:200]):
            self.tb.insertRow(i)
            self.tb.setItem(i, 0, W.cell(row.hid))
            self.tb.setItem(i, 1, W.cell("%.3f" % row.e, theme.TEXT_MUTED))
            self.tb.setItem(i, 2, W.cell("%.3f" % row.n, theme.TEXT_MUTED))
            self.tb.setItem(i, 3, W.cell("%.3f" % row.r, theme.TEXT_MUTED))
            self.tb.setItem(i, 4, W.cell("—", theme.TEXT_FAINT))
        if not task.rows:
            self.lb_check.setText("没有有效炮孔记录，请看上方问题说明。")
            self.lb_check.setStyleSheet("color:%s;" % theme.DANGER)
            return
        msg = ("TXT 共 %d 行：有效 %d · 异常 %d · 重复 %d；品位表还没填，"
               "粘贴后点「解析预览」即可按原口径核对" %
               (task.total_rows, task.valid_rows, task.invalid_rows, task.duplicate_rows))
        self.lb_check.setText(msg)
        color = theme.DANGER if task.blocked else (
            theme.WARNING if task.warnings else theme.SUCCESS)
        self.lb_check.setStyleSheet("color:%s;" % color)
        self.log.append_line("[导入] %s → 有效 %d 孔（%s / %s）"
                             % (task.source_name, task.valid_rows,
                                task.platform or "平台未识别", task.date or "日期未识别"))
        for issue in (task.errors + task.warnings)[:5]:
            self.log.append_line("        %s %s" % ("[问题]" if issue.level == "error"
                                                   else "[提示]", issue.text))

    # ------------------------------------------------------------ 原有交互

    def on_show(self) -> None:
        task = self.ctx.txt_import
        if task is not None and getattr(self, "_task", None) is not task:
            self.apply_import(task)

    def _on_txt(self, text: str) -> None:
        if self._applying:
            return
        p = Path(text.strip())
        # 手工改了路径 → 之前的导入任务不再对应当前文件，清掉卡片但不影响手工流程
        if self._task is not None:
            try:
                changed = Path(self._task.effective_path).resolve() != p.resolve()
            except OSError:
                changed = True
            if changed:
                self._task = None
                self._conflicts = []
                self.ctx.txt_import = None
                self._render_import(None)
                self._refresh_gate()
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
        if self._task is not None and getattr(self._task, "blocked", False):
            errs = self._task.errors[:5]
            QMessageBox.warning(
                self, "本次导入存在问题",
                "以下问题需要先处理，本次未进入生成流程：\n\n"
                + "\n".join("· " + e.text for e in errs)
                + ("" if len(self._task.errors) <= 5
                   else "\n… 共 %d 条" % len(self._task.errors)))
            return
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


# ---------------------------------------------------------------- 小工具

def _meta_chip(key: str, value: str, source: str, warn: bool = False) -> QWidget:
    """「平台 3970 / 炮孔编号」这种小胶囊。"""
    box = QWidget()
    box.setObjectName("metaChip")
    box.setProperty("warn", "true" if warn else "false")
    box.setAttribute(Qt.WA_StyledBackground, True)
    lay = QVBoxLayout(box)
    lay.setContentsMargins(11, 6, 11, 7)
    lay.setSpacing(1)
    k = QLabel(key)
    k.setObjectName("metaChipKey")
    v = QLabel(value)
    v.setObjectName("metaChipVal")
    s = QLabel(source)
    s.setObjectName("metaChipSrc")
    lay.addWidget(k)
    lay.addWidget(v)
    lay.addWidget(s)
    box.setMinimumWidth(110)
    return box


def _clear(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w is not None:
            w.deleteLater()
        elif item.layout() is not None:
            _clear(item.layout())


def _lab(text: str) -> QLabel:
    l = QLabel(text)
    l.setObjectName("fieldLabel")
    return l
