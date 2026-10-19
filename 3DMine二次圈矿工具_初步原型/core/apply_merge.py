# -*- coding: utf-8 -*-
"""把"并入后的副本"正式替换掉综合图原件——**先自动备份，可一键回退**。

用法:
  python apply_merge.py "<…_并入1008.dwg>" [--original "<综合图.dwg>"] [--dry-run]

做的事（每一步都打印，出问题能照原样退回去）：
  ① 校验副本与原件都存在；
  ② 原件改名备份成 `<原名>_原版_YYYYmmdd_HHMMSS.dwg`（不删除任何东西）；
  ③ 副本**复制**成原件的名字（副本自己保留）；
  ④ 打印回退命令：把备份改回原名即可。

--dry-run 只演练、不动文件。
"""
from __future__ import annotations

import re
import shutil
import sys
import time
from pathlib import Path

try:
    from bak_housekeeping import collect_bak_files
except ImportError:                       # 作为 core 包导入时
    from .bak_housekeeping import collect_bak_files


def guess_original(merged: Path) -> Path:
    """从 `<原stem>_并入<tag>.dwg` 猜回原名。"""
    m = re.match(r"^(.*?)_并入.+$", merged.stem)
    if m:
        return merged.with_name(m.group(1) + merged.suffix)
    return None


def apply_merge(merged: Path, original: Path = None, dry_run: bool = False):
    merged = Path(merged)
    if not merged.exists():
        return False, "找不到并入后的副本：%s" % merged
    original = Path(original) if original else guess_original(merged)
    if original is None:
        return False, "猜不出原件名，请用 --original 指定"
    if not original.exists():
        return False, "找不到综合图原件：%s" % original
    if original.resolve() == merged.resolve():
        return False, "原件与副本是同一个文件"
    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = original.with_name("%s_原版_%s%s" % (original.stem, stamp, original.suffix))
    steps = [
        "① 原件改名备份：%s  →  %s" % (original.name, backup.name),
        "② 副本复制为原件名：%s  →  %s" % (merged.name, original.name),
        "   （副本本身保留，可反复替换）",
        "③ 回退：把 %s 改回 %s 即可" % (backup.name, original.name),
    ]
    print("\n".join(("   " + s) for s in steps))
    if dry_run:
        print("   （--dry-run：只演练，没有动任何文件）")
        return True, "演练通过"
    try:
        original.rename(backup)
    except Exception as exc:
        return False, "备份原件失败（什么都没改）：%s" % exc
    try:
        shutil.copy2(merged, original)
    except Exception as exc:
        # 复制失败就往回滚
        try:
            backup.rename(original)
            return False, "复制副本失败，已把备份改回原名：%s" % exc
        except Exception:
            return False, "复制副本失败，且回滚失败！请手工把 %s 改回 %s（%s）" % (
                backup.name, original.name, exc)
    collect_bak_files(original.parent)
    return True, "已替换；原件备份 = %s" % backup


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        return
    merged = Path(sys.argv[1])
    original = None
    if "--original" in sys.argv:
        i = sys.argv.index("--original")
        original = Path(sys.argv[i + 1])
    ok, msg = apply_merge(merged, original, dry_run="--dry-run" in sys.argv)
    print(("OK  " if ok else "FAIL ") + msg)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
