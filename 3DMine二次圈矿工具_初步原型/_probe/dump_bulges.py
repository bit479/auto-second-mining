# -*- coding: utf-8 -*-
"""只读检查人工 DWG 里矿界折线的凸度(bulge)，判断是否有圆弧段导致面积偏小。

用法: python dump_bulges.py <dwg>
"""
from __future__ import annotations

import sys
from pathlib import Path

import pythoncom
import win32com.client


def main() -> None:
    dwg = Path(sys.argv[1])
    pythoncom.CoInitialize()
    acad = win32com.client.GetActiveObject("AutoCAD.Application")
    doc = None
    for d in acad.Documents:
        try:
            if Path(str(d.FullName)).name.lower() == dwg.name.lower():
                doc = d
                break
        except Exception:
            continue
    if doc is None:
        doc = acad.Documents.Open(str(dwg), True)
    print("doc:", doc.Name)

    keep = ("0", "0.500-1.000", "1.000-1.500", "1.500-3.000", "3.000-999.000")
    found = 0
    for ent in doc.ModelSpace:
        try:
            if ent.ObjectName not in ("AcDbPolyline", "AcDb2dPolyline"):
                continue
            if ent.Layer not in keep:
                continue
        except Exception:
            continue
        found += 1
        coords = list(ent.Coordinates)
        n = len(coords) // 2
        bulges = []
        for i in range(n):
            try:
                bulges.append(round(float(ent.GetBulge(i)), 6))
            except Exception:
                bulges.append("n/a")
        print("layer=%s closed=%s 顶点=%d area(COM)=%s"
              % (ent.Layer, ent.Closed, n, getattr(ent, "Area", "?")))
        print("   bulges:", bulges)
        print("   pts:", [(round(coords[2 * i], 3), round(coords[2 * i + 1], 3)) for i in range(n)])
    print("命中矿界折线 %d 条" % found)
    pythoncom.CoUninitialize()


if __name__ == "__main__":
    main()
