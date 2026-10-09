# -*- coding: utf-8 -*-
"""v4h 直连现有 acad 实例转换（不杀不启，带线程超时保护）。"""
import os, sys, time, threading

DXF = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\sample_data\output\1004_macro\3940平台 1004二次圈矿矿块图_3块版_full.dxf"
DWG = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\sample_data\output\3940平台 1004二次圈矿矿块图_3块版_2010.dwg"

import win32com.client
import pythoncom

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
    doc = acad.Documents.Open(DXF, True)
    print("opened dxf", flush=True)
except Exception as ex:
    print("Open err:", ex, flush=True)
    try:
        doc = acad.ActiveDocument
        print("use active doc", flush=True)
    except Exception:
        sys.exit(1)
time.sleep(5)
if os.path.exists(DWG):
    try:
        os.remove(DWG)
    except Exception:
        pass
doc.SaveAs(DWG, 48)
time.sleep(2)
with open(DWG, "rb") as fp:
    head = fp.read(6).decode("ascii", errors="ignore")
print("DWG:", DWG, "head:", head, "size:", os.path.getsize(DWG), flush=True)
try:
    doc.Close(False)
except Exception:
    pass
print("DONE", flush=True)
