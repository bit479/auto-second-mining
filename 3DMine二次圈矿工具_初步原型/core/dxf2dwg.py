# -*- coding: utf-8 -*-
"""DXF → DWG(2010/AC1024) 转换（走本机 AutoCAD COM）。

用法: python dxf2dwg.py <a.dxf> [a.dwg] [--start]
  --start : 若 AutoCAD 没开就启动它（缺省只挂已开的，不动用户的图）

原则：
  * 只 **新开** 一个文档来转换，绝不改动/关闭用户已经打开的图纸；
  * 转换完把自己开的那个文档关掉；
  * SaveAs 类型 48 = ac2010_dwg（AC1024 = R2010）；
  * 转换失败时保留 DXF，业务上由人工在 CAD 里另存兜底。
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ACAD_ENUM_2010 = 48          # ac2010_dwg
ACAD_EXE_CANDIDATES = [
    r"E:\gzRJ\CAD\AutoCAD 2023\acad.exe",
    r"C:\Program Files\Autodesk\AutoCAD 2023\acad.exe",
]


def _acad_running() -> bool:
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq acad.exe"],
                         capture_output=True, text=True, errors="replace").stdout
    return "acad.exe" in out.lower()


def _start_acad() -> None:
    for exe in ACAD_EXE_CANDIDATES:
        if Path(exe).exists():
            subprocess.Popen([exe], cwd=str(Path(exe).parent))
            return


def _connect(timeout_s: float = 120.0, start: bool = False):
    import pythoncom
    import win32com.client
    pythoncom.CoInitialize()
    if start and not _acad_running():
        _start_acad()
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        try:
            return win32com.client.Dispatch("AutoCAD.Application")
        except Exception:
            time.sleep(2)
    return None


def convert(dxf: Path, dwg: Path = None, start: bool = False,
            quiet: bool = True) -> tuple:
    """返回 (成功?, 说明)。"""
    dxf = Path(dxf)
    dwg = Path(dwg) if dwg else dxf.with_name(dxf.stem + "_2010.dwg")
    if not dxf.exists():
        return False, "找不到 DXF：%s" % dxf
    acad = _connect(start=start)
    if acad is None:
        return False, "AutoCAD COM 未就绪（可在 CAD 里手工打开 DXF 另存 2010）"
    pythoncom_ok = True
    try:
        import pythoncom
        acad.Visible = not quiet
    except Exception:
        pythoncom_ok = False
    doc = None
    try:
        doc = acad.Documents.Open(str(dxf), True)      # 只读打开
        time.sleep(1.5)
        if dwg.exists():
            try:
                dwg.unlink()
            except Exception:
                pass
        doc.SaveAs(str(dwg), ACAD_ENUM_2010)
        time.sleep(1.0)
        head = dwg.read_bytes()[:6].decode("ascii", "ignore") if dwg.exists() else ""
        if not dwg.exists():
            return False, "SaveAs 未生成文件"
        return True, "DWG 版本头 %s（AC1024=DWG2010），%.1f KB" % (
            head, dwg.stat().st_size / 1024.0)
    except Exception as exc:
        return False, "转换异常：%s" % exc
    finally:
        if doc is not None:
            try:
                doc.Close(False)
            except Exception:
                pass
        if pythoncom_ok:
            try:
                import pythoncom
                pythoncom.CoUninitialize()
            except Exception:
                pass


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        return
    dxf = Path(sys.argv[1])
    dwg = None
    for a in sys.argv[2:]:
        if not a.startswith("--"):
            dwg = Path(a)
    ok, msg = convert(dxf, dwg, start="--start" in sys.argv, quiet=False)
    print(("OK  " if ok else "FAIL ") + msg)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
