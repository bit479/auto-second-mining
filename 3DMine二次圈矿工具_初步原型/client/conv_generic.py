# -*- coding: utf-8 -*-
"""Step3 通用 DXF -> DWG2010 转换（参数化）：
用法: python conv_generic.py <dxf> [dwg]
  dxf : Step2 产出的 <blast_id>_二次圈矿矿块图_full.dxf
  dwg : 输出 DWG（AutoCAD 2010 / AC1024），缺省 = dxf 同名 .dwg
依赖: 本机 AutoCAD（COM）。COM 挂起时可在 AutoCAD 里手动另存为 2010 格式兜底。
"""
from __future__ import annotations
import os
import sys
import time
import threading
from pathlib import Path

import win32com.client
import pythoncom

DXF = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\sample_data\output\1004_macro\3940平台 1004二次圈矿矿块图_3块版_full.dxf")
DWG = Path(sys.argv[2]) if len(sys.argv) > 2 else DXF.with_name(DXF.stem + "_2010.dwg")

result = {"acad": None, "err": None}


def connect():
    try:
        pythoncom.CoInitialize()
        result["acad"] = win32com.client.Dispatch("AutoCAD.Application")
    except Exception as ex:
        result["err"] = ex


t = threading.Thread(target=connect, daemon=True)
t.start()
t.join(30)
if result["acad"] is None:
    print("FAIL connect:", result["err"], flush=True)
    sys.exit(1)
acad = result["acad"]
print("COM connected", flush=True)
try:
    acad.Visible = True
except Exception:
    pass
time.sleep(2)

try:
    doc = acad.Documents.Open(str(DXF), True)
    print("opened dxf", flush=True)
except Exception as ex:
    print("Open err:", ex, flush=True)
    print("提示：请先关闭所有 AutoCAD 窗口（或等待其就绪）后重试本脚本；", flush=True)
    print(f"也可手动在 AutoCAD 中打开 {DXF}，另存为 AutoCAD 2010/LT2010 图形(*.dwg) 到 {DWG}。", flush=True)
    sys.exit(1)
time.sleep(5)
if DWG.exists():
    try:
        DWG.unlink()
    except Exception:
        pass
doc.SaveAs(str(DWG), 48)
time.sleep(2)
with open(DWG, "rb") as fp:
    head = fp.read(6).decode("ascii", errors="ignore")
print("DWG:", DWG, "head:", head, "size:", DWG.stat().st_size, flush=True)
try:
    doc.Close(False)
except Exception:
    pass
print("DONE", flush=True)
