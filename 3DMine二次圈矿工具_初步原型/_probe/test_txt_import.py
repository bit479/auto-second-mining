# -*- coding: utf-8 -*-
"""TXT 拖放导入：解析引擎 + 全局拖放 + 页面联动的自动化测试。

    python _probe/test_txt_import.py            # 全部
    python _probe/test_txt_import.py parser     # 只跑解析
    python _probe/test_txt_import.py ui         # 只跑界面联动

不写生产数据：所有样本都在系统临时目录里现造，输出目录也只指向临时目录。
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLIENT = ROOT / "client"
sys.path.insert(0, str(CLIENT))
os.chdir(CLIENT)

from PySide6.QtCore import QMimeData, QPoint, Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)
from ui_v2 import theme
from ui_v2.services import txt_import as T

theme.apply_theme(app)

TMP = Path(tempfile.mkdtemp(prefix="txtdrop_"))
PASS, FAIL = [], []


def check(name: str, cond: bool, detail: str = "") -> None:
    (PASS if cond else FAIL).append(name)
    print(("  ✓ " if cond else "  ✗ ") + name + ("" if cond else ("  ← " + detail)))


def make(name: str, content: str, encoding: str = "utf-8") -> Path:
    p = TMP / name
    p.write_bytes(content.encode(encoding))
    return p


def wait(ms: int = 12000, until=None) -> bool:
    t0 = time.time()
    while (time.time() - t0) * 1000 < ms:
        app.processEvents()
        if until is not None and until():
            return True
        time.sleep(0.02)
    return until() if until else True


# ==================================================================== 解析引擎

OK = ("BS-3940-0915-P1,,470163.884,4349418.489,3971.508\n"
      "BS-3940-0915-P2,,470162.526,4349413.330,3971.485\n"
      "BS-3940-0915-P3,,470167.467,4349411.378,3971.869\n"
      "BS-3940-0915-P4,,470166.068,4349406.130,3972.038\n"
      "BS-3940-0915-P5,,470161.136,4349408.194,3971.557\n")


def test_parser() -> None:
    print("\n[解析引擎]")

    t = T.parse_txt_file(make("ok_utf8.txt", OK))
    check("UTF-8 / 5 列：解析就绪、5 孔、核心可直接使用",
          t.state == "ready" and t.valid_rows == 5 and t.core_ready and not t.normalized,
          "%s %s %s" % (t.state, t.valid_rows, t.core_ready))
    check("平台/日期取自炮孔编号（3940 / 0915）",
          (t.platform, t.date) == ("3940", "0915"), "%s/%s" % (t.platform, t.date))
    check("来源标记正确（hole_id）", t.meta["platform"].source == "hole_id",
          t.meta["platform"].source)

    bom = "\ufeff工程号\tE\tN\tR\nBS-3940-1008-P1\t470000.1\t4349000.2\t3941.3\n" \
          "BS-3940-1008-P2\t470001.1\t4349001.2\t3941.4\n"
    t = T.parse_txt_file(make("bom_tab_header.txt", bom))
    check("UTF-8 BOM + 制表符 + 表头：识别并规范化",
          t.state == "ready" and t.has_header and t.valid_rows == 2 and t.normalized,
          "%s hdr=%s norm=%s" % (t.state, t.has_header, t.normalized))
    check("BOM 编码标记为 UTF-8 BOM", t.encoding == "UTF-8 BOM", t.encoding)

    gbk_body = ("平台：3940\n炮区日期：1008\n"
                "BS-3940-1008-P1,,470163.884,4349418.489,3971.508\n"
                "BS-3940-1008-P2,,470162.526,4349413.330,3971.485\n")
    t = T.parse_txt_file(make("gbk_中文.txt", gbk_body, "gbk"))
    check("GBK 编码可解析并生成规范化副本",
          t.state == "ready" and t.valid_rows == 2 and t.normalized and "GBK" in t.encoding,
          "%s %s %s" % (t.state, t.encoding, t.normalized))

    space = ("平台：3960\n炮区日期：0919\n台阶高度：12\n"
             "BS-3960-0919-P1 470000.5 4349000.1 3961.2\n"
             "BS-3960-0919-P2 470001.5 4349002.1 3961.3\n")
    t = T.parse_txt_file(make("space_meta.txt", space))
    check("空格分隔 + 文件内标注：平台/日期/台阶都来自文件",
          (t.platform, t.date, t.bench) == ("3960", "0919", "12") and t.valid_rows == 2,
          "%s/%s/%s rows=%d" % (t.platform, t.date, t.bench, t.valid_rows))
    check("标注行不会被当成炮孔", t.total_rows == 2, "total=%d" % t.total_rows)

    t = T.parse_txt_file(make("坐标.txt", "A1,470000,4349000,3960\nA2,470001,4349002,3960\n"))
    check("缺平台/缺日期：不猜、只提示",
          not t.platform and not t.date and any("平台" in i.text for i in t.issues),
          "%s/%s" % (t.platform, t.date))
    check("缺元数据仍可进入页面（未被阻断）", not t.blocked, "blocked=%s" % t.blocked)

    # 坐标高程不得被当作平台：Z=3960 但编号是 3940
    z = "BS-3940-0915-P1,,470000,4349000,3960.0\n"
    t = T.parse_txt_file(make("z_should_not_be_platform.txt", z))
    check("不从 Z 高程推断平台（仍为 3940）", t.platform == "3940", t.platform)

    bad = ("BS-3940-1008-P1,,470000,4349000,3960\n"
           "BS-3940-1008-P2,,abc,4349002,3960\n"
           ",470004,4349004,3960\n")
    t = T.parse_txt_file(make("bad_coords.txt", bad))
    check("坏坐标/空工程号被计为异常并阻断生成",
          t.invalid_rows == 2 and t.valid_rows == 1 and t.blocked,
          "inv=%d valid=%d blocked=%s" % (t.invalid_rows, t.valid_rows, t.blocked))

    dup = ("BS-3940-1008-P1,,470000,4349000,3960\n"
           "BS-3940-1008-P1,,470001,4349001,3960\n"
           "BS-3940-1008-P2,,470002,4349002,3960\n")
    t = T.parse_txt_file(make("dup_ids.txt", dup))
    check("重复炮孔编号被识别并阻断", t.duplicate_rows == 1 and t.blocked,
          "dup=%d blocked=%s" % (t.duplicate_rows, t.blocked))

    t = T.parse_txt_file(make("BS-3960-0904-P1.txt", OK))
    check("文件内与文件名冲突：采用文件内并给出警告",
          t.platform == "3940"
          and any("冲突" in i.text for i in t.issues),
          "%s %s" % (t.platform, [i.text for i in t.issues if "冲突" in i.text]))

    empty = make("empty.txt", "")
    t = T.parse_txt_file(empty)
    check("空文件：友好失败不崩", t.state == "failed" and "空" in t.error, t.error)

    xlsx = TMP / "假的表格.xlsx"
    xlsx.write_bytes(b"PK\x03\x04")
    t = T.parse_txt_file(xlsx)
    check("非 TXT：拒绝并说明原因", t.state == "failed" and "TXT" in t.error, t.error)

    big = make("big.txt", "".join("BS-3940-1010-P%d,,%d,%d,3941.0\n"
                                  % (i, 470000 + i, 4349000 + i) for i in range(1, 60001)))
    t0 = time.time()
    t = T.parse_txt_file(big)
    cost = time.time() - t0
    check("大文件（6 万行）解析正确且够快",
          t.valid_rows == 60000 and cost < 8.0,
          "rows=%d cost=%.2fs" % (t.valid_rows, cost))
    print("      大文件耗时 %.2f 秒 / 文件 %.1f MB" % (cost, big.stat().st_size / 1048576))


# ==================================================================== 界面联动

class Harness:
    def __init__(self):
        from ui_v2.main_window import MainWindow

        self.win = MainWindow()
        self.win.resize(1440, 900)
        self.win.show()
        app.processEvents()
        self.db = self.win.pages["database"]
        self.results = []
        self.win.drop_manager.finished.connect(lambda task: self.results.append(task))

    def drop(self, widget, path: Path):
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(path))])
        pos = QPoint(40, 40)
        enter = QDragEnterEvent(pos, Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
        QApplication.sendEvent(widget, enter)
        drop = QDropEvent(pos, Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
        QApplication.sendEvent(widget, drop)

    def wait_task(self, before: int, timeout: int = 15000):
        wait(timeout, lambda: len(self.results) > before)
        return self.results[-1] if len(self.results) > before else None


def test_ui() -> None:
    print("\n[界面联动]")
    h = Harness()
    win = h.win

    # 1) 首页拖入合法 TXT
    n = len(h.results)
    h.drop(win.pages["dashboard"], make("drop_ok.txt", OK))
    task = h.wait_task(n)
    check("首页拖入：解析成功", task is not None and task.valid_rows == 5)
    check("首页拖入：自动跳到炮孔数据库生成页",
          win.stack.currentWidget() is h.db)
    check("平台/日期已填入表单",
          (h.db.ed_plat.text(), h.db.ed_date.text()) == ("3940", "0915"),
          "%s/%s" % (h.db.ed_plat.text(), h.db.ed_date.text()))
    check("XTF 路径自动回填，无需再选文件",
          Path(h.db.row_txt.value()).name.endswith(".txt"))
    check("预览表已载入 5 行", h.db.tb.rowCount() == 5, str(h.db.tb.rowCount()))
    check("任务已写入全局上下文", win.ctx.txt_import is task)
    check("无异常时允许生成", h.db.btn_make.isEnabled())

    # 2) 其它页面拖入（除数据库页外，全部页面都要能接住）
    for key in ("single", "batch", "manual", "composite", "excel",
                "database", "params", "diagnostics", "settings"):
        win.navigate(key)
        n = len(h.results)
        h.drop(win.pages[key], make("drop_%s.txt" % key, OK))
        t = h.wait_task(n)
        check("%s 页拖入同样生效" % win.pages[key].TITLE,
              t is not None and win.stack.currentWidget() is h.db)

    # 3) 非 TXT
    win.navigate("dashboard")
    cur = win.stack.currentWidget()
    n = len(h.results)
    xlsx = TMP / "非坐标表.xlsx"
    xlsx.write_bytes(b"PK\x03\x04")
    h.drop(win.pages["dashboard"], xlsx)
    wait(1200, lambda: False)
    check("拖入非 TXT：不触发导入、不跳页",
          len(h.results) == n and win.stack.currentWidget() is cur)

    # 4) 坏坐标：仍跳页但禁止生成
    n = len(h.results)
    h.drop(win.pages["single"], make("drop_bad.txt",
                                     "BS-3940-1008-P1,,470000,4349000,3960\n"
                                     "BS-3940-1008-P2,,xx,4349002,3960\n"))
    t = h.wait_task(n)
    check("坏坐标：仍进入数据库页并提示", t is not None and win.stack.currentWidget() is h.db)
    check("坏坐标：生成按钮被禁用", not h.db.btn_make.isEnabled())
    check("坏坐标：问题条目已展示", len(t.errors) >= 1)

    # 5) 重复编号
    n = len(h.results)
    h.drop(win.pages["batch"], make("drop_dup.txt",
                                    "BS-3940-1008-P1,,1,2,3\nBS-3940-1008-P1,,4,5,6\n"))
    t = h.wait_task(n)
    check("重复编号：识别并禁用生成", t is not None and t.blocked and not h.db.btn_make.isEnabled())

    # 6) 冲突：页面已有平台 3960，拖入 3940 → 不静默覆盖
    h.db.ed_plat.setText("3960")
    n = len(h.results)
    h.drop(win.pages["params"], make("drop_conflict.txt", OK))
    t = h.wait_task(n)
    check("参数冲突：保留页面值 3960", h.db.ed_plat.text() == "3960", h.db.ed_plat.text())
    check("参数冲突：记录在卡片里（有待确认项）", bool(h.db._conflicts))
    if h.db._conflicts:
        h.db._adopt_conflicts()
        check("点击「采用识别值」后改为 3940", h.db.ed_plat.text() == "3940",
              h.db.ed_plat.text())

    # 7) 同一文件重复拖入：不重复解析（复用上一次的任务对象）
    prev = h.results[-1]
    n = len(h.results)
    h.drop(win.pages["dashboard"], Path(prev.source_path))
    t = h.wait_task(n)
    check("重复拖入同一文件：直接复用、不重复解析", t is prev)

    # 8) 连续拖入两个不同文件
    n = len(h.results)
    h.drop(win.pages["dashboard"], make("drop_a.txt", OK))
    h.drop(win.pages["dashboard"], make("drop_b.txt",
                                        "BS-3960-0919-P1,,470100,4349100,3961.0\n"))
    wait(15000, lambda: len(h.results) >= n + 2)
    check("连续拖入：最后一次导入生效（平台 3960）",
          (h.db.ed_plat.text(), h.db.ed_date.text()) == ("3960", "0919"),
          "%s/%s" % (h.db.ed_plat.text(), h.db.ed_date.text()))

    # 9) 取消导入
    h.db.clear_import()
    check("取消导入：上下文与卡片都被清空",
          win.ctx.txt_import is None and h.db._task is None and h.db.btn_make.isEnabled())

    # 10) 取消解析（大文件）
    n = len(h.results)
    win.drop_manager.start_import(str(TMP / "big.txt"))
    wait(120, lambda: win.drop_manager.busy)
    win.drop_manager.cancel()
    wait(1500, lambda: False)
    check("解析中取消：不产生导入任务", len(h.results) == n and not win.drop_manager.busy)

    # 11) 取消后重新导入
    n = len(h.results)
    h.drop(win.pages["dashboard"], make("drop_again.txt", OK))
    t = h.wait_task(n)
    check("取消后重新导入正常", t is not None and t.valid_rows == 5
          and win.stack.currentWidget() is h.db)

    # 12) 页面切换不丢任务
    win.navigate("dashboard")
    win.navigate("database")
    check("切走再回来：导入任务仍在", h.db._task is not None and h.db.tb.rowCount() == 5)


# ==================================================================== main

if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("all", "parser"):
        test_parser()
    if what in ("all", "ui"):
        test_ui()

    print("\n" + "=" * 66)
    print("通过 %d 项，失败 %d 项" % (len(PASS), len(FAIL)))
    for f in FAIL:
        print("  ✗", f)
    sys.exit(1 if FAIL else 0)
