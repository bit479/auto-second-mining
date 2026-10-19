# -*- coding: utf-8 -*-
"""Excel 工具里的 .bak 收纳：所有备份统一放进同目录的 ``bak/`` 子文件夹。"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

BAK_DIRNAME = "bak"


def bak_dir(path, create: bool = False) -> Path:
    p = Path(path)
    folder = p if p.is_dir() else p.parent
    out = folder / BAK_DIRNAME
    if create:
        out.mkdir(parents=True, exist_ok=True)
    return out


def unique_path(folder, name: str) -> Path:
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


def collect_bak_files(folder, quiet: bool = False) -> list:
    """把 folder 第一层的 .bak 全部移进 folder/bak/。"""
    folder = Path(folder)
    if not folder.is_dir():
        return []
    moved = []
    for p in sorted(folder.iterdir()):
        if not p.is_file():
            continue
        low = p.name.lower()
        if not (low.endswith(".bak") or ".bak-" in low):
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
    return moved
