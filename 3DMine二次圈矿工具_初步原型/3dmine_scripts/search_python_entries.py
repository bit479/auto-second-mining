# -*- coding: utf-8 -*-
import os, sys

root = r"E:\gzRJ\3Dmine\2022"
hits = []
for dirpath, dirnames, filenames in os.walk(root):
    # skip huge binary dirs
    if "nt_x64" in dirpath or "debug" in dirpath.lower():
        continue
    for fn in filenames:
        if not fn.lower().endswith((".xml", ".py", ".txt", ".ini", ".cfg")):
            continue
        p = os.path.join(dirpath, fn)
        try:
            s = open(p, "rb").read()
        except Exception:
            continue
        if b"pytool" in s or b"Macro Path" in s or b"RunPython" in s or b"PythonRun" in s:
            hits.append((p, s.count(b"Macro Path"), s.count(b"pytool")))
for p, mc, pt in hits:
    print(p, "MacroPath:", mc, "pytool:", pt, flush=True)
print("total", len(hits), flush=True)
