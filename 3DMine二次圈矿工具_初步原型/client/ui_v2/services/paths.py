# -*- coding: utf-8 -*-
"""路径与运行环境（源码运行 / PyInstaller 单文件 exe 都适用）。

源码目录布局::

    3DMine二次圈矿工具_初步原型/
    ├── client/ui_v2/            ← 本 UI
    ├── core/                    ← 圈矿核心（命令行入口）
    ├── excel_tools/             ← 报告汇总 / 单日并入
    ├── _probe/                  ← 验收脚本
    ├── assets/                  ← 3DMine 空库模板等
    └── 圈矿参数.json

冻结成单文件 exe 之后：代码与资源在 ``sys._MEIPASS``（临时解包目录，**只读**），
用户可写的配置/参数则放在 exe 同目录的 ``data/`` 下，用环境变量 ``SM_HOME``
告诉子进程"可写根目录在哪"（core/params.py、core/grades.py 等已经支持）。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "二次圈矿智能工作台"
APP_NAME_EN = "GEOLOGICAL MINING WORKSPACE"
APP_VERSION = "v1.17"
BUILD_STAMP = "BUILD 2026-11-06"
RELEASE_CHANNEL = "专业工作站版"

# 让子进程知道"可写根目录"是谁；没设就让它们按源码树自己算
ENV_HOME = "SM_HOME"


def build_stamp() -> str:
    """侧栏底部的构建信息：版本号下面那一行。"""
    mode = "单文件 exe" if is_frozen() else "源码运行"
    return "%s · %s" % (mode, BUILD_STAMP.replace("BUILD ", "").strip())


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def bundle_root() -> Path:
    """代码/资源所在目录：源码=项目根；exe=解包目录。"""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parents[3]


def app_dir() -> Path:
    """界面上显示的「程序目录」：源码=项目根；exe=exe 所在文件夹（不是 _MEI 临时目录）。"""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return bundle_root()


def data_home() -> Path:
    """可写根目录（圈矿参数.json、grade_profiles.json、成果、日志都在这里）。

    源码运行 = 项目根；exe（单文件或目录版）= **exe 同目录的 data\\**。
    """
    env = os.environ.get(ENV_HOME)
    if env:
        return Path(env)
    if is_frozen():
        return Path(sys.executable).resolve().parent / "data"
    return bundle_root()


def ensure_home() -> Path:
    """冻结运行时，把"必须可写"的配置从包里搬到 exe 旁边（只补缺，不覆盖）。"""
    home = data_home()
    if not is_frozen():
        return home
    home.mkdir(parents=True, exist_ok=True)
    pairs = [
        (bundle_root() / "圈矿参数.json", home / "圈矿参数.json"),
        (bundle_root() / "excel_tools" / "config" / "grade_profiles.json",
         home / "excel_tools" / "config" / "grade_profiles.json"),
        (bundle_root() / "assets" / "3dmine_template.mdb", home / "assets" / "3dmine_template.mdb"),
    ]
    for src, dst in pairs:
        try:
            if dst.exists() or not src.exists():
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())
        except OSError:
            pass
    return home


def core_dir() -> Path:
    return bundle_root() / "core"


def client_dir() -> Path:
    return bundle_root() / "client"


def probe_dir() -> Path:
    return bundle_root() / "_probe"


def excel_tools_dir() -> Path:
    return bundle_root() / "excel_tools"


def assets_dir() -> Path:
    return bundle_root() / "assets"


def ui_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def script(rel: str) -> Path:
    """按相对项目根的名字取脚本（core/run_strip.py、excel_tools/main.py …）。"""
    p = Path(rel)
    return p if p.is_absolute() else bundle_root() / rel


def params_json() -> Path:
    return data_home() / "圈矿参数.json"


def grade_config() -> Path:
    """品位分级配置（唯一来源）：优先可写目录里的那份，其次包内的。"""
    home = data_home() / "excel_tools" / "config" / "grade_profiles.json"
    if home.exists():
        return home
    return bundle_root() / "excel_tools" / "config" / "grade_profiles.json"


def state_file() -> Path:
    home = data_home()
    base = home if os.access(home, os.W_OK) else Path(os.environ.get("LOCALAPPDATA", home))
    return Path(base) / ".ui_state.json"


def child_env() -> dict:
    """给子进程的环境：UTF-8 + 可写根目录。"""
    env = os.environ.copy()
    env["SM_HOME"] = str(data_home())
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


def child_command(rel_script: str, args: list[str]) -> list[str]:
    """构造"跑某个脚本"的命令行。

    * 源码运行：用当前 Python 解释器直接跑脚本；
    * 单文件 exe：用 exe 自己（``--run-script``）跑脚本 —— 一个 exe 既能开界面也能当脚本宿主。
    """
    if is_frozen():
        return [sys.executable, "--run-script", str(script(rel_script))] + [str(a) for a in args]
    return [sys.executable, "-X", "utf8", str(script(rel_script))] + [str(a) for a in args]


def open_path(path) -> bool:
    """用系统默认程序打开文件/文件夹。"""
    p = Path(path)
    if not p.exists():
        return False
    try:
        os.startfile(str(p))  # noqa: S606 - Windows 桌面应用
        return True
    except Exception:
        return False
