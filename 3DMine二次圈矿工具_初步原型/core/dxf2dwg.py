# -*- coding: utf-8 -*-
"""DXF → DWG(2010/AC1024) 转换。**三条路，自动挑最快的**（用户 2026-10-18：嫌 COM 太慢）：

  ① **ODA File Converter**（Open Design Alliance 的免费转换器，不依赖 AutoCAD）——
     装了就用它，通常 1 秒内；路径靠 auto 探测或环境变量 `ODA_FILE_CONVERTER` 指定。
  ② **accoreconsole**（AutoCAD 自带的**无界面内核**）——不开 GUI、不走 COM，
     单独起一个进程，实测 **约 2 秒**（COM 那条要 6~7 秒，AutoCAD 没开时还要等它启 30~60 秒）。
  ③ **AutoCAD COM** —— 最后兜底（老路径）。

原则：
  * 任何一条路都**不碰用户已经打开的图纸**（accoreconsole 是独立进程；COM 只新开一个文档再关掉）；
  * 输出一律 2010 版（AC1024）；
  * 转换失败时保留 DXF，业务上由人工在 CAD 里另存兜底。

用法: python dxf2dwg.py <a.dxf> [a.dwg] [--start] [--via auto|oda|accore|com]
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
ODA_CANDIDATES = [
    r"C:\Program Files\ODA\ODAFileConverter 25.12.0\ODAFileConverter.exe",
    r"C:\Program Files\ODA\ODAFileConverter 25.6.0\ODAFileConverter.exe",
    r"C:\Program Files\ODA\ODAFileConverter 24.12.0\ODAFileConverter.exe",
    r"C:\Program Files (x86)\ODA\ODAFileConverter\ODAFileConverter.exe",
    r"E:\gzRJ\ODA\ODAFileConverter.exe",
]


def _find_oda():
    """找 ODA File Converter（免费、不依赖 AutoCAD）。装了才用。"""
    import os
    env = os.environ.get("ODA_FILE_CONVERTER", "").strip()
    if env and Path(env).exists():
        return Path(env)
    for p in ODA_CANDIDATES:
        if Path(p).exists():
            return Path(p)
    for root in (r"C:\Program Files\ODA", r"C:\Program Files (x86)\ODA", r"E:\gzRJ\ODA"):
        if Path(root).exists():
            hits = sorted(Path(root).rglob("ODAFileConverter.exe"))
            if hits:
                return hits[-1]
    return None


def _find_accore():
    """找 AutoCAD 的无界面内核 accoreconsole.exe（和 acad.exe 同目录）。"""
    for exe in ACAD_EXE_CANDIDATES:
        cand = Path(exe).with_name("accoreconsole.exe")
        if cand.exists():
            return cand
    for root in (r"E:\gzRJ\CAD", r"C:\Program Files\Autodesk"):
        if Path(root).exists():
            hits = sorted(Path(root).rglob("accoreconsole.exe"))
            if hits:
                return hits[-1]
    return None


def _dwg_head(p: Path) -> str:
    try:
        return p.read_bytes()[:6].decode("ascii", "ignore")
    except Exception:
        return ""


def _convert_oda(oda: Path, dxf: Path, dwg: Path, timeout_s: float = 120.0):
    """用 ODA File Converter 转（它按"输入目录→输出目录"批量转，所以先复制到临时目录）。"""
    import shutil
    import tempfile
    with tempfile.TemporaryDirectory(prefix="dxf2dwg_") as td:
        td = Path(td)
        src_dir, dst_dir = td / "in", td / "out"
        src_dir.mkdir()
        dst_dir.mkdir()
        shutil.copy2(dxf, src_dir / "in.dxf")
        # 参数：输入目录 输出目录 输出版本 输入格式 输出格式 是否递归 审核
        cmd = [str(oda), str(src_dir), str(dst_dir), "ACAD2010", "DXF", "DWG", "0", "1"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
        out = dst_dir / "in.dwg"
        if not out.exists():
            raise RuntimeError("ODA 没产出 DWG（返回码 %s）" % r.returncode)
        if dwg.exists():
            try:
                dwg.unlink()
            except Exception:
                dwg = dwg.with_name(dwg.stem + "_new" + dwg.suffix)
        shutil.move(str(out), str(dwg))
    return dwg


def _convert_accore(acc: Path, dxf: Path, dwg: Path, timeout_s: float = 180.0):
    """用 accoreconsole（无界面内核）转：脚本里 _SAVEAS 2010 → 退出。

    关键：**输入/输出都用临时目录里的 ASCII 文件名**再搬回去。
    中文路径在 accoreconsole 的脚本/命令行里会变成问号（脚本按 ANSI 解析），
    之前就因此静默失败、退回了慢的 COM。
    """
    import shutil
    import tempfile
    with tempfile.TemporaryDirectory(prefix="dxf2dwg_") as td:
        td = Path(td)
        src = td / "in.dxf"
        target = td / "out.dwg"
        shutil.copy2(dxf, src)
        scr = td / "conv.scr"
        scr.write_text("_SAVEAS\n2010\n%s\n_QUIT\n" % target, encoding="ascii")
        r = subprocess.run([str(acc), "/i", str(src), "/s", str(scr)],
                           capture_output=True, text=True, timeout=timeout_s,
                           errors="replace")
        if not target.exists():
            raise RuntimeError("accoreconsole 没产出 DWG（返回码 %s）" % r.returncode)
        out = dwg
        if out.exists():
            try:
                out.unlink()
            except Exception:
                out = dwg.with_name(dwg.stem + "_new" + dwg.suffix)
        shutil.move(str(target), str(out))
    return out


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
            quiet: bool = True, via: str = "auto") -> tuple:
    """返回 (成功?, 说明)。via: auto（默认，挑最快的）/ oda / accore / com。"""
    dxf = Path(dxf)
    dwg = Path(dwg) if dwg else dxf.with_name(dxf.stem + "_2010.dwg")
    dxf = dxf.resolve()
    dwg = dwg.resolve()
    if not dxf.exists():
        return False, "找不到 DXF：%s" % dxf
    # ---------- ① ODA File Converter（不依赖 AutoCAD，最快）----------
    if via in ("auto", "oda"):
        oda = _find_oda()
        if oda is not None:
            t0 = time.time()
            try:
                out = _convert_oda(oda, dxf, dwg)
                return True, "DWG 版本头 %s，%.1f KB（ODA File Converter，不依赖 AutoCAD，用时 %.1f 秒）" % (
                    _dwg_head(out), out.stat().st_size / 1024.0, time.time() - t0)
            except Exception as exc:
                print("[dxf2dwg] ODA 转换失败，换下一条路：%s" % exc)
        elif via == "oda":
            return False, "没找到 ODA File Converter（可用环境变量 ODA_FILE_CONVERTER 指定路径）"
    # ---------- ② accoreconsole（AutoCAD 无界面内核，不开 GUI/不走 COM）----------
    if via in ("auto", "accore"):
        acc = _find_accore()
        if acc is not None:
            t0 = time.time()
            try:
                out = _convert_accore(acc, dxf, dwg)
                return True, "DWG 版本头 %s，%.1f KB（accoreconsole 无界面内核，用时 %.1f 秒）" % (
                    _dwg_head(out), out.stat().st_size / 1024.0, time.time() - t0)
            except Exception as exc:
                print("[dxf2dwg] accoreconsole 转换失败，退回 AutoCAD COM：%s" % exc)
        elif via == "accore":
            return False, "没找到 accoreconsole.exe"
    # ---------- ③ AutoCAD COM（老路径，最后兜底）----------
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
    alt = None
    try:
        doc = acad.Documents.Open(str(dxf), True)      # 只读打开
        time.sleep(1.5)
        if dwg.exists():
            try:
                dwg.unlink()
            except Exception:
                pass
        try:
            doc.SaveAs(str(dwg), ACAD_ENUM_2010)
        except Exception:
            # 目标 DWG 被占着（最常见：这张图正开在 AutoCAD 里）→ 换个名字存，
            # 免得整步白跑（用户 2026-10-15 就是这么撞上的）
            alt = dwg.with_name(dwg.stem + "_new" + dwg.suffix)
            doc.SaveAs(str(alt), ACAD_ENUM_2010)
            dwg = alt
        time.sleep(1.0)
        head = dwg.read_bytes()[:6].decode("ascii", "ignore") if dwg.exists() else ""
        if not dwg.exists():
            return False, "SaveAs 未生成文件"
        tail = ("（原来那个 .dwg 被占着——多半是你正开着它；这份是新存的：%s）"
                % alt.name) if alt else ""
        return True, "DWG 版本头 %s（AC1024=DWG2010），%.1f KB%s" % (
            head, dwg.stat().st_size / 1024.0, tail)
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
    via = "auto"
    args = sys.argv[2:]
    for i, a in enumerate(args):
        if a == "--via" and i + 1 < len(args):
            via = args[i + 1]
        elif a.startswith("--via="):
            via = a.split("=", 1)[1]
        elif not a.startswith("--") and (i == 0 or args[i - 1] != "--via"):
            dwg = Path(a)
    ok, msg = convert(dxf, dwg, start="--start" in sys.argv, quiet=False, via=via)
    print(("OK  " if ok else "FAIL ") + msg)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
