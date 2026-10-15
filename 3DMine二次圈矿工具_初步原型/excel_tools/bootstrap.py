"""启动前自检：确认 Python 版本与依赖可用，缺失时自动安装。

所有提示都由 Python 输出（UTF-8），避免在 .bat 里写中文导致 cmd 按 GBK
解析出乱码指令。

* ``REQUIRED`` —— 缺失且安装失败则直接退出（报告汇总必需）；
* ``EXTRA``    —— 尽力自动安装（单日并入总表需要），失败只告警不阻断。
"""

from __future__ import annotations

import os
import subprocess
import sys

REQUIRED = {"openpyxl": "openpyxl"}          # 模块名 -> pip 包名

# 单日数据并入总表用到的依赖：读 .xls / 写 .xls / 读写 .mdb
EXTRA = {
    "xlrd": "xlrd",
    "xlwt": "xlwt",
    "xlutils": "xlutils",
    "pyodbc": "pyodbc",
}

OPTIONAL = {**EXTRA}                          # 兼容旧调用方


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

    missing_extra = [pkg for mod, pkg in EXTRA.items() if not _have(mod)]
    if missing_extra:
        print("[提示] 正在安装「单日数据并入总表」所需的依赖：%s"
              % "、".join(missing_extra))
        if not _install(*missing_extra):
            print("[警告] 这些依赖没装上，只影响「单日数据并入总表」功能：")
            print("       %s -m pip install %s"
                  % (sys.executable, " ".join(missing_extra)))
        else:
            print("[完成] 依赖安装成功。")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
