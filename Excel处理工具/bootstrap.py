"""启动前自检：确认 Python 版本与依赖可用，缺失时自动安装。

所有提示都由 Python 输出（UTF-8），避免在 .bat 里写中文导致 cmd 按 GBK
解析出乱码指令。
"""

from __future__ import annotations

import os
import subprocess
import sys

REQUIRED = {"openpyxl": "openpyxl"}          # 模块名 -> pip 包名
OPTIONAL = {"xlrd": "xlrd"}                  # 读 .xls 时才需要


def _have(module: str) -> bool:
    import importlib.util

    return importlib.util.find_spec(module) is not None


def _install(*packages: str) -> bool:
    cmd = [sys.executable, "-m", "pip", "install", *packages]
    try:
        return subprocess.run(cmd).returncode == 0
    except Exception as exc:  # noqa: BLE001
        print("[错误] 无法调用 pip：%s" % exc)
        return False


def main() -> int:
    if sys.version_info < (3, 9):
        print("[错误] 需要 Python 3.9 以上，当前为 %d.%d.%d"
              % (sys.version_info[:3]))
        print("       请到 python.org 下载安装，安装时勾选 Add to PATH。")
        return 1

    missing = [pkg for mod, pkg in REQUIRED.items() if not _have(mod)]
    if missing:
        print("[提示] 首次运行，正在安装依赖：%s" % "、".join(missing))
        if not _install(*missing):
            print("[错误] 依赖安装失败。请手动执行：")
            print("       %s -m pip install %s" % (sys.executable, " ".join(missing)))
            return 1
        print("[完成] 依赖安装成功。")

    missing_opt = [pkg for mod, pkg in OPTIONAL.items() if not _have(mod)]
    if missing_opt:
        print("[提示] 可选依赖缺失（读取 .xls 时需要）：%s" % "、".join(missing_opt))
        print("       如需处理 .xls，请执行：%s -m pip install %s"
              % (sys.executable, " ".join(missing_opt)))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
