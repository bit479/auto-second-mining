# -*- coding: utf-8 -*-
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
for b in d["blocks"]:
    n = sum(len(p) for p in b["parts"])
    print(f"#{b['no']} {b['grade_label']} 面积{b['area_m2']:.0f}m2 孔{b['cell_count']} "
          f"边界点数{n} parts={len(b['parts'])}")
