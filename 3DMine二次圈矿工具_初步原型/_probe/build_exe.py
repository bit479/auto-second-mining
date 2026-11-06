# -*- coding: utf-8 -*-
"""把整套工具打成**一个 exe**（含二次圈矿 + Excel 工具 + 单日并入 + 验收脚本）。

用法（在项目根目录、用带 PySide6/PyInstaller 的解释器）::

    python _probe/build_exe.py                # 单文件 exe（默认；首次启动解包约 5~10 秒）
    python _probe/build_exe.py --onedir       # 目录版（启动快，便于排错）
    python _probe/build_exe.py --no-clean     # 用上次的 build 缓存（增量，快）

产物：``dist/二次圈矿智能工作台.exe``（或 ``dist/二次圈矿智能工作台/``）。

exe 的两种角色（见 client/ui_v2/app.py）::

    二次圈矿智能工作台.exe                                   # 打开界面
    二次圈矿智能工作台.exe --run-script core/run_strip.py …  # 当脚本宿主（界面后台任务用）

可写配置不放进 exe：首次运行会把 圈矿参数.json / grade_profiles.json / 3DMine 模板
摆到 exe 同目录的 ``data/``，之后所有读写都在那儿（环境变量 ``SM_HOME``）。
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # …/3DMine二次圈矿工具_初步原型
DIST = ROOT / "dist"
BUILD = ROOT / "build"
NAME = "二次圈矿智能工作台"
ENTRY = ROOT / "client" / "ui_v2" / "app.py"
ICON = ROOT / "assets" / "app.ico"

# (项目内路径, 包内目标)；不打包的目录在 COPY_IGNORE 里
DATAS = [
    ("core", "core"),
    ("excel_tools", "excel_tools"),
    ("_probe", "_probe"),
    ("sample_data", "sample_data"),
    ("assets", "assets"),
    ("圈矿参数.json", "."),
    ("README.md", "."),
    ("项目结构说明.md", "."),
]
COPY_IGNORE = shutil.ignore_patterns("__pycache__", "_out", "归档", "bak",
                                     ".pytest_cache", "*.pyc", "release_v1")

HIDDEN = [
    "pyodbc", "xlwt", "xlutils", "xlutils.copy", "xlrd", "openpyxl", "ezdxf",
    "matplotlib", "matplotlib.backends.backend_agg", "scipy", "scipy.spatial",
    "scipy.spatial._qhull", "shapely", "numpy", "PIL",
    "ui_v2", "ui_v2.app", "ui_v2.main_window", "ui_v2.theme", "ui_v2.icons",
    "ui_v2.components", "ui_v2.components.widgets",
    "ui_v2.pages", "ui_v2.pages.base", "ui_v2.pages.dashboard",
    "ui_v2.pages.single_mining", "ui_v2.pages.batch_mining",
    "ui_v2.pages.manual_calibration", "ui_v2.pages.composite_manager",
    "ui_v2.pages.excel_tools", "ui_v2.pages.database_builder",
    "ui_v2.pages.parameter_manager", "ui_v2.pages.diagnostics",
    "ui_v2.pages.settings",
    "ui_v2.services", "ui_v2.services.paths", "ui_v2.services.runner",
    "ui_v2.services.config", "ui_v2.services.files", "ui_v2.services.context",
    "ui_v2.services.txt_import", "ui_v2.services.drop_manager",
    "ui_v2.components.drop_overlay", "ui_v2.components.shell",
]

# PySide6 全家桶很大，只留用得上的
EXCLUDE_MODULES = [
    "tkinter", "pydoc_data", "lib2to3",
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick",
    "PySide6.QtWebChannel", "PySide6.QtWebSockets", "PySide6.QtQuick", "PySide6.QtQuick3D",
    "PySide6.QtQml", "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.Qt3DAnimation",
    "PySide6.QtCharts", "PySide6.QtDataVisualization", "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets", "PySide6.QtBluetooth", "PySide6.QtNfc",
    "PySide6.QtPositioning", "PySide6.QtSerialPort", "PySide6.QtSql", "PySide6.QtTest",
    "PySide6.QtPdf", "PySide6.QtPdfWidgets", "PySide6.QtDesigner", "PySide6.QtHelp",
    "PySide6.QtUiTools", "PySide6.QtNetworkAuth", "PySide6.QtRemoteObjects",
    "PySide6.QtScxml", "PySide6.QtSensors", "PySide6.QtSpatialAudio",
    "PySide6.QtStateMachine", "PySide6.QtTextToSpeech",
    "PySide6.QtHttpServer", "PySide6.QtGraphs", "PySide6.QtSvgWidgets",
]


def _project_version() -> tuple[str, str, str]:
    """从 services/paths.py 读版本号与构建日期，避免两处手写。"""
    import re

    src = (ROOT / "client" / "ui_v2" / "services" / "paths.py").read_text(encoding="utf-8")
    ver = re.search(r'APP_VERSION\s*=\s*"v?([0-9.]+)"', src)
    build = re.search(r'BUILD_STAMP\s*=\s*"BUILD\s*([0-9-]+)"', src)
    return (ver.group(1) if ver else "0.0", build.group(1) if build else "", src)


def write_version_file(work: Path) -> Path | None:
    """生成 Windows 文件属性里的版本信息（右键→属性→详细信息）。"""
    tag, build_date, _src = _project_version()
    parts = [int(x) for x in tag.split(".") if x.isdigit()][:4]
    while len(parts) < 4:
        parts.append(0)
    v = tuple(parts)
    path = work / "version_info.txt"
    path.write_text(
        "VSVersionInfo(\n"
        "  ffi=FixedFileInfo(filevers=%r, prodvers=%r, mask=0x3f, flags=0x0,\n"
        "                    OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),\n"
        "  kids=[\n"
        "    StringFileInfo([StringTable('080404B0', [\n"
        "      StringStruct('CompanyName', 'bit479'),\n"
        "      StringStruct('FileDescription', '二次圈矿智能工作台'),\n"
        "      StringStruct('FileVersion', '%s'),\n"
        "      StringStruct('InternalName', 'second-mining-workbench'),\n"
        "      StringStruct('LegalCopyright', 'Copyright (C) 2026 bit479'),\n"
        "      StringStruct('OriginalFilename', '二次圈矿智能工作台.exe'),\n"
        "      StringStruct('ProductName', '二次圈矿智能工作台'),\n"
        "      StringStruct('ProductVersion', '%s'),\n"
        "      StringStruct('Comments', 'build %s'),\n"
        "    ])]),\n"
        "    VarFileInfo([VarStruct('Translation', [2052, 1200])])\n"
        "  ]\n"
        ")\n" % (v, v, tag, tag, build_date or "-"),
        encoding="utf-8")
    return path


def main() -> int:
    onedir = "--onedir" in sys.argv
    clean = "--no-clean" not in sys.argv
    sep = ";" if sys.platform.startswith("win") else ":"

    print("=" * 74)
    print("打包 %s（%s）" % (NAME, "目录版" if onedir else "单文件"))
    print("解释器 %s" % sys.executable)
    print("项目   %s" % ROOT)
    print("=" * 74)

    # 1) 先做一份干净的"要打包的数据"树（去掉缓存/中间产物）
    # 每次用新的暂存目录：旧的可能被占用/删不掉，别因此中断打包
    stage = BUILD / ("_stage_%s" % time.strftime("%m%d_%H%M%S"))
    stage.mkdir(parents=True, exist_ok=True)
    total = 0
    for src, dst in DATAS:
        s = ROOT / src
        if not s.exists():
            print("  [跳过] 不存在：%s" % src)
            continue
        t = stage / dst
        if s.is_dir():
            shutil.copytree(s, t, ignore=COPY_IGNORE)
            n = sum(1 for _ in t.rglob("*") if _.is_file())
            print("  + %-18s → %-12s %5d 个文件" % (src, dst, n))
            total += n
        else:
            t.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(s, t)
            print("  + %-18s → %-12s %5d 个文件" % (src, dst, 1))
            total += 1
    print("  数据合计 %d 个文件\n" % total)

    # 2) PyInstaller
    # 每次用独立 workpath：上一轮的中间文件可能被占用/删不掉（Windows + 杀毒），
    # 复用会直接失败；新建目录不需要删任何东西。
    mode = "onedir" if onedir else "onefile"
    work = BUILD / ("w_%s_%s" % (mode, time.strftime("%m%d_%H%M%S")))
    work.mkdir(parents=True, exist_ok=True)
    # PyInstaller 会 os.remove 掉旧产物；某些环境（沙箱/回收站不可用）这一步会抛
    # OSError，导致打包失败。先把旧产物改名挪走（改名不触发删除）再打包。
    old_target = DIST / (NAME + (".exe" if not onedir else ""))
    if old_target.exists():
        bin_trash = BUILD / "_replaced"
        bin_trash.mkdir(parents=True, exist_ok=True)
        moved = bin_trash / ("%s_%s%s" % (NAME, time.strftime("%m%d_%H%M%S"),
                                          ".exe" if not onedir else ""))
        try:
            old_target.rename(moved)
            print("  旧产物已挪到 %s" % moved.name)
        except OSError as e:
            print("  [提示] 旧产物挪不动（%s），继续尝试直接覆盖" % e)

    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm",
           "--name", NAME,
           "--distpath", str(DIST), "--workpath", str(work), "--specpath", str(work),
           "--paths", str(ROOT / "client"),
           "--onedir" if onedir else "--onefile",
           "--windowed",
           "--collect-submodules", "xlutils",
           "--collect-submodules", "xlwt",
           ]
    if ICON.exists():
        cmd += ["--icon", str(ICON)]
    ver_file = write_version_file(work)
    if ver_file is not None:
        cmd += ["--version-file", str(ver_file)]
        print("  版本资源：%s v%s" % (ver_file.name, _project_version()[0]))
    for src, dst in DATAS:
        if (stage / dst).exists():
            cmd += ["--add-data", "%s%s%s" % ((stage / dst).as_posix(), sep, dst)]
    for h in HIDDEN:
        cmd += ["--hidden-import", h]
    for m in EXCLUDE_MODULES:
        cmd += ["--exclude-module", m]
    cmd.append(str(ENTRY))

    print("执行 PyInstaller（可能要 3~8 分钟）…\n")
    rc = subprocess.call(cmd, cwd=str(ROOT))
    if rc != 0:
        print("\n[失败] PyInstaller 退出码 %s" % rc)
        return rc

    exe = (DIST / NAME / (NAME + ".exe")) if onedir else (DIST / (NAME + ".exe"))
    print("\n" + "=" * 74)
    if exe.exists():
        size = sum(f.stat().st_size for f in exe.parent.rglob("*") if f.is_file()) \
            if onedir else exe.stat().st_size
        print("完成：%s（%.1f MB）" % (exe, size / 1048576))
        print("首次运行会在 exe 同目录建 data\\（圈矿参数 / 品位分级 / 3DMine 模板）")
        return 0
    print("完成，但没找到预期产物：%s" % exe)
    return 1


if __name__ == "__main__":
    sys.exit(main())
