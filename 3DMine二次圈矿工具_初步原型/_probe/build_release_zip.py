# -*- coding: utf-8 -*-
"""打一个"绿色包" zip（发 Release 用）。

用法: python _probe/build_release_zip.py v1.0.1
产出: D:\\WK\\N CRT\\release_v1\\second-mining-tool-v1.0.1.zip
      （解包后是 second-mining-tool-v1.0.1/ 一个目录，里面就是可直接双击的整套）
排除: .git、__pycache__、3dmine_scripts（旧调试图）、sample_data/output 里的对账/GUI 跑通中间产物、
      归档/、*.bmp/*.bak、以及根目录那些一次性 log/txt。
"""
from __future__ import annotations

import fnmatch
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT.parent / "release_v1"

# build / dist / release_v1 是打包产物（几百 MB 的 exe 与中间文件），不进源码包；
# exe 走单独的 Release 资产。
EXCLUDE_DIRS = {".git", "__pycache__", "3dmine_scripts", "归档", "_out",
                "build", "dist", "release_v1", "_buildenv", "_replaced"}
EXCLUDE_FILE_GLOBS = ["*.bmp", "*.bak", "*.pyc", "*.dwl", "*.dwl2",
                      "pip_install_log.txt", "pip_scipy_log.txt", "tk_check.txt",
                      "tk_check2.txt", "win_state.txt", "holes_1008.txt",
                      "bat_test.txt", "deps_check.txt", "运行记录.txt",
                      ".ui_state.json", "*.spec"]
EXCLUDE_PATH_PARTS = ("sample_data/output/对账_", "sample_data/output/GUI跑通_",
                      "sample_data/output/AUTOCAD自检")


def keep(p: Path) -> bool:
    rel = p.relative_to(ROOT)
    if any(part in EXCLUDE_DIRS for part in rel.parts):
        return False
    s = str(rel).replace("\\", "/")
    if any(x in s for x in EXCLUDE_PATH_PARTS):
        return False
    return not any(fnmatch.fnmatch(p.name, g) for g in EXCLUDE_FILE_GLOBS)


def main() -> int:
    tag = sys.argv[1] if len(sys.argv) > 1 else "v1.0.1"
    top = "second-mining-tool-%s" % tag
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = OUT_DIR / ("%s.zip" % top)
    n = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(ROOT.rglob("*")):
            if not p.is_file() or not keep(p):
                continue
            z.write(p, "%s/%s" % (top, p.relative_to(ROOT).as_posix()))
            n += 1
    print("打包完成：%s（%d 个文件，%.2f MB）" % (zip_path, n, zip_path.stat().st_size / 1048576))
    return 0


if __name__ == "__main__":
    sys.exit(main())
