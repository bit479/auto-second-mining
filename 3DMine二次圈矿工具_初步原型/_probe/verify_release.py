# -*- coding: utf-8 -*-
"""发布包"冷启动"验收：解压到临时目录 → 校验 SHA256 → 直接运行 → 检查 data\\。"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZIP = ROOT.parent / "release_v1" / "second-mining-workbench-v1.17-win64.zip"
APP = "二次圈矿智能工作台"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ok = True
    print("发布包：", ZIP, "存在：", ZIP.exists())
    if not ZIP.exists():
        return 2

    with zipfile.ZipFile(ZIP) as z:
        names = z.namelist()
        print("\n[1] 包内文件（%d 个）：" % len(names))
        for n in names:
            print("    %-58s %10d" % (n, z.getinfo(n).file_size))
        bad = [n for n in names if "__pycache__" in n or n.endswith(".pyc")]
        print("    无缓存文件：", "是" if not bad else "否 %s" % bad)
        ok &= not bad

        dest = Path(tempfile.mkdtemp(prefix="release_check_"))
        stage = dest / "解压目标"
        z.extractall(stage)

    top = next(stage.iterdir())
    exe = top / (APP + ".exe")
    print("\n[2] 解压目录：", top.name, "| exe 存在：", exe.exists())
    ok &= exe.exists()

    sums = (top / "SHA256SUMS.txt").read_text(encoding="utf-8").split()
    want = sums[0] if sums else ""
    got = sha256(exe)
    print("    exe SHA256 期望：", want[:24], "…")
    print("    exe SHA256 实际：", got[:24], "…")
    print("    一致：", "是" if want == got else "否")
    ok &= want == got

    print("\n[3] 在干净目录直接运行（不依赖源码树）…")
    shot = dest / "shot.png"
    t0 = time.time()
    p = subprocess.Popen([str(exe), "--shot", str(shot), "--page", "dashboard",
                          "--size", "1400x860"], cwd=str(dest))
    while not shot.exists() and time.time() - t0 < 90:
        time.sleep(0.2)
    dt = time.time() - t0
    print("    启动+截图：%.1f 秒，截图 %s（%d 字节）"
          % (dt, "已生成" if shot.exists() else "未生成", shot.stat().st_size if shot.exists() else 0))
    ok &= shot.exists()
    try:
        p.wait(timeout=20)
    except Exception:
        p.kill()

    data = exe.parent / "data"
    need = [data / "圈矿参数.json",
            data / "excel_tools" / "config" / "grade_profiles.json",
            data / "assets" / "3dmine_template.mdb"]
    print("\n[4] 首次运行生成 data\\：", data.exists())
    for f in need:
        print("    %-56s %s" % (f.relative_to(exe.parent), "有" if f.exists() else "缺"))
    ok &= data.exists() and all(f.exists() for f in need)

    print("\n" + "=" * 70)
    print("结论：" + ("✅ 发布包可直接分发运行" if ok else "❌ 有问题，见上"))
    print("临时解压目录：%s（确认后可删）" % dest)
    print("=" * 70)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
