# -*- coding: utf-8 -*-
"""生成 v1.17 功能截图：拖放提示层、导入结果卡片、异常阻断态。"""

import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "client"))
os.chdir(ROOT / "client")

from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)
from ui_v2 import theme
from ui_v2.main_window import MainWindow

theme.apply_theme(app)

OUT = ROOT / "docs" / "screenshots" / "v1.17"
OUT.mkdir(parents=True, exist_ok=True)
TMP = Path(tempfile.mkdtemp())

OK = TMP / "NS-3970-0718-P1-P90.txt"
OK.write_text("".join("NS-3970-0718-P%d,,%d.%03d,4349%03d.489,3971.508\n"
                      % (i, 470160 + i, 800 + i, 400 + i) for i in range(1, 91)),
              encoding="utf-8")
BAD = TMP / "BS-3940-1008-P1.txt"
BAD.write_text("BS-3940-1008-P1,,470163.884,4349418.489,3971.508\n"
               "BS-3940-1008-P2,,abc,4349413.330,3971.485\n"
               "BS-3940-1008-P1,,470167.467,4349411.378,3971.869\n", encoding="utf-8")

win = MainWindow()
win.resize(1600, 900)
win.move(40, 40)
win.show()
app.processEvents()
time.sleep(0.4)
app.processEvents()

# 1) 拖放态
win.navigate("single")
app.processEvents()
win.drop_overlay.show_drop("NS-3970-0718-P1-P90.txt")
for _ in range(6):
    app.processEvents()
    time.sleep(0.05)
win.grab().save(str(OUT / "01_拖放提示.png"))
win.drop_overlay.hide_overlay()

# 2) 导入结果（正常）
win.drop_manager.start_import(str(OK))
t0 = time.time()
while time.time() - t0 < 15 and win.ctx.txt_import is None:
    app.processEvents()
    time.sleep(0.03)
for _ in range(10):
    app.processEvents()
    time.sleep(0.05)
win.grab().save(str(OUT / "02_导入成功.png"))

# 3) 导入结果（有异常 → 禁止生成）
win.navigate("dashboard")
app.processEvents()
win.drop_manager.start_import(str(BAD))
t0 = time.time()
while time.time() - t0 < 15:
    app.processEvents()
    task = win.ctx.txt_import
    if task is not None and task.source_name == BAD.name:
        break
    time.sleep(0.03)
for _ in range(10):
    app.processEvents()
    time.sleep(0.05)
win.grab().save(str(OUT / "03_异常阻断.png"))

print("saved to", OUT)
