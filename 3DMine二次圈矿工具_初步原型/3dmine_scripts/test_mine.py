# -*- coding: cp936 -*-
import mine
from mine_enum import *
from mine import *

LOG = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\3dmine_scripts\test_mine_log.txt"
def wlog(msg):
    try:
        with open(LOG, "a") as f:
            f.write(msg + "\n")
    except Exception:
        pass

try:
    wlog("START")
    database = GetActiveDbDatabase()
    wlog("DB_OK: " + repr(database))
    drill = database.getDrillHoleManage()
    wlog("DRILL_OK: " + repr(drill))
    block = database.getBlockModel()
    wlog("BLOCK_OK: " + repr(block))
    import numpy as np
    face = pyDbFace()
    verts = np.array([[0,0,0],[10,0,0],[0,10,0],[10,10,0]], dtype=np.float64)
    tris = np.array([[0,1,2],[1,3,2]], dtype=np.int32)
    face.setNpData(verts, tris)
    face.setColor(Point3d(255,0,0))
    database.AddDbObject(face, True)
    database.Update()
    Update_Layer_Manager()
    wlog("DONE")
except Exception as e:
    import traceback
    wlog("FAIL: " + repr(e))
    wlog(traceback.format_exc())