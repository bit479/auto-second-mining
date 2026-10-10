# -*- coding: utf-8 -*-
"""二次圈矿 · 计算核心（口径已按 3DMine 实测标定）

口径（在 1008 三块上逐块精确复现）：
    每孔 gradeLenght = round(孔深)                    # 取整米
    单元体积  = 单元面积 × 该孔 gradeLenght
    矿块体积  = Σ 单元体积
    矿块重量  = 矿块体积 × 容重
    矿块品位  = Σ(gradeLenght × 孔品位) / Σ(gradeLenght)   # 孔品位取图上 2 位小数
    金属量(百克) = 重量 × 品位 / 100

单元几何来源：3DMine「露天 → 岩粉数据库 → 爆区voronoi图」导出的选择集
（.3ds 带 ID号/体积/重量/品位/金属量，.3dm 带 gradeLenght/holepos 与面顶点）。

矿块划分规则：矿孔按品位档（左闭右开）分类；同档且相邻（单元相接）的孔并成一块。
"""
from __future__ import annotations

import re
import struct
from dataclasses import dataclass, field
from pathlib import Path

from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

# ---- 品位档（左闭右开）----
LEVELS = [
    ("L4", 3.0, float("inf"), "3.000-999.000"),
    ("L3", 1.5, 3.0, "1.500-3.000"),
    ("L2", 1.0, 1.5, "1.000-1.500"),
    ("L1", 0.5, 1.0, "0.500-1.000"),
]


def level_of(grade: float):
    for lid, lo, hi, label in LEVELS:
        if lo <= grade < hi:
            return lid, label
    return None, None            # <0.5 废孔


@dataclass
class Hole:
    hid: str
    x: float
    y: float
    z: float
    depth: float
    grade: float
    short: str = ""

    @property
    def grade_lenght(self) -> float:
        return float(int(round(self.depth)))

    @property
    def grade_disp(self) -> float:
        return round(self.grade, 2)


@dataclass
class Cell:
    """一个炮孔的 Voronoi 单元。"""
    hid: str
    hole: Hole
    polygon: Polygon = None
    area_m2: float = 0.0


@dataclass
class Block:
    no: int = 0
    level_id: str = ""
    label: str = ""
    holes: list = field(default_factory=list)     # list[Hole]
    cells: list = field(default_factory=list)     # list[Cell]
    area_m2: float = 0.0
    volume_m3: float = 0.0
    tonnage_t: float = 0.0
    grade: float = 0.0
    metal_hg: float = 0.0        # 金属量（百克）
    polygon: Polygon = None

    def compute(self, density: float) -> None:
        self.area_m2 = sum(c.area_m2 for c in self.cells)
        self.volume_m3 = sum(c.area_m2 * c.hole.grade_lenght for c in self.cells)
        self.tonnage_t = self.volume_m3 * density
        wsum = sum(h.grade_lenght for h in self.holes)
        self.grade = (sum(h.grade_lenght * h.grade_disp for h in self.holes) / wsum
                      if wsum else 0.0)
        self.metal_hg = self.tonnage_t * self.grade / 100.0
        self.polygon = unary_union([c.polygon for c in self.cells]) if self.cells else None


# ------------------------------------------------------------------ 读 3DMine 导出
ATTR = re.compile(r"Au,([\d.]+),gradeLenght,([\d.]+),holepos,([\d.]+) ([\d.]+) ([\d.]+)")


def read_3dm(path: Path):
    """读 3DMine 二进制 .3dm，返回 [(holepos_x, holepos_y, au, gradeLenght, polygon), ...]"""
    data = Path(path).read_bytes()
    idx = [m.start() for m in re.finditer(b"AcDbFace", data)]
    txt = data.decode("latin-1")
    attrs = [(m.start(), m.group(1), m.group(2), m.group(3), m.group(4))
             for m in ATTR.finditer(txt)]
    out = []
    for k, start in enumerate(idx):
        end = idx[k + 1] if k + 1 < len(idx) else len(data)
        blob = data[start:end]
        a = [x for x in attrs if start <= x[0] < end]
        if not a:
            continue
        _, au, lenght, hx, hy = a[0]
        pts = _face_polygon(blob)
        if pts is None:
            continue
        out.append((float(hx), float(hy), float(au), float(lenght),
                    Polygon(pts).buffer(0)))
    return out


def _face_polygon(blob: bytes):
    vals = []
    seen = set()
    for off in range(len(blob) - 8):
        v = struct.unpack_from("<d", blob, off)[0]
        if not any(lo <= v <= hi for lo, hi in
                   ((469000, 471000), (4349000, 4351000), (3900, 3960))):
            continue
        key = round(v, 6)
        if key in seen:
            continue
        seen.add(key)
        vals.append((off, v))
    vals.sort()
    pts = []
    for i, (_, v) in enumerate(vals):
        if 469000 <= v <= 471000 and i + 1 < len(vals):
            n = vals[i + 1][1]
            if 4349000 <= n <= 4351000 and abs(vals[i + 1][0] - vals[i][0]) <= 9:
                pts.append((v, n))
    return pts if len(pts) >= 3 else None


