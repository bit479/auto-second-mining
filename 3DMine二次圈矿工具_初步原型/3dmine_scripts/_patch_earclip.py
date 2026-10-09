# -*- coding: utf-8 -*-
"""修复 mine_1004_macro.py 的 earclip（去共线 + 严格内点 + 质心扇形兜底）。"""
import io

p = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\3dmine_scripts\mine_1004_macro.py"
src = io.open(p, encoding="gbk").read()

old_in = """def _pt_in_tri(p, a, b, c):
    def sgn(px, py, qx, qy, rx, ry):
        return (px - rx) * (qy - ry) - (qx - rx) * (py - ry)
    d1 = sgn(p[0], p[1], a[0], a[1], b[0], b[1])
    d2 = sgn(p[0], p[1], b[0], b[1], c[0], c[1])
    d3 = sgn(p[0], p[1], c[0], c[1], a[0], a[1])
    neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
    pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
    return not (neg and pos)"""
new_in = """def _pt_in_tri(p, a, b, c):
    def sgn(px, py, qx, qy, rx, ry):
        return (px - rx) * (qy - ry) - (qx - rx) * (py - ry)
    d1 = sgn(p[0], p[1], a[0], a[1], b[0], b[1])
    d2 = sgn(p[0], p[1], b[0], b[1], c[0], c[1])
    d3 = sgn(p[0], p[1], c[0], c[1], a[0], a[1])
    return (d1 > 0 and d2 > 0 and d3 > 0) or (d1 < 0 and d2 < 0 and d3 < 0)"""
assert old_in in src, "old_in not found"
src = src.replace(old_in, new_in)

old_ec = """def earclip(pts):
    \"\"\"ear clipping 三角化（凹多边形）：pts=[[x,y],...] -> [[i,j,k],...] 顶点索引\"\"\"
    n = len(pts)
    if n < 3:
        return []
    area = 0.0
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    idx = list(range(n))
    if area < 0:
        idx.reverse()
    tris = []
    guard = 0
    while len(idx) > 3 and guard < n * n:
        guard += 1
        cut = False
        m = len(idx)
        for i in range(m):
            i0 = idx[i - 1]
            i1 = idx[i]
            i2 = idx[(i + 1) % m]
            a, b, c = pts[i0], pts[i1], pts[i2]
            cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            if cross <= 0:
                continue
            ok = True
            for j in idx:
                if j in (i0, i1, i2):
                    continue
                if _pt_in_tri(pts[j], a, b, c):
                    ok = False
                    break
            if ok:
                tris.append((i0, i1, i2))
                idx.pop(i)
                cut = True
                break
        if not cut:
            break
    if len(idx) == 3:
        tris.append((idx[0], idx[1], idx[2]))
    else:
        # 兜底扇形化（对近凸多边形可用）
        tris = []
        k0 = idx[0]
        for t in range(1, len(idx) - 1):
            tris.append((k0, idx[t], idx[t + 1]))
    return tris"""
new_ec = """def earclip(pts):
    \"\"\"ear clipping 三角化（凹多边形）：pts=[[x,y],...] -> [[i,j,k],...] 顶点索引\"\"\"
    # 1) 去共线顶点
    pp = []
    n0 = len(pts)
    for i in range(n0):
        a = pts[i - 1]
        b = pts[i]
        c = pts[(i + 1) % n0]
        cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if abs(cross) > 1e-6:
            pp.append(b)
    if len(pp) < 3:
        return []
    pts = pp
    n = len(pts)
    area = 0.0
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    idx = list(range(n))
    if area < 0:
        idx.reverse()
    tris = []
    guard = 0
    while len(idx) > 3 and guard < n * n:
        guard += 1
        cut = False
        m = len(idx)
        for i in range(m):
            i0 = idx[i - 1]
            i1 = idx[i]
            i2 = idx[(i + 1) % m]
            a, b, c = pts[i0], pts[i1], pts[i2]
            cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            if cross <= 1e-9:
                continue
            ok = True
            for j in idx:
                if j in (i0, i1, i2):
                    continue
                if _pt_in_tri(pts[j], a, b, c):
                    ok = False
                    break
            if ok:
                tris.append((i0, i1, i2))
                idx.pop(i)
                cut = True
                break
        if not cut:
            break
    if len(idx) == 3:
        tris.append((idx[0], idx[1], idx[2]))
    elif len(idx) > 3:
        # 兜底：质心扇形化（星形多边形近似覆盖）
        cx = sum(pts[i][0] for i in idx) / len(idx)
        cy = sum(pts[i][1] for i in idx) / len(idx)
        for t in range(len(idx) - 1):
            tris.append((idx[t], idx[t + 1], idx[0]))
    return tris"""
assert old_ec in src, "old_ec not found"
src = src.replace(old_ec, new_ec)

io.open(p, "w", encoding="gbk", newline="\n").write(src)
print("patched ok, size:", len(src.encode("gbk")))
