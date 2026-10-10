# -*- coding: utf-8 -*-
"""只读扫描人工 DWG（附加到已在运行的 AutoCAD，不启动、不关闭、不改动）。

用法: python scan_manual_dwg.py <dwg> <out.json> [--census]
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

import pythoncom
import win32com.client


def get_doc(acad, dwg: Path):
    for d in acad.Documents:
        try:
            if Path(str(d.FullName)).name.lower() == dwg.name.lower():
                return d, False
        except Exception:
            continue
    return acad.Documents.Open(str(dwg), True), True


def main() -> None:
    dwg = Path(sys.argv[1])
    out = Path(sys.argv[2])
    census_only = "--census" in sys.argv

    pythoncom.CoInitialize()
    acad = win32com.client.GetActiveObject("AutoCAD.Application")
    print("attached:", acad.Name, acad.Version)
    doc, opened = get_doc(acad, dwg)
    print("document:", doc.Name, "opened_new=", opened)

    layers = []
    for ly in doc.Layers:
        try:
            layers.append({"name": ly.Name, "color": ly.Color, "on": ly.LayerOn})
        except Exception:
            layers.append({"name": ly.Name})

    counts = Counter()
    polys, lines, texts, hatches = [], [], [], []
    t0 = time.time()
    for ent in doc.ModelSpace:
        try:
            name = ent.ObjectName
        except Exception:
            continue
        counts[name] += 1
        if census_only:
            continue
        try:
            if name in ("AcDbPolyline", "AcDb2dPolyline", "AcDb3dPolyline"):
                coords = list(ent.Coordinates)
                pts = [[round(coords[i], 3), round(coords[i + 1], 3)]
                       for i in range(0, len(coords) - 1, 2)]
                polys.append({"layer": ent.Layer, "closed": bool(ent.Closed),
                              "color": int(ent.Color),
                              "lw": int(getattr(ent, "Lineweight", -1) or -1),
                              "elev": round(float(getattr(ent, "Elevation", 0.0) or 0.0), 3),
                              "pts": pts})
            elif name == "AcDbLine":
                lines.append({"layer": ent.Layer,
                              "a": [round(ent.StartPoint[0], 3), round(ent.StartPoint[1], 3)],
                              "b": [round(ent.EndPoint[0], 3), round(ent.EndPoint[1], 3)]})
            elif name in ("AcDbText", "AcDbMText"):
                txt = str(ent.TextString)
                ins = ent.InsertionPoint
                texts.append({"kind": name, "layer": ent.Layer, "txt": txt,
                              "pos": [round(ins[0], 3), round(ins[1], 3)],
                              "h": round(float(ent.Height), 4),
                              "style": str(getattr(ent, "StyleName", ""))})
            elif name == "AcDbHatch":
                rec = {"layer": ent.Layer, "pattern": str(ent.PatternName)}
                try:
                    bb = ent.GeometricExtents
                    rec["cx"] = round((bb.MinPoint[0] + bb.MaxPoint[0]) / 2, 3)
                    rec["cy"] = round((bb.MinPoint[1] + bb.MaxPoint[1]) / 2, 3)
                    rec["w"] = round(bb.MaxPoint[0] - bb.MinPoint[0], 3)
                    rec["h"] = round(bb.MaxPoint[1] - bb.MinPoint[1], 3)
                except Exception:
                    pass
                hatches.append(rec)
        except Exception as exc:
            print("  entity err", name, exc)

    print("elapsed %.1fs" % (time.time() - t0))
    print("counts:", dict(counts))
    if census_only:
        out.write_text(json.dumps({"layers": layers, "counts": dict(counts)},
                                  ensure_ascii=False, indent=1), encoding="utf-8")
    else:
        out.write_text(json.dumps({"dwg": str(dwg), "layers": layers,
                                   "counts": dict(counts), "polylines": polys,
                                   "lines": lines, "texts": texts, "hatches": hatches},
                                  ensure_ascii=False, indent=1), encoding="utf-8")
    print("saved", out, "size", out.stat().st_size)
    if opened:
        try:
            doc.Close(False)
        except Exception:
            pass
    pythoncom.CoUninitialize()


if __name__ == "__main__":
    main()
