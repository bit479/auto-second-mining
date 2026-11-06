# -*- coding: utf-8 -*-
"""单炮区二次圈矿：输入 → 模式 → 参数 → 执行（四步流程）。"""

from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QButtonGroup, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QProgressBar, QPushButton, QRadioButton, QSplitter, QVBoxLayout,
    QWidget,
)

from .. import theme
from ..components import widgets as W
from ..services import config, files, paths
from .base import Page


class SingleMiningPage(Page):
    TITLE = "单炮区二次圈矿"
    SUB = "数据库+综合图 → 模式 → 参数 → 一键出三件套"

    def __init__(self, parent=None):
        self._chain: list[tuple[str, str, list]] = []
        self._chain_idx = 0
        self._busy = False
        self._started_at = 0.0
        super().__init__(parent)

    # ------------------------------------------------------------ 构建

    def _build(self) -> None:
        self.subtitle.setText(self.SUB)
        self.runner.finished.connect(self._on_step_finished)

        # 顶部识别条
        self.banner = W.Banner("还没有选数据库。把炮孔数据库 Excel 拖进下面任一输入框，"
                              "平台/日期、综合图、输出目录会自动带出来。", "info")
        self.add(self.banner)

        split = QSplitter(Qt.Horizontal)
        split.setChildrenCollapsible(False)
        left = QWidget()
        self.steps = QVBoxLayout(left)
        self.steps.setContentsMargins(0, 0, 8, 0)
        self.steps.setSpacing(14)
        split.addWidget(left)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(12)
        split.addWidget(right)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 2)
        split.setSizes([720, 460])
        self.add(split)

        self._build_step1()
        self._build_step2()
        self._build_step3()
        self._build_step4()
        self._build_right(rl)

        # 动作按钮（页面右上）
        self.btn_open_out = W.icon_button("folder", "打开输出目录", on_click=self._open_out)
        self.add_action(self.btn_open_out)

    # ---- 第一步：输入 ----

    def _build_step1(self) -> None:
        card = W.Card()
        card.add(W.SectionTitle("1", "输入数据", "必填：数据库 + 综合图 + 平台/日期"))
        self.steps.addWidget(card)

        self.row_xls = W.FileRow("炮孔数据库 Excel", "如 1、3940平台 炮孔数据库1008.xls",
                                 file_filter="Excel (*.xls *.xlsx)", title="选择炮孔数据库",
                                 must_exist=True)
        self.row_xls.changed.connect(self._on_xls_changed)
        card.add(self.row_xls)

        self.row_comp = W.FileRow("平台综合图 DWG", "该平台的综合图（每次都要指定）",
                                  file_filter="DWG (*.dwg)", title="选择综合图 DWG")
        self.row_comp.changed.connect(self._sync_ctx)
        card.add(self.row_comp)

        grid = QWidget()
        gl = QGridLayout(grid)
        gl.setContentsMargins(0, 0, 0, 0)
        gl.setHorizontalSpacing(10)
        gl.setVerticalSpacing(6)

        gl.addWidget(_lab("平台"), 0, 0)
        self.ed_platform = QLineEdit()
        self.ed_platform.setPlaceholderText("3940")
        self.ed_platform.setFixedWidth(90)
        self.ed_platform.textChanged.connect(self._refresh_banner)
        gl.addWidget(self.ed_platform, 0, 1)

        gl.addWidget(_lab("炮区日期"), 0, 2)
        self.ed_date = QLineEdit()
        self.ed_date.setPlaceholderText("1008")
        self.ed_date.setFixedWidth(90)
        self.ed_date.textChanged.connect(self._refresh_banner)
        gl.addWidget(self.ed_date, 0, 3)

        gl.addWidget(_lab("矿段"), 0, 4)
        self.cb_section = W.combo(config.grade_choices())
        self.cb_section.setFixedWidth(226)
        self.cb_section.currentIndexChanged.connect(self._on_section_changed)
        gl.addWidget(self.cb_section, 0, 5, 1, 2)

        self.lb_detect = QLabel("")
        self.lb_detect.setObjectName("muted")
        gl.addWidget(self.lb_detect, 1, 0, 1, 7)
        gl.setColumnStretch(6, 1)
        card.add(grid)

        self.row_out = W.FileRow("输出目录", "默认：数据库同目录\\二次圈矿成果_平台_日期",
                                 mode="dir", title="选择输出目录", must_exist=False)
        self.row_out.changed.connect(self._sync_ctx)
        card.add(self.row_out)

    # ---- 第二步：模式 ----

    def _build_step2(self) -> None:
        card = W.Card()
        card.add(W.SectionTitle("2", "圈矿模式", "三种模式都调用原有算法，不改变算量口径"))
        self.steps.addWidget(card)

        row = QHBoxLayout()
        row.setSpacing(10)
        self.mode_group = QButtonGroup(self)
        self.mode_buttons: dict[str, QRadioButton] = {}
        self.mode_boxes: dict[str, QFrame] = {}
        specs = [
            ("auto", "① 自动圈矿", "按参数与算法自动分档、圈矿界、分块算量（日常默认）"),
            ("manual", "② 人工圈矿", "导入人工画的闭合矿块 .3ds：一条线 = 一块，只算量出图"),
            ("exact", "③ 精确模式", "导入人工 .3ds 轮廓当整条矿界，界内按品位档再分块"),
        ]
        for key, title, desc in specs:
            box = QFrame()
            box.setObjectName("modeCard")
            box.setCursor(Qt.PointingHandCursor)
            bl = QVBoxLayout(box)
            bl.setContentsMargins(12, 10, 12, 10)
            bl.setSpacing(4)
            rb = QRadioButton(title)
            rb.setStyleSheet("QRadioButton{font-weight:600;}")
            rb.setProperty("modekey", key)
            self.mode_group.addButton(rb)
            self.mode_buttons[key] = rb
            bl.addWidget(rb)
            d = QLabel(desc)
            d.setObjectName("muted")
            d.setWordWrap(True)
            bl.addWidget(d)
            row.addWidget(box, 1)
            self.mode_boxes[key] = box
            box.mousePressEvent = lambda e, k=key: self.set_mode(k)   # 点卡片任意处都切换
        self.mode_buttons["auto"].setChecked(True)
        self.mode_group.buttonClicked.connect(lambda b: self.set_mode(b.property("modekey")))
        card.add(row)

        self.row_outline = W.FileRow("轮廓文件 .3ds", "人工导出的矿界/矿块（可多选，分号分隔）",
                                     file_filter="3DMine 字符串 (*.3ds)", title="选择 .3ds")
        self.row_outline.changed.connect(self._on_outline_changed)
        self.row_outline.setVisible(False)
        card.add(self.row_outline)
        self.btn_pick_outline = W.icon_button("plus", "添加 .3ds", kind="ghost",
                                              on_click=self._pick_outlines)
        self.btn_pick_outline.setVisible(False)
        card.add(self.btn_pick_outline)

        self.lb_mode_hint = QLabel("")
        self.lb_mode_hint.setObjectName("muted")
        self.lb_mode_hint.setWordWrap(True)
        card.add(self.lb_mode_hint)

    # ---- 第三步：参数 ----

    def _build_step3(self) -> None:
        card = W.Card()
        head = W.SectionTitle("3", "参数配置", "读取优先级不变：全局默认 → 平台 → 炮区")
        card.add(head)

        bar = QHBoxLayout()
        bar.setSpacing(8)
        self.lb_layer = QLabel("当前生效：全局默认")
        self.lb_layer.setObjectName("muted")
        bar.addWidget(self.lb_layer)
        bar.addStretch(1)
        self.btn_refresh = W.icon_button("refresh", "刷新", kind="ghost", on_click=self.refresh_params)
        bar.addWidget(self.btn_refresh)
        self.btn_save_plat = W.icon_button("save", "存为平台默认", kind="ghost",
                                           on_click=lambda: self.save_params("platform"))
        bar.addWidget(self.btn_save_plat)
        self.btn_save_blast = W.icon_button("save", "存为当前炮区", kind="ghost",
                                            on_click=lambda: self.save_params("blast"))
        bar.addWidget(self.btn_save_blast)
        card.add(bar)

        basic = [s for s in config.PARAM_SPECS if not s[0].startswith(("block_", "density_"))]
        self.grid_basic = W.ParamGrid(basic[:6], columns=3)
        card.add(self.grid_basic)

        self.btn_adv, adv = W.expander()
        card.add(self.btn_adv)
        al = QVBoxLayout(adv)
        al.setContentsMargins(0, 4, 0, 0)
        al.setSpacing(8)
        self.grid_adv = W.ParamGrid(
            basic[6:] + [x for x in config.PARAM_SPECS
                         if x[0].startswith(("block_", "density_"))], columns=3)
        al.addWidget(self.grid_adv)
        note = QLabel("高级参数一般不用动；改完记得「存为平台默认」或「存为当前炮区」。")
        note.setObjectName("muted")
        al.addWidget(note)
        card.add(adv)
        self.steps.addWidget(card)

    # ---- 第四步：执行 ----

    def _build_step4(self) -> None:
        card = W.Card()
        card.add(W.SectionTitle("4", "执行", "长任务在后台跑，日志实时输出"))
        self.steps.addWidget(card)

        opts = QHBoxLayout()
        opts.setSpacing(16)
        self.ck_dwg = W.CheckRow("圈完转 DWG 2010（需要 AutoCAD）", True,
                                 "取消勾选则只出 DXF，事后可在 CAD 里另存")
        self.ck_merge = W.CheckRow("圈完顺手并入综合图副本（原件不动）", True,
                                   "只生成副本；替换原件请到「综合图管理」页确认执行")
        opts.addWidget(self.ck_dwg)
        opts.addWidget(self.ck_merge)
        opts.addStretch(1)
        card.add(opts)

        run_row = QHBoxLayout()
        run_row.setSpacing(10)
        self.btn_run = W.icon_button("play", "一键出三件套", kind="primary",
                                     on_click=self.start_pipeline)
        self.btn_run.setMinimumWidth(172)
        run_row.addWidget(self.btn_run)
        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.setProperty("kind", "danger")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._cancel)
        run_row.addWidget(self.btn_cancel)
        run_row.addStretch(1)
        self.lb_state = QLabel("就绪")
        self.lb_state.setObjectName("muted")
        run_row.addWidget(self.lb_state)
        card.add(run_row)

        self.pbar = QProgressBar()
        self.pbar.setRange(0, 1000)
        self.pbar.setValue(0)
        self.pbar.setTextVisible(False)
        self.pbar.setFixedHeight(8)
        card.add(self.pbar)
        self._set_progress(0.0)

    def _build_right(self, box: QVBoxLayout) -> None:
        res = W.Card("成果文件", "生成后可直接打开")
        self.res_list = QVBoxLayout()
        self.res_list.setSpacing(4)
        res.add(self.res_list)
        self.res_list.addWidget(W.EmptyState(
            "file-text", "还没有生成成果",
            "跑完一次圈矿后，报告 xlsx / 图片 / DWG / DXF / .3ds 会出现在这里。",
            compact=True))
        box.addWidget(res)

        logc = W.Card("运行日志", "")
        self.log = W.LogView()
        self.log.setMinimumHeight(300)
        logc.add(self.log)
        bar = QHBoxLayout()
        bar.setSpacing(6)
        bar.addWidget(W.icon_button("refresh", "清空", kind="ghost", on_click=self.log.clear))
        bar.addWidget(W.icon_button("save", "另存日志", kind="ghost", on_click=self._save_log))
        bar.addStretch(1)
        self.lb_steps = QLabel("")
        self.lb_steps.setObjectName("muted")
        bar.addWidget(self.lb_steps)
        logc.add(bar)
        box.addWidget(logc, 1)

    # ------------------------------------------------------------ 交互

    def on_show(self) -> None:
        self._sync_from_ctx()

    def _sync_from_ctx(self) -> None:
        c = self.ctx
        if c.xls and not self.row_xls.value():
            self.row_xls.set_value(c.xls)
            self.row_comp.set_value(c.comp)
            self.row_out.set_value(c.out_dir)
            self.ed_platform.setText(c.platform)
            self.ed_date.setText(c.date)
            idx = self.cb_section.findData(c.section)
            if idx >= 0:
                self.cb_section.setCurrentIndex(idx)
            self.set_mode(c.mode)
            if c.outlines:
                self.row_outline.set_value(";".join(c.outlines))
        self.refresh_params()
        self._refresh_banner()

    def _on_xls_changed(self, text: str) -> None:
        p = Path(text.strip())
        if not p.is_file():
            self._refresh_banner()
            return
        self.ctx.set_xls(p)
        plat, date = files.parse_platform_date(p.name)
        self.ed_platform.setText(self.ctx.platform or plat)
        self.ed_date.setText(self.ctx.date or date)
        self.row_out.set_value(self.ctx.out_dir)
        if self.ctx.comp:
            self.row_comp.set_value(self.ctx.comp)
        if self.ctx.outlines:
            self.row_outline.set_value(";".join(self.ctx.outlines))
            self.set_mode(self.ctx.mode)
            self.log.append_line("[自动取用] 炮区文件夹里的 .3ds：%s（%d 条闭合线）"
                                 % (Path(self.ctx.outlines[0]).name,
                                    files.count_3ds_lines(self.ctx.outlines)))
        self.refresh_params()
        self._refresh_banner()

    def _on_section_changed(self) -> None:
        self.ctx.set_section(self.cb_section.currentData())
        self._refresh_banner()

    def _sync_ctx(self) -> None:
        self.ctx.comp = self.row_comp.value()
        self.ctx.out_dir = self.row_out.value()
        self._refresh_banner()

    def _refresh_banner(self) -> None:
        plat = self.ed_platform.text().strip()
        date = self.ed_date.text().strip()
        prof = self.ctx.current_profile()
        self.ctx.platform, self.ctx.date = plat, date
        if not self.row_xls.value():
            self.banner.set_text("还没有选数据库。把炮孔数据库 Excel 拖进下面任一输入框，"
                                 "平台/日期、综合图、输出目录会自动带出来。")
            self.lb_detect.setText("")
            return
        comp_ok = "已匹配综合图" if self.row_comp.value() else "未找到综合图，请手工指定"
        if self.row_comp.value():
            self.banner.set_text(
                "已就绪：%s ｜ 平台 %s / 日期 %s ｜ 综合图已匹配 ｜ 当前分级 %s（%s）。"
                "确认好参数后点下面的「一键出三件套」。"
                % (Path(self.row_xls.value()).name, plat or "?", date or "?",
                   " / ".join(b.short for b in prof.bands), prof.name.split("（")[0]))
        else:
            self.banner.set_text("已选数据库（%s），但没找到综合图 —— 请手工指定该平台的综合图 DWG。"
                                 % Path(self.row_xls.value()).name)
        self.lb_detect.setText("自动识别：平台 %s / 日期 %s ｜ %s ｜ 当前分级：%s"
                               % (plat or "?", date or "?", comp_ok,
                                  " / ".join(b.short for b in prof.bands)))
        self.ctx.changed.emit()

    def _on_outline_changed(self, text: str) -> None:
        items = [x.strip() for x in text.split(";") if x.strip()]
        self.ctx.outlines = items
        n = files.count_3ds_lines(items) if items else 0
        if items and self.mode() == "auto":
            self.lb_mode_hint.setText(
                "已选 %d 个 .3ds、共 %d 条闭合线 —— 但当前是「自动圈矿」，运行前会提示你切换模式。"
                % (len(items), n))
        elif items:
            self.lb_mode_hint.setText("已选 %d 个 .3ds、共 %d 条闭合线。" % (len(items), n))
        else:
            self.lb_mode_hint.setText("")

    def _pick_outlines(self) -> None:
        start = str(Path(self.row_xls.value()).parent) if self.row_xls.value() else ""
        fs, _ = QFileDialog.getOpenFileNames(self, "选择人工导出的 .3ds（可多选）", start,
                                             "3DMine 字符串 (*.3ds)")
        if fs:
            self.row_outline.set_value(";".join(fs))

    # ---- 模式 ----

    def mode(self) -> str:
        for key, rb in self.mode_buttons.items():
            if rb.isChecked():
                return key
        return "auto"

    def set_mode(self, key: str) -> None:
        rb = self.mode_buttons.get(key or "auto")
        if rb is None:
            return
        rb.setChecked(True)
        for k, box in self.mode_boxes.items():
            box.setProperty("selected", "true" if k == key else "false")
            box.style().unpolish(box)
            box.style().polish(box)
        need = key in ("manual", "exact")
        self.row_outline.setVisible(need)
        self.btn_pick_outline.setVisible(need)
        self.ctx.mode = key
        self._on_outline_changed(self.row_outline.value())
        if key == "auto":
            self.lb_mode_hint.setText("自动圈矿：按当前参数自动分档、圈矿界、分块算量。")

    # ---- 参数 ----

    def refresh_params(self) -> None:
        plat = self.ed_platform.text().strip()
        date = self.ed_date.text().strip()
        P = config.params_for(plat, date)
        src = config.param_sources(plat, date)
        self.grid_basic.set_values(P, src)
        self.grid_adv.set_values(P, src)
        layers = {v for v in src.values()}
        if "炮区 %s-%s" % (plat, date) in layers:
            txt = "当前生效：炮区 %s-%s 覆盖（优先级最高）" % (plat, date)
        elif ("平台 %s" % plat) in layers:
            txt = "当前生效：平台 %s 覆盖 + 全局默认" % plat
        else:
            txt = "当前生效：全局默认"
        self.lb_layer.setText(txt + "（灰色小字是该值来自哪一层）")

    def save_params(self, scope: str) -> None:
        vals = {}
        vals.update(self.grid_basic.values())
        vals.update(self.grid_adv.values())
        plat = self.ed_platform.text().strip()
        date = self.ed_date.text().strip()
        if scope == "blast" and not (plat and date):
            QMessageBox.information(self, "参数", "存为炮区需要先填平台号和日期。")
            return
        if scope == "platform" and not plat:
            QMessageBox.information(self, "参数", "存为平台需要先填平台号。")
            return
        try:
            out = config.save_params(vals, scope=scope, platform=plat, date=date)
        except Exception as exc:
            QMessageBox.warning(self, "保存失败", str(exc))
            return
        where = {"blast": "炮区 %s-%s" % (plat, date), "platform": "平台 %s" % plat}.get(scope, "全局默认")
        self.log.append_line("[参数] 已保存为%s → %s" % (where, out))
        self.refresh_params()
        self.lb_state.setText("参数已保存为%s" % where)

    # ---- 执行 ----

    def _validate(self) -> bool:
        if not Path(self.row_xls.value()).is_file():
            QMessageBox.warning(self, "缺少输入", "请先选择存在的炮孔数据库 Excel。")
            return False
        if not Path(self.row_comp.value()).is_file():
            QMessageBox.warning(self, "缺少输入", "请指定该平台的综合图 DWG（每次都要手工给）。")
            return False
        if not (self.ed_platform.text().strip() and self.ed_date.text().strip()):
            QMessageBox.warning(self, "缺少参数", "平台和日期不能为空。")
            return False
        return True

    def start_pipeline(self) -> None:
        if self._busy or self.runner.running("run_strip"):
            QMessageBox.information(self, "正在进行", "已经有一个圈矿任务在跑了，等它结束再来。")
            return
        if not self._validate():
            return

        outlines = [x.strip() for x in self.row_outline.value().split(";") if x.strip()]
        mode = self.mode()
        if outlines and mode == "auto":
            n = files.count_3ds_lines(outlines)
            how = "③ 精确模式（整条当矿界、界内按品位再分块）" if n <= 1 else \
                  "② 人工圈矿（%d 条闭合线 = %d 块）" % (n, n)
            if QMessageBox.question(
                    self, "模式没切",
                    "你填了 .3ds 轮廓（%d 条闭合线），但模式是「自动圈矿」——那样不会用你的线。\n\n"
                    "要不要改用 %s？\n（选 No = 忽略 .3ds，按自动圈矿跑）" % (n, how),
                    QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                mode = "exact" if n <= 1 else "manual"
                self.set_mode(mode)

        xls = self.row_xls.value()
        plat = self.ed_platform.text().strip()
        date = self.ed_date.text().strip()
        out = self.row_out.value().strip() or str(Path(xls).parent)
        Path(out).mkdir(parents=True, exist_ok=True)
        comp = self.row_comp.value()

        extra: list[str] = []
        section = self.cb_section.currentData()
        if section and section != "auto":
            extra += ["--grades", section]
        if outlines and mode in ("manual", "exact"):
            extra += (["--manual-blocks", ";".join(outlines)] if mode == "manual"
                      else ["--outline", ";".join(outlines)])

        self.log.clear()
        self.log.append_line("炮孔数据库：%s" % xls)
        self.log.append_line("综合图    ：%s" % comp)
        self.log.append_line("平台=%s  日期=%s  模式=%s  矿段=%s"
                             % (plat, date, {"auto": "自动圈矿", "manual": "人工圈矿",
                                             "exact": "精确模式"}.get(mode, mode),
                                self.cb_section.currentText()))
        self.log.append_line("输出目录  ：%s" % out)
        self.log.append_line("-" * 60)

        tag = "%s平台 %s" % (plat, date)
        self._out = Path(out)
        self._tag = tag
        self._plat, self._date = plat, date
        self._chain = [("第 1 步 圈矿算量 + 出报告/图/.3ds",
                        "core/run_strip.py",
                        [xls, plat, date, out, comp] + extra)]
        dxf = Path(out) / ("%s二次圈矿矿块图.dxf" % tag)
        tds = Path(out) / ("%s矿块边界线.3ds" % tag)
        if self.ck_dwg.isChecked():
            self._chain.append(("第 2 步 DXF → DWG 2010（AutoCAD）",
                                "core/dxf2dwg.py", [str(dxf), "--start"]))
        if self.ck_merge.isChecked():
            self._chain.append(("第 3 步 并入综合图副本（原件不动）",
                                "core/merge_to_composite.py",
                                [comp, str(tds), "--start"] + extra))
        self._chain_idx = 0
        self._set_busy(True)
        self._started_at = time.time()
        self._run_next()

    def _run_next(self) -> None:
        if self._chain_idx >= len(self._chain):
            self._finish()
            return
        name, script, args = self._chain[self._chain_idx]
        self.lb_state.setText("正在执行：%s" % name)
        self.lb_steps.setText("%d / %d" % (self._chain_idx + 1, len(self._chain)))
        self._set_progress(self._chain_idx / max(len(self._chain), 1))
        self._tid = self.runner.run(name, script, args, key=script,
                                    cwd=str(paths.bundle_root()))

    def _on_step_finished(self, tid: str, code: int) -> None:
        if not self._busy or getattr(self, "_tid", None) != tid:
            return
        name = self._chain[self._chain_idx][0]
        if code != 0:
            self.log.append_line("[失败] %s 退出码 %s" % (name, code))
            self._set_progress(1.0, error=True)
            self.lb_state.setText("失败：%s（详见日志）" % name)
            self.ctx.record(name, "失败", "退出码 %s" % code, str(self._out))
            self._set_busy(False)
            return
        self.log.append_line("[完成] %s（用时 %.1f 秒）" % (name, time.time() - self._started_at))
        self._chain_idx += 1
        # 上一步没产出（比如 DXF 转换失败但继续）时直接跳下一步
        self._run_next()

    def _finish(self) -> None:
        self._set_progress(1.0)
        self._set_busy(False)
        self.lb_steps.setText("%d / %d" % (len(self._chain), len(self._chain)))
        out, tag = self._out, self._tag
        p = files.output_paths(out, getattr(self, "_plat", ""), getattr(self, "_date", ""))
        found = []
        for key in ("xlsx", "png", "dwg", "dxf", "tds"):
            f = p[key]
            if f.exists():
                found.append((key, f))
                self.ctx.state.add_output(str(f), key)
        self._show_results(found)
        self.lb_state.setText("完成：%d 个成果文件" % len(found))
        self.log.append_line("-" * 60)
        self.log.append_line("全部流程结束：%d 个成果文件在 %s" % (len(found), out))
        self.ctx.record("单炮区圈矿 %s" % tag, "完成" if found else "失败",
                        "%d 个成果文件" % len(found), str(out))
        self.ctx.changed.emit()

    def _show_results(self, items) -> None:
        while self.res_list.count():
            w = self.res_list.takeAt(0).widget()
            if w is not None:
                w.deleteLater()
        names = {"xlsx": "报告 xlsx", "png": "报告图片", "dwg": "成果图 DWG",
                 "dxf": "成果图 DXF", "tds": "矿块边界线 .3ds"}
        if not items:
            self.res_list.addWidget(W.EmptyState(
                "alert", "没有找到成果文件", "请看下方运行日志确认失败原因。", compact=True))
            return
        for key, f in items:
            row = QWidget()
            hl = QHBoxLayout(row)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.setSpacing(6)
            lab = QLabel(names.get(key, key))
            lab.setFixedWidth(110)
            hl.addWidget(lab)
            val = QLabel(f.name)
            val.setObjectName("muted")
            val.setToolTip(str(f))
            hl.addWidget(val, 1)
            btn = W.tool_button("external", "打开", lambda _=False, p=f: paths.open_path(p))
            hl.addWidget(btn)
            self.res_list.addWidget(row)

    def _cancel(self) -> None:
        tid = getattr(self, "_tid", None)
        if tid:
            self.runner.cancel(tid)
        self._set_busy(False)
        self.lb_state.setText("已取消")

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.btn_run.setEnabled(not busy)
        self.btn_cancel.setEnabled(busy)
        if not busy:
            self.lb_steps.setText("")

    def _set_progress(self, ratio: float, error: bool = False) -> None:
        value = int(max(0.0, min(1.0, ratio)) * 1000)
        self.pbar.setValue(value)
        self.pbar.setStyleSheet(
            "QProgressBar{background:%s;border:none;border-radius:4px;}"
            "QProgressBar::chunk{background:%s;border-radius:4px;}"
            % (theme.NEUTRAL_BG, theme.DANGER if error else theme.PRIMARY))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        QTimer.singleShot(0, lambda: self._set_progress(
            (self._chain_idx / max(len(self._chain), 1)) if self._busy else 0.0))

    def _save_log(self) -> None:
        out = self.row_out.value().strip() or str(Path(self.row_xls.value()).parent)
        p, _ = QFileDialog.getSaveFileName(self, "另存日志", str(Path(out) / "圈矿日志.txt"),
                                           "文本 (*.txt)")
        if p:
            Path(p).write_text(self.log.plain(), encoding="utf-8")
            self.lb_state.setText("日志已保存：%s" % p)

    def _open_out(self) -> None:
        out = self.row_out.value().strip()
        if out and Path(out).exists():
            paths.open_path(out)
        else:
            QMessageBox.information(self, "输出目录", "输出目录还不存在。")


def _lab(text: str) -> QLabel:
    l = QLabel(text)
    l.setObjectName("fieldLabel")
    return l