def read_3ds(path: Path):
    """读 .3ds，返回 [(holepos_x, holepos_y, au, None, polygon), ...]（.3ds 无 gradeLenght）"""
    txt = Path(path).read_text(encoding="gbk", errors="replace").splitlines()
    name_by_id = {}
    objs = []
    cur = None
    for ln in txt:
        s = ln.strip()
        if not s or s.startswith("file_version") or "3DMine String File" in s:
            continue
        p = [t.strip() for t in s.split(",")]
        if len(p) >= 11 and p[0].isdigit() and p[1] == "7":
            name_by_id[int(p[0])] = p[10]
            continue
        if p[0] == "0" and len(p) >= 4 and p[1].startswith("0.000"):
            if cur and cur["pts"]:
                objs.append(cur)
            cur = None
            continue
        if s.startswith("0,0,0,0,0,0,0,0"):
            continue
        if cur is None:
            cur = {"id": int(p[0]) if p[0].isdigit() else -1, "pts": [], "attr": p[4] if len(p) > 4 else ""}
        try:
            cur["pts"].append((float(p[2]), float(p[1])))
        except Exception:
            pass
    if cur and cur["pts"]:
        objs.append(cur)
    out = []
    for o in objs:
        o["name"] = name_by_id.get(o["id"], "")
        if o["id"] not in (1, 2, 3, 4, 5, 6) or len(o["pts"]) < 3:
            continue
        attr = o.get("attr", "")
        m = re.match(r"ID.*?:(\d+),([\d.]+),([\d.]+),([\d.]+),([\d.]+)", attr)
        au = float(m.group(5)) if m else None
        pts = o["pts"]
        if pts[0] != pts[-1]:
            pts = pts + [pts[0]]
        out.append((None, None, au, None, Polygon(pts).buffer(0)))
    return out


def load_holes_xls(path: Path):
    import xlrd
    wb = xlrd.open_workbook(str(path))
    loc, bl = wb.sheet_by_name("定位表"), wb.sheet_by_name("pit_blast")
    holes = {}
    for r in range(1, loc.nrows):
        hid = str(loc.cell_value(r, 0)).strip()
        holes[hid] = Hole(hid=hid, short=hid.split("-")[-1],
                          x=loc.cell_value(r, 1), y=loc.cell_value(r, 2),
                          z=loc.cell_value(r, 3), depth=loc.cell_value(r, 5),
                          grade=0.0)
    for r in range(1, bl.nrows):
        hid = str(bl.cell_value(r, 0)).strip()
        if hid in holes:
            holes[hid].grade = float(bl.cell_value(r, 3))
    return holes


def attach_cells(holes, faces):
    """把 3DMine 面按 holepos 最近匹配到孔上，得到 Cell 列表。"""
    cells = []
    for hx, hy, au, lenght, poly in faces:
        if hx is None:
            continue
        best, bd = None, 1e18
        for h in holes.values():
            d = (h.x - hx) ** 2 + (h.y - hy) ** 2
            if d < bd:
                bd, best = d, h
        if best is None:
            continue
        cells.append(Cell(hid=best.hid, hole=best, polygon=poly, area_m2=poly.area))
    return cells


def build_blocks(cells, min_area_m2: float = 0.0):
    """同档且相接的单元并成矿块；体号按 高档在前 全局连续。"""
    ore = [c for c in cells if c.hole.grade >= 0.5]
    by_level = {}
    for c in ore:
        lid, _ = level_of(c.hole.grade)
        by_level.setdefault(lid, []).append(c)

    blocks = []
    for lid, _, _, _ in LEVELS:
        todo = list(by_level.get(lid, []))
        used = [False] * len(todo)
        for i in range(len(todo)):
            if used[i]:
                continue
            group = [todo[i]]
            used[i] = True
            changed = True
            while changed:
                changed = False
                for j in range(len(todo)):
                    if used[j]:
                        continue
                    if any(todo[j].polygon.distance(g.polygon) < 1e-6 for g in group):
                        group.append(todo[j])
                        used[j] = True
                        changed = True
            blocks.append((lid, group))

    out = []
    for lid, group in blocks:
        if sum(c.area_m2 for c in group) < min_area_m2:
            continue
        _, label = level_of(group[0].hole.grade)
        b = Block(level_id=lid, label=label, cells=group,
                  holes=[c.hole for c in group])
        out.append(b)
    for i, b in enumerate(out, 1):
        b.no = i
    return out
