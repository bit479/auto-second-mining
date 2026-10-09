# -*- coding: utf-8 -*-
"""探测本机 CAD/DWG 相关环境：COM 组件、ODA、LibreDWG、常用 CAD 安装。"""
import os, sys, glob, subprocess

def probe_com():
    import win32com.client
    progids = [
        "AutoCAD.Application", "AutoCAD.Application.25", "AutoCAD.Application.24",
        "ZwCAD.Application", "ZWCAD.Application", "Zcad.Application",
        "Gcad.Application", "GstarCAD.Application", "GstarCAD.Application.26",
        "CADAssist.Application", "HcCAD.Application", "BricsCAD.Application",
        "VisualMine.Application", "3DMine.Application",
    ]
    found = []
    for p in progids:
        try:
            obj = win32com.client.Dispatch(p)
            found.append((p, "OK"))
        except Exception as e:
            found.append((p, "no"))
    for p, s in found:
        print(f"COM {p}: {s}")

def probe_oda():
    pats = [
        r"C:\Program Files\ODA\ODAFileConverter*",
        r"C:\Program Files (x86)\ODA\ODAFileConverter*",
        r"D:\*\ODA*", r"E:\*\ODA*",
    ]
    hits = []
    for pat in pats:
        hits += glob.glob(pat)
    print("ODA:", hits if hits else "not found")

def probe_libredwg():
    import shutil
    for exe in ["dwgwrite", "dwg2dxf", "dxf2dwg", "libredwg-dwgwrite"]:
        p = shutil.which(exe)
        print(f"LibreDWG {exe}: {p if p else 'no'}")

def probe_cad_dirs():
    roots = ["C:\\Program Files", "C:\\Program Files (x86)", "D:\\", "E:\\"]
    names = ["autocad", "zwcad", "中望", "gstarcad", "浩辰", "bricscad", "qcad", "librecad", "oda"]
    for r in roots:
        if not os.path.isdir(r):
            continue
        try:
            for d in os.listdir(r):
                dl = d.lower()
                if any(n in dl for n in names):
                    print("DIR:", os.path.join(r, d))
        except Exception:
            pass

def probe_dxf_dwg_tools():
    import shutil
    for exe in ["ezdxf", "dwgread", "teigha", "dwg2dxf"]:
        p = shutil.which(exe)
        if p:
            print(f"TOOL {exe}: {p}")

probe_com()
probe_oda()
probe_libredwg()
probe_cad_dirs()
probe_dxf_dwg_tools()
print("DONE")
