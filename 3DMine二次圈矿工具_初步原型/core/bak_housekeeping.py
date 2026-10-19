# -*- coding: utf-8 -*-
"""把 .bak 备份统一收进"同目录下的 bak 子文件夹"。

用户 2026-10-19：程序产生的 .bak 和文件夹里原本的 .bak 混在一起太乱，
要求在每个 .bak 所在文件夹里新建一个文件夹，把 .bak 全部收进去。

约定：
  * 文件夹名固定为 ``bak``（常量 :data:`BAK_DIRNAME`）；
  * 只处理**当前文件夹第一层**的 .bak，不递归、不动 bak 子文件夹里的东西；
  * 同名已存在时自动加 ``-2``、``-3``，绝不覆盖；
  * 文件被 CAD 占用时只提示、不中断。
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

BAK_DIRNAME = "bak"


def bak_dir(path, create: bool = False) -> Path:
    """返回 ``path`` 同目录下的 bak 文件夹（path 可以是文件或文件夹）。"""
    p = Path(path)
    folder = p if p.is_dir() else p.parent
    out = folder / BAK_DIRNAME
    if create:
        out.mkdir(parents=True, exist_ok=True)
    return out


def unique_path(folder, name: str) -> Path:
    """在 folder 里给 name 找一个不冲突的名字：foo.bak -> foo-2.bak。"""
    folder = Path(folder)
    cand = folder / name
    if not cand.exists():
        return cand
    stem, ext = os.path.splitext(name)
    i = 2
    while True:
        cand = folder / ("%s-%d%s" % (stem, i, ext))
        if not cand.exists():
            return cand
        i += 1


def is_bak_name(name: str) -> bool:
    low = name.lower()
    return low.endswith(".bak") or ".bak-" in low


def collect_bak_files(folder, quiet: bool = False) -> list:
    """把 folder 第一层的 .bak 全部移进 folder/bak/，返回 [(原路径, 新路径)]。"""
    folder = Path(folder)
    if not folder.is_dir():
        return []
    moved = []
    for p in sorted(folder.iterdir()):
        if not p.is_file() or not is_bak_name(p.name):
            continue
        target_dir = folder / BAK_DIRNAME
        target_dir.mkdir(exist_ok=True)
        dst = unique_path(target_dir, p.name)
        try:
            shutil.move(str(p), str(dst))
            moved.append((p, dst))
        except Exception as exc:
            if not quiet:
                print("[提示] .bak 收纳失败（可能正被占用）：%s（%s）" % (p.name, exc))
    if moved and not quiet:
        print("    已把 %d 个 .bak 收进 %s" % (len(moved), folder / BAK_DIRNAME))
    return moved
