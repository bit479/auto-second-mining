# -*- coding: utf-8 -*-
"""一次性小工具：把 strip.py 里可能碰到非法几何的 unary_union 换成 _safe_union。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUBS = [
    ("poly = unary_union(list(poly.geoms))",
     "poly = _safe_union(list(poly.geoms))"),
    ("poly = unary_union([poly, LineString([near, tip]).buffer(",
     "poly = _safe_union([poly, LineString([near, tip]).buffer("),
    ("poly = unary_union([poly, LineString([tuple(p) for p in north]).buffer(",
     "poly = _safe_union([poly, LineString([tuple(p) for p in north]).buffer("),
    ("poly = unary_union([poly, LineString([tuple(p) for p in south]).buffer(",
     "poly = _safe_union([poly, LineString([tuple(p) for p in south]).buffer("),
    ('poly = unary_union([poly, sh.buffer(extrude, join_style="mitre")]).buffer(0)',
     'poly = _safe_union([poly, sh.buffer(extrude, join_style="mitre")]).buffer(0)'),
    ("region = unary_union([cells[h.hid] for h in grp])",
     "region = _safe_union([cells[h.hid] for h in grp])"),
    ("poly = unary_union(parts).buffer(0)", "poly = _safe_union(parts).buffer(0)"),
]


def main() -> None:
    p = ROOT / "core" / "strip.py"
    t = p.read_text(encoding="utf-8")
    n = 0
    for a, b in SUBS:
        if a in t:
            t = t.replace(a, b)
            n += 1
        else:
            print("未找到:", a[:56])
    p.write_text(t, encoding="utf-8")
    print("替换", n, "处")


if __name__ == "__main__":
    main()
