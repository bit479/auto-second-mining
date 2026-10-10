# -*- coding: utf-8 -*-
"""给 3DMine「3DMIN PLUS」安装做最小可逆改动：备份菜单 + 新增 CodexPy 菜单组。

用法（需要写 E: 盘权限）：
  python patch_3dminplus.py apply
  python patch_3dminplus.py revert
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

BASE = Path(r"E:\gzRJ\3Dmine\3Dmine plus e无限台安装\3DMIN PLUS")
MENU = BASE / r"common\cui\3dmine_profile_chinese\00_标准界面\menu_default.xml"
PY_TOOLS = BASE / r"common\py_tools"
MACRO_SRC = Path(__file__).with_name("dm_probe_py2.py")
MACRO_DST = PY_TOOLS / "dm_probe_py2.py"
STAMP = "bak_codex_20261010"

VALUE = str(MACRO_DST)
GROUP = (
    '  <menu_group name="CodexPy(^K)">\n'
    '    <menu_item name="Probe API">\n'
    '      <Version ID="1.0" />\n'
    '      <Visibility value="yes" />\n'
    '      <Function name="" />\n'
    '      <Icon small_image_name="" large_image_name="" />\n'
    '      <Help Tip="dump 3DMine python api" HelpSource="AAA" />\n'
    '      <Macro Path ="' + VALUE + '" />\n'
    '    </menu_item>\n'
    '  </menu_group>\n'
)


def log(m: str) -> None:
    print(m, flush=True)


def apply() -> None:
    bak = MENU.with_name(MENU.name + "." + STAMP)
    if not bak.exists():
        shutil.copy2(MENU, bak)
        log("backup -> %s" % bak)
    else:
        log("backup exists -> %s" % bak)

    PY_TOOLS.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MACRO_SRC, MACRO_DST)
    log("macro deployed -> %s" % MACRO_DST)

    s = MENU.read_text(encoding="utf-8")
    if "CodexPy" in s:
        log("menu already patched")
        return
    idx = s.find("<3dmine_menu>")
    pos = s.find("\n", idx) + 1
    MENU.write_text(s[:pos] + GROUP + s[pos:], encoding="utf-8")
    log("menu group CodexPy inserted")


def revert() -> None:
    bak = MENU.with_name(MENU.name + "." + STAMP)
    if bak.exists():
        shutil.copy2(bak, MENU)
        log("restored <- %s" % bak)
    if MACRO_DST.exists():
        MACRO_DST.unlink()
        log("removed %s" % MACRO_DST)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "apply"
    if cmd == "apply":
        apply()
    elif cmd == "revert":
        revert()
    else:
        raise SystemExit("usage: patch_3dminplus.py [apply|revert]")
