# -*- coding: utf-8 -*-
"""解析 3DMine 字符串文件(.3ds)，列出每条字符串的名称、点数、类型与几何摘要。

用法: python parse_3ds.py <file.3ds> [out.json]
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from shapely.geometry import LineString, Polygon


def parse(path: Path):
    lines = path.read_text(encoding="gbk", errors="replace").splitlines()
    names: dict[int, str] = {}
    objs = []
    cur = None
    for ln in lines:
        s = ln.strip()
        if not s or s.startswith("file_version") or "3DMine String File" in s:
            continue
        parts = [p.strip() for p in s.split(",")]
        if len(parts) >= 11 and parts[0].isdigit() and parts[1] == "7":
            names[int(parts[0])] = parts[10]
            continue
        if parts[0] == "0" and len(parts) >= 4 and parts[1].startswith("0.000"):
            if cur is not None and cur["pts"]:
                objs.append(cur)
            cur = None
            continue
        if parts[0] == "0" and s.startswith("0,0,0,0,0,0,0,0"):
            continue
        if cur is None:
            cur = {"id": int(parts[0]) if parts[0].isdigit() else -1, "pts": []}
        try:
            cur["pts"].append([float(parts[2]), float(parts[1]), float(parts[3])])
        except Exception:
            pass
    if cur is not None and cur["pts"]:
        objs.append(cur)
    for o in objs:
        o["name"] = names.get(o["id"], "?")
    return objs


def main() -> None:
    src = Path(sys.argv[1])
    strings = parse(src)
    print("实体对象条数 =", len(strings))
    print("名称分布 =", dict(Counter(s["name"] for s in strings)))
    print()
    print("%-4s %-14s %-6s %-12s %-6s %s" %
          ("id", "name", "pts", "面积m2", "闭合", "bbox"))
    for s in sorted(strings, key=lambda x: (x["id"], -len(x["pts"]))):
        pts = s["pts"]
        area = closed = "-"
        bb = ""
        if len(pts) >= 3:
            xy = [(p[0], p[1]) for p in pts]
            if abs(xy[0][0] - xy[-1][0]) < 1e-6 and abs(xy[0][1] - xy[-1][1]) < 1e-6:
                poly = Polygon(xy).buffer(0)
                area = "%.4f" % poly.area
                closed = "Y"
        if pts:
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            bb = "(%.2f,%.2f)-(%.2f,%.2f) Z %.2f~%.2f" % (
                min(xs), min(ys), max(xs), max(ys),
                min(p[2] for p in pts), max(p[2] for p in pts))
        print("%-4s %-14s %-6d %-12s %-6s %s" %
              (s["id"], s["name"], len(pts), area, closed, bb))
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(json.dumps(strings, ensure_ascii=False, indent=1),
                                     encoding="utf-8")
        print("\nsaved ->", sys.argv[2])


if __name__ == "__main__":
    main()
