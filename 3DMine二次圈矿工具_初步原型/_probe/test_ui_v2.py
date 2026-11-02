# -*- coding: utf-8 -*-
"""新界面自检：所有页面能建、能切；单炮区页真跑一次（1008）并检查成果文件。

用法::

    python _probe/test_ui_v2.py            # 全量（含真跑一圈，约 1~2 分钟）
    python _probe/test_ui_v2.py --pages    # 只检查页面能建能切

用 ``QT_QPA_PLATFORM=offscreen`` 可以无窗口跑（CI/远程）。
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLIENT = ROOT / "client"
sys.path.insert(0, str(CLIENT))

os.environ.setdefault("SM_HOME", str(ROOT))

from PySide6.QtCore import QTimer                      # noqa: E402
from PySide6.QtWidgets import QApplication             # noqa: E402

from ui_v2 import theme                                # noqa: E402
from ui_v2.main_window import MainWindow               # noqa: E402

CHECKS: list[tuple[bool, str]] = []


def check(ok: bool, msg: str) -> None:
    CHECKS.append((bool(ok), msg))
    print("  %s  %s" % ("OK  " if ok else "FAIL", msg))


def test_pages(app, win) -> None:
    print("\n[页面]")
    for key in win.pages:
        try:
            win.navigate(key)
            app.processEvents()
            check(True, "页面可打开：%s（%s）" % (key, win.pages[key].TITLE))
        except Exception as exc:            # noqa: BLE001
            check(False, "页面打不开：%s → %s" % (key, exc))


def test_single_run(app, win) -> None:
    print("\n[单炮区：真跑一圈]")
    page = win.pages["single"]
    win.navigate("single")
    src = Path(r"E:\AAAWK\NNN CRT\auto-second-mining\北部山头3940平台2026\7、单日数据"
               r"\北部山头3940平台-1008\1、3940平台 炮孔数据库1008.xls")
    comp = Path(r"E:\AAAWK\NNN CRT\auto-second-mining\北部山头3940平台2026"
                r"\5、 北部山头3940平台二次圈矿矿块图-2026综合.dwg")
    if not src.exists():
        check(True, "本机没有 1008 数据，跳过真跑")
        return
    tmp = Path(tempfile.mkdtemp(prefix="ui_v2_"))
    xls = tmp / src.name
    shutil.copy2(src, xls)
    page.row_xls.set_value(str(xls))
    page.ed_platform.setText("3940")
    page.ed_date.setText("1008")
    if comp.exists():
        page.row_comp.set_value(str(comp))
    else:
        page.row_comp.set_value(str(tmp / "dummy.dwg"))
        (tmp / "dummy.dwg").write_bytes(b"x")
    page.row_out.set_value(str(tmp / "out"))
    page.ck_dwg.setChecked(False)       # 不拉 AutoCAD
    page.ck_merge.setChecked(False)
    app.processEvents()

    page.start_pipeline()
    check(page.runner.running("run_strip") or page._busy, "任务已启动（后台 QProcess）")

    done = {"v": False}
    page.runner.finished.connect(lambda tid, code: done.__setitem__("v", True))
    QTimer.singleShot(180_000, app.quit)      # 兜底：最长 3 分钟
    while not done["v"]:
        app.processEvents()
        if not page._busy:
            break
    out = Path(page.row_out.value())
    xlsx = out / "3940平台 1008炮孔数据报告.xlsx"
    tds = out / "3940平台 1008矿块边界线.3ds"
    dxf = out / "3940平台 1008二次圈矿矿块图.dxf"
    check(xlsx.exists(), "报告 xlsx 已生成：%s" % xlsx.name)
    check(tds.exists(), "矿块边界线 .3ds 已生成")
    check(dxf.exists(), "成果图 DXF 已生成")
    check(len(page.log.plain()) > 200, "日志有内容（%d 字符）" % len(page.log.plain()))
    if xlsx.exists():
        try:
            from openpyxl import load_workbook

            ws = load_workbook(xlsx, data_only=True).active
            labels = [ws.cell(r, 1).value for r in range(3, 8)]
            check(any(str(x or "").startswith(("0.5", "1.", "3.")) for x in labels),
                  "报告档位列正常：%s" % [x for x in labels if x])
        except Exception as exc:            # noqa: BLE001
            check(False, "读报告失败：%s" % exc)


def test_batch(app, win) -> None:
    """批量：在临时父目录里放一天炮区，走 UI 队列真跑一次。"""
    print("\n[批量：真跑一个炮区]")
    src = Path(r"E://AAAWK//NNN CRT//auto-second-mining//北部山头3940平台2026//7、单日数据"
               r"\北部山头3940平台-1008\1、3940平台 炮孔数据库1008.xls")
    comp = Path(r"E://AAAWK//NNN CRT//auto-second-mining//北部山头3940平台2026"
                r"\5、 北部山头3940平台二次圈矿矿块图-2026综合.dwg")
    if not src.exists() or not comp.exists():
        check(True, "本机没有批量测试数据，跳过")
        return
    from PySide6.QtCore import Qt

    tmp = Path(tempfile.mkdtemp(prefix="ui_v2_batch_"))
    day = tmp / "北部山头3940平台-1008"
    day.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, day / src.name)

    page = win.pages["batch"]
    win.navigate("batch")
    page.row_parent.set_value(str(tmp))
    page.row_comp.set_value(str(comp))
    page.scan()
    app.processEvents()
    check(len(page.tasks) == 1, "扫到 1 个炮区（%s）" % (page.tasks[0].name if page.tasks else "—"))
    if not page.tasks:
        return
    check(page.tasks[0].platform == "3940" and page.tasks[0].date == "1008",
          "平台/日期识别：%s / %s" % (page.tasks[0].platform, page.tasks[0].date))
    for i in range(page.table.rowCount()):
        item = page.table.item(i, 0)
        if item is not None:
            item.setCheckState(Qt.Checked if i == 0 else Qt.Unchecked)

    page.run_queue()
    check(page._running, "批量队列已启动")

    done = {"v": False}
    page.runner.finished.connect(lambda tid, code: done.__setitem__("v", True))
    QTimer.singleShot(300_000, app.quit)
    while not done["v"] and page._running:
        app.processEvents()

    out = page.tasks[0].folder / ("二次圈矿成果_%s_%s" % (page.tasks[0].platform, page.tasks[0].date))
    check(page.tasks[0].status == "完成", "任务状态：%s" % page.tasks[0].status)
    check((out / "3940平台 1008炮孔数据报告.xlsx").exists(), "批量成果：报告 xlsx")
    check((out / "3940平台 1008矿块边界线.3ds").exists(), "批量成果：边界线 .3ds")
    check(len(page.log.plain()) > 100, "单任务日志有内容（%d 字符）" % len(page.log.plain()))


def main() -> int:
    pages_only = "--pages" in sys.argv
    app = QApplication(sys.argv[:1])
    theme.apply_theme(app)
    win = MainWindow()
    win.resize(1440, 900)
    win.show()
    app.processEvents()

    test_pages(app, win)
    if not pages_only:
        test_single_run(app, win)
        if "--with-batch" in sys.argv:
            test_batch(app, win)

    failed = [m for ok, m in CHECKS if not ok]
    print("\n" + "=" * 70)
    print("共 %d 项检查，%d 项通过" % (len(CHECKS), len(CHECKS) - len(failed)))
    if failed:
        for m in failed:
            print("  FAIL  %s" % m)
        return 1
    print("结论：全部通过 ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
