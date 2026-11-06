# -*- coding: utf-8 -*-
"""把单文件 exe 打成可发布的 zip（exe + 使用说明 + 版本记录 + 校验值）。

用法::

    python _probe/make_release_exe.py            # 版本取自 paths.APP_VERSION（v1.17）
    python _probe/make_release_exe.py v1.17      # 也可显式指定

产物::

    auto-second-mining/release_v1/second-mining-workbench-v1.17-win64.zip
        └─ 二次圈矿智能工作台-v1.17/
             ├─ 二次圈矿智能工作台.exe
             ├─ 使用说明.txt
             ├─ 版本更新记录.md
             └─ SHA256SUMS.txt

同时写一个 `.zip.sha256` 旁路校验文件，方便发版时直接贴到 Release 说明里。
"""

from __future__ import annotations

import hashlib
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST_EXE = ROOT / "dist" / "二次圈矿智能工作台.exe"
RELEASE_DIR = ROOT.parent / "release_v1"
DOCS = ROOT / "docs"

APP_NAME = "二次圈矿智能工作台"


def project_version() -> str:
    src = (ROOT / "client" / "ui_v2" / "services" / "paths.py").read_text(encoding="utf-8")
    m = re.search(r'APP_VERSION\s*=\s*"v?([0-9.]+)"', src)
    return m.group(1) if m else "0.0"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


README_TXT = """%(name)s  v%(ver)s
================================================================

一、这是什么
    一套 3DMine 二次圈矿辅助工具：炮孔数据库生成、单炮区二次圈矿、批量处理、
    人工圈矿标定、综合图管理、Excel 数据工具、参数管理、验收与诊断。
    圈矿算法与 Excel 口径沿用原有实现，界面是新的桌面工作台。

二、三步上手
    1) 把本目录解压到可写位置（例如 D:\\工具\\二次圈矿\\，不要放 C:\\Program Files\\ 根下）
    2) 双击  %(name)s.exe
       首次运行会在旁边生成 data\\（参数、品位分级、3DMine 模板、最近记录）
    3) 把坐标 TXT 拖进窗口任意位置 —— 会自动识别平台/日期、解析炮孔，
       并跳到「炮孔数据库生成」页填好参数与数据

三、环境要求
    · Windows 10 1809+ / Windows 11，64 位
    · 不需要安装 Python、PySide6 或 VC 运行库；全程离线
    · AutoCAD 仅在勾选「圈完转 DWG 2010」时需要（不勾则只出 DXF）

四、常见问题
    · SmartScreen 提示"未知发布者" → 更多信息 → 仍要运行（exe 未做代码签名）
    · 杀毒软件拦截 → 把本目录加入信任（单文件 exe 偶发误报）
    · 提示无法写 data → exe 放在了只读目录，换到可写目录
    · 冷启动 10~15 秒属正常（单文件需要解包）

五、文件与校验
    · 版本更新记录.md   本版改了什么
    · SHA256SUMS.txt    exe 与 zip 的校验值
      certutil -hashfile %(zip)s SHA256

六、回退
    需要旧版行为时，直接用旧的 exe；data\\ 目录结构（圈矿参数.json、
    excel_tools\\config\\grade_profiles.json）与旧版完全兼容。
"""


def main() -> int:
    tag = sys.argv[1] if len(sys.argv) > 1 else "v%s" % project_version()
    tag = tag if tag.startswith("v") else "v" + tag
    ver = tag.lstrip("v")

    if not DIST_EXE.exists():
        print("[失败] 找不到 exe：%s\n先跑 打包exe.bat" % DIST_EXE)
        return 2

    top = "%s-%s" % (APP_NAME, tag)
    stage = ROOT / "build" / ("_release_%s" % tag.replace(".", ""))
    stage.mkdir(parents=True, exist_ok=True)
    pkg = stage / top
    if pkg.exists():
        for old in sorted(pkg.rglob("*"), reverse=True):
            try:
                old.unlink() if old.is_file() else old.rmdir()
            except OSError:
                pass
    pkg.mkdir(parents=True, exist_ok=True)

    # 1) exe
    exe_dst = pkg / (APP_NAME + ".exe")
    exe_dst.write_bytes(DIST_EXE.read_bytes())
    exe_hash = sha256(exe_dst)
    print("  + exe   %.1f MB  sha256=%s…" % (exe_dst.stat().st_size / 1048576, exe_hash[:16]))

    # 2) 使用说明
    zip_name = "second-mining-workbench-%s-win64.zip" % tag
    (pkg / "使用说明.txt").write_text(
        README_TXT % {"name": APP_NAME, "ver": ver, "zip": zip_name},
        encoding="utf-8", newline="\r\n")
    print("  + 使用说明.txt")

    # 3) 版本更新记录（直接复用 docs 里那份）
    note = DOCS / ("发布说明_%s.md" % tag)
    if note.exists():
        (pkg / "版本更新记录.md").write_bytes(note.read_bytes())
        print("  + 版本更新记录.md  ← docs/%s" % note.name)

    # 4) 校验值
    (pkg / "SHA256SUMS.txt").write_text(
        "%s  %s.exe\n" % (exe_hash, APP_NAME), encoding="utf-8")

    # 5) 打 zip
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = RELEASE_DIR / zip_name
    if zip_path.exists():
        bak = zip_path.with_suffix(".zip.old")
        try:
            zip_path.replace(bak)
        except OSError:
            pass
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(pkg.rglob("*")):
            if p.is_file():
                z.write(p, "%s/%s" % (top, p.relative_to(pkg).as_posix()))
    zip_hash = sha256(zip_path)
    (RELEASE_DIR / (zip_name + ".sha256")).write_text(
        "%s  %s\n" % (zip_hash, zip_name), encoding="utf-8")

    print("\n" + "=" * 70)
    print("发布包：%s" % zip_path)
    print("体积  ：%.1f MB" % (zip_path.stat().st_size / 1048576))
    print("SHA256：%s" % zip_hash)
    print("解包后：%s\\（%d 个文件）" % (top, len(list(pkg.rglob('*')))))
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
