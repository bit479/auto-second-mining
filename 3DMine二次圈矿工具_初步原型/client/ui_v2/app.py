# -*- coding: utf-8 -*-
"""入口：开界面，或（单文件 exe 里）当脚本宿主跑 core / excel_tools / _probe 的脚本。

用法::

    python client/ui_v2/app.py                  # 源码运行（GUI）
    二次圈矿智能工作台.exe                       # 单文件 exe（GUI）
    二次圈矿智能工作台.exe --run-script core/run_strip.py <参数…>   # exe 内部派发
    python client/ui_v2/app.py --shot out.png   # 开发自检：截图后退出
"""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent          # …/client/ui_v2
CLIENT_DIR = APP_DIR.parent                        # …/client
if str(CLIENT_DIR) not in sys.path:
    sys.path.insert(0, str(CLIENT_DIR))


def _setup_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def run_script(argv: list[str]) -> int:
    """单文件 exe 的脚本宿主：按路径跑原脚本，参数、退出码原样传。"""
    if not argv:
        print("[错误] --run-script 缺少脚本路径")
        return 2
    script = Path(argv[0])
    if not script.is_absolute() and not script.exists():
        # 相对路径按"包内根目录"解析（exe 里就是 _MEIPASS）
        root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        cand = root / script
        if cand.exists():
            script = cand
    if not script.exists():
        print("[错误] 找不到脚本：%s" % script)
        return 2
    sys.argv = [str(script)] + [str(a) for a in argv[1:]]
    for p in (str(script.parent),):
        if p not in sys.path:
            sys.path.insert(0, p)
    import runpy

    try:
        runpy.run_path(str(script), run_name="__main__")
        return 0
    except SystemExit as exc:
        return int(exc.code or 0)
    except Exception:                     # noqa: BLE001
        traceback.print_exc()
        return 1


def main(argv: list[str] | None = None) -> int:
    _setup_stdio()
    argv = list(sys.argv[1:] if argv is None else argv)

    if argv[:1] == ["--run-script"]:
        return run_script(argv[1:])

    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtWidgets import QApplication, QMessageBox

    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    from ui_v2 import theme
    from ui_v2.services import paths

    paths.ensure_home()                     # exe 首次运行：把可写配置摆到 exe 旁边

    app = QApplication(sys.argv)
    app.setApplicationName("二次圈矿智能工作台")
    app.setOrganizationName("bit479")
    theme.apply_theme(app)

    from ui_v2.main_window import MainWindow

    try:
        win = MainWindow()
    except Exception:
        box = QMessageBox()
        box.setWindowTitle("启动失败")
        box.setText("界面初始化失败：\n\n%s" % traceback.format_exc()[-1200:])
        box.exec()
        return 1
    win.show()

    # 开发/验收自检：截图后退出
    if "--shot" in argv:
        i = argv.index("--shot")
        target = Path(argv[i + 1]) if i + 1 < len(argv) else Path("ui_shot.png")
        page = None
        if "--page" in argv:
            j = argv.index("--page")
            page = argv[j + 1] if j + 1 < len(argv) else None

        def _snap():
            if page:
                win.navigate(page)
            QTimer.singleShot(600, lambda: _save_and_quit(win, target))

        QTimer.singleShot(700, _snap)
    return app.exec()


def _save_and_quit(win, target: Path) -> None:
    from PySide6.QtWidgets import QApplication

    target.parent.mkdir(parents=True, exist_ok=True)
    win.grab().save(str(target))
    QApplication.instance().quit()


if __name__ == "__main__":
    sys.exit(main())
