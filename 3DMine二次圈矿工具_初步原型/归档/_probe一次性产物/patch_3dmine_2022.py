# -*- coding: utf-8 -*-
"""给 3DMine 2022 安装做最小可逆改动：备份 + 设 m_pyPath + 新增 CodexPy 菜单组。

用法（需要写 E: 盘权限）：
  python patch_3dmine_2022.py apply
  python patch_3dmine_2022.py revert
"""
from __future__ import annotations

import re
import shutil
import sys
import time
from pathlib import Path

BASE = Path(r"E:\gzRJ\3Dmine\2022")
MENU = BASE / r"common\cui\3dmine_profile_chinese\00_标准界面\menu_default.xml"
APPSET = BASE / r"common\config\appsetting.txt"
PY_TOOLS = BASE / r"common\py_tools"
MACRO_SRC = Path(__file__).with_name("dm_probe_api.py")
MACRO_DST = PY_TOOLS / "dm_probe_api.py"
PY_DLL = BASE / r"bin\nt_x64\python39.dll"
STAMP = "bak_codex_20261009"

GROUP = """  <menu_group name="CodexPy(^K)">
    <menu_item name="Probe API">
      <Version ID="1.0" />
      <Visibility value="yes" />
      <Function name="" />
      <Icon small_image_name="" large_image_name="" />
      <Help Tip="dump 3DMine python api" HelpSource="AAA" />
      <Macro Path ="E:\\gzRJ\\3Dmine\\2022\\common\\py_tools\\dm_probe_api.py" />
    </menu_item>
    <menu_item name="Probe API rel1">
      <Version ID="1.0" />
      <Visibility value="yes" />
      <Function name="" />
      <Icon small_image_name="" large_image_name="" />
      <Help Tip="relative variant 1" HelpSource="AAA" />
      <Macro Path ="py_tools\\dm_probe_api.py" />
    </menu_item>
    <menu_item name="Probe API rel2">
      <Version ID="1.0" />
      <Visibility value="yes" />
      <Function name="" />
      <Icon small_image_name="" large_image_name="" />
      <Help Tip="relative variant 2" HelpSource="AAA" />
      <Macro Path ="..\\py_tools\\dm_probe_api.py" />
    </menu_item>
  </menu_group>
"""


def log(msg: str) -> None:
    print(msg, flush=True)


def backup(path: Path) -> Path:
    dst = path.with_name(path.name + "." + STAMP)
    if not dst.exists():
        shutil.copy2(path, dst)
        log("backup -> %s" % dst)
    else:
        log("backup exists -> %s" % dst)
    return dst


def apply() -> None:
    log("time=%s" % time.strftime("%Y-%m-%d %H:%M:%S"))
    backup(MENU)
    backup(APPSET)

    PY_TOOLS.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MACRO_SRC, MACRO_DST)
    log("macro deployed -> %s" % MACRO_DST)

    s = APPSET.read_text(encoding="gbk", errors="replace")
    new_line = "m_pyPath=" + str(PY_DLL)
    if re.search(r"(?m)^m_pyPath=.*$", s):
        s = re.sub(r"(?m)^m_pyPath=.*$", lambda _m: new_line, s)
    else:
        s = s.rstrip("\r\n") + "\n" + new_line + "\n"
    APPSET.write_text(s, encoding="gbk")
    log("appsetting m_pyPath -> %s" % PY_DLL)

    m = MENU.read_text(encoding="utf-8")
    if "CodexPy" in m:
        log("menu already patched")
    else:
        idx = m.find("<3dmine_menu>")
        pos = m.find("\n", idx) + 1
        m = m[:pos] + GROUP + m[pos:]
        MENU.write_text(m, encoding="utf-8")
        log("menu group CodexPy inserted")


def revert() -> None:
    for p in (MENU, APPSET):
        b = p.with_name(p.name + "." + STAMP)
        if b.exists():
            shutil.copy2(b, p)
            log("restored <- %s" % b)
        else:
            log("no backup for %s" % p)
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
        raise SystemExit("usage: patch_3dmine_2022.py [apply|revert]")
