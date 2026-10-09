# -*- coding: utf-8 -*-
"""
BS-3940-1004 二次圈矿宏（3DMine 内嵌 Python 执行）
功能（对应人工二次圈矿全流程）：
  1) 炮孔点：在钻孔数据库当前工作区绘制炮孔点，desc 显示 孔号+品位
  2) 矿块圈连：每个矿块生成闭合矿界线，按品位档着色（0.5-1 青 / 1-1.5 蓝 / 1.5-3 红 / >=3 黄）
  3) 填充面：矿块以三角面填充（着色，图上直观可见矿块形态）
  4) 1m 网格：每个矿块加边长 1m 的正方形网格线（单独子层）
  5) 矿块标注：矿块质心生成标注点（矿块号 + 品位档）
  6) 数据报告：按矿块输出 面积/体积/重量/平均品位/金属量，写 txt 报告
数据来源：output/1004_macro/1004_blocks.json（由 1004 xls 自动圈连生成）
运行方式：3DMine 菜单 PyMacro(M) -> RunMacroTest
"""
import json
import os
import sys

try:
    import mine
    from mine_enum import *
    from mine import *
except Exception as _e:
    _import_err = str(_e)
else:
    _import_err = ""

LOG = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\macro_log.txt"
LOG2 = r"C:\tmp\macro_log.txt"
JSON = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\1004_blocks.json"
REPORT = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\1004_矿块数据报告.txt"


def log(msg):
    for lp in (LOG, LOG2):
        try:
            with open(lp, "a", encoding="utf-8") as f:
                f.write(str(msg) + "\n")
        except Exception:
            pass


def main():
    log("SCRIPT_STARTED from %s" % os.path.abspath(__file__))
    log("import_err=%s" % _import_err)
    try:
        database = GetActiveDbDatabase()
        log("DB_OBTAINED=%s" % str(database))
        if database is None:
            log("ERROR: 当前没有打开的数据库！请在 3DMine 中先加载 3940平台炮孔数据库1004.mdb 再运行宏")
            return
        data = json.load(open(JSON, encoding="utf-8"))
        m = data["meta"]
        z = m["bench_z"]
        h = m["bench_height_m"]
        dens = m["density_ore_t_m3"]
        log("DB=%s holes=%d blocks=%d z=%.1f" % (str(database), len(data["holes"]), len(data["blocks"]), z))

        # ---- 1. 炮孔点（孔号 + 品位） ----
        n_holes = 0
        for hd in data["holes"]:
            n_holes += 1
            pt = pyDbPoint()
            pt.setPosition(Point3d(hd["x"], hd["y"], z))
            pt.setDesc("%s  %.2f" % (hd["id"], hd["grade"]))
            pt.setLayerName("3940-1004炮孔")
            pt.setSubLayerName("炮孔品位")
            database.AddDbObject(pt, True)
        log("holes ok: %d" % n_holes)

        # ---- 2. 矿块 ----
        report_lines = []
        for b in data["blocks"]:
            pts = [[p[0], p[1]] for p in b["boundary"]]
            c = b["color"]
            no = b["no"]
            # 2a. 闭合矿界线
            poly = pyDb3DPolyline()
            lp = ListPoint3d()
            for (x, y) in pts:
                lp.push_back(Point3d(x, y, z))
            lp.push_back(Point3d(pts[0][0], pts[0][1], z))
            poly.setVertex(lp)
            poly.setColor(Point3d(c[0], c[1], c[2]))
            poly.setLayerName("3940-1004矿块")
            poly.setSubLayerName("矿块%d_%s" % (no, b["grade_label"]))
            database.AddDbObject(poly, True)
            # 2b. 填充面（json 内已用约束 Delaunay 预生成三角形）
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
                database.AddDbObject(face, True)
            # 2c. 矿块标注点（质心）
            lbl = pyDbPoint()
            lbl.setPosition(Point3d(b["centroid"][0], b["centroid"][1], z))
            lbl.setDesc("矿块%d %s" % (no, b["grade_label"]))
            lbl.setLayerName("3940-1004矿块标注")
            lbl.setSubLayerName("")
            database.AddDbObject(lbl, True)
            # 2d. 1m 网格线
            for ln in b["grid_lines"]:
                g = pyDb3DPolyline()
                gl = ListPoint3d()
                gl.push_back(Point3d(ln[0][0], ln[0][1], z))
                gl.push_back(Point3d(ln[1][0], ln[1][1], z))
                g.setVertex(gl)
                g.setLayerName("3940-1004网格")
                g.setSubLayerName("矿块%d" % no)
                database.AddDbObject(g, True)
            # 2e. 算量（3DMine 口径：台阶高 x 面积 x 密度；品位按面积加权）
            area = 0.0
            if tv and tf:
                for f in tf:
                    p0 = tv[f[0]]
                    p1 = tv[f[1]]
                    p2 = tv[f[2]]
                    area += abs((p1[0] - p0[0]) * (p2[1] - p0[1]) - (p1[1] - p0[1]) * (p2[0] - p0[0])) / 2.0
            vol = area * h
            ton = vol * dens
            gd = b["avg_grade_g_t"]
            metal = gd * ton
            report_lines.append("矿块%d | %s | 面积 %.3f m2 | 体积 %.3f m3 | 重量 %.3f t | 平均品位 %.3f g/t | 金属量 %.3f g | 炮孔 %d 个" % (
                no, b["grade_label"], area, vol, ton, gd, metal, b["cell_count"]))
            log("block %d ok: pts=%d tris=%d grid=%d" % (no, len(pts), len(tf or []), len(b["grid_lines"])))

        # ---- 3. 报告 ----
        try:
            with open(REPORT, "w", encoding="utf-8") as f:
                f.write("BS-3940-1004 二次圈矿数据报告（3DMine 宏出具）\n\n")
                f.write("\n".join(report_lines))
        except Exception as e:
            log("report write fail: %s" % e)

        Update_Layer_Manager()
        log("DONE")
    except Exception:
        import traceback
        log(traceback.format_exc())


main()
