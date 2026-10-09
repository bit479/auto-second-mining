# -*- coding: utf-8 -*-
"""更新宏：用 json 中预计算的 tri_verts/tri_faces 创建填充面。"""
import io

p = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\3dmine_scripts\mine_1004_macro.py"
src = io.open(p, encoding="gbk").read()

old = """            # 2b. 填充面（三角化）
            tris = earclip(pts)
            if tris:
                face = pyDbFace()
                vl = ListPoint3d()
                for (x, y) in pts:
                    vl.push_back(Point3d(x, y, z))
                fl = ListInt()
                for t in tris:
                    fl.push_back(t[0])
                    fl.push_back(t[1])
                    fl.push_back(t[2])
                face.setVertex(vl)
                face.setFaceList(fl)
                face.setColor(Point3d(c[0], c[1], c[2]))
                face.setLayerName("3940-1004矿块填充")
                face.setSubLayerName("矿块%d_%s" % (no, b["grade_label"]))
                database.AddDbObject(face, True)"""
new = """            # 2b. 填充面（json 中已用约束 Delaunay 预计算三角形，精确覆盖凹多边形）
            tv = b.get("tri_verts")
            tf = b.get("tri_faces")
            if tv and tf:
                face = pyDbFace()
                vl = ListPoint3d()
                for (x, y) in tv:
                    vl.push_back(Point3d(x, y, z))
                fl = ListInt()
                for f in tf:
                    fl.push_back(f[0])
                    fl.push_back(f[1])
                    fl.push_back(f[2])
                face.setVertex(vl)
                face.setFaceList(fl)
                face.setColor(Point3d(c[0], c[1], c[2]))
                face.setLayerName("3940-1004矿块填充")
                face.setSubLayerName("矿块%d_%s" % (no, b["grade_label"]))
                database.AddDbObject(face, True)"""
assert old in src, "old face block not found"
src = src.replace(old, new)
io.open(p, "w", encoding="gbk", newline="\n").write(src)
print("macro patched ok, size:", len(src.encode("gbk")))
