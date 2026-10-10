# -*- coding: utf-8 -*-
"""带重试的人工 DWG 只读扫描（AutoCAD 忙时 COM 会报"被呼叫方拒绝接收呼叫"）。

用法: python scan_manual_retry.py <dwg> <out.json> [最多重试次数]
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

import pythoncom
import win32com.client


def scan_once(dwg: Path, out: Path) -> bool:
    pythoncom.CoInitialize()
    try:
        acad = win32com.client.GetActiveObject("AutoCAD.Application")
        doc, opened = None, False
        for d in acad.Documents:
            try:
                if Path(str(d.FullName)).name.lower() == dwg.name.lower():
                    doc = d
                    break
            except Exception:
                continue
        if doc is None:
            doc = acad.Documents.Open(str(dwg), True)
            opened = True
        layers = []
        for ly in doc.Layers:
            try:
                layers.append({"name": ly.Name, "on": ly.LayerOn})
            except Exception:
                pass
        counts = Counter()
        polys, lines, texts, hatches = [], [], [], []
        for ent in doc.ModelSpace:
            try:
                name = ent.ObjectName
            except Exception:
                continue
            counts[name] += 1
            try:
                if name in ("AcDbPolyline", "AcDb2dPolyline", "AcDb3dPolyline"):
                    coords = list(ent.Coordinates)
                    pts = [[round(coords[i], 3), round(coords[i + 1], 3)]
                           for i in range(0, len(coords) - 1, 2)]
                    polys.append({"layer": ent.Layer, "closed": bool(ent.Closed),
                                  "color": int(ent.Color), "pts": pts})
                elif name == "AcDbLine":
                    lines.append({"layer": ent.Layer,
                                  "a": [round(ent.StartPoint[0], 3), round(ent.StartPoint[1], 3)],
                                  "b": [round(ent.EndPoint[0], 3), round(ent.EndPoint[1], 3)]})
                elif name in ("AcDbText", "AcDbMText"):
                    ins = ent.InsertionPoint
                    texts.append({"kind": name, "layer": ent.Layer,
                                  "txt": str(ent.TextString),
                                  "pos": [round(ins[0], 3), round(ins[1], 3)],
                                  "h": round(float(ent.Height), 4)})
                elif name == "AcDbHatch":
                    rec = {"layer": ent.Layer, "pattern": str(ent.PatternName)}
                    try:
                        bb = ent.GeometricExtents
                        rec["cx"] = round((bb.MinPoint[0] + bb.MaxPoint[0]) / 2, 3)
                        rec["cy"] = round((bb.MinPoint[1] + bb.MaxPoint[1]) / 2, 3)
                    except Exception:
                        pass
                    hatches.append(rec)
            except Exception as exc:
                print("  entity err", name, exc)
        out.write_text(json.dumps({"dwg": str(dwg), "layers": layers,
                                   "counts": dict(counts), "polylines": polys,
                                   "lines": lines, "texts": texts, "hatches": hatches},
                                  ensure_ascii=False), encoding="utf-8")
        print("OK", dwg.name, dict(counts), "->", out.name, out.stat().st_size)
        if opened:
            try:
                doc.Close(False)
            except Exception:
                pass
        return True
    except Exception as exc:
        print("失败:", exc)
        return False
    finally:
        pythoncom.CoUninitialize()


def main() -> None:
    dwg, out = Path(sys.argv[1]), Path(sys.argv[2])
    tries = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    for k in range(tries):
        if scan_once(dwg, out):
            return
        wait = 8 + 4 * k
        print("  第 %d 次失败，等 %d 秒重试" % (k + 1, wait))
        time.sleep(wait)
    print("放弃:", dwg.name)


if __name__ == "__main__":
    main()
