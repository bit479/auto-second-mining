# -*- coding: utf-8 -*-
"""把当天的矿块边界**并进综合图的一个副本**（绝不改原件）。

用法:
  python merge_to_composite.py <综合图.dwg> <本日矿块边界线.3ds> [输出.dwg] [--layer-suffix 1008]

做的事：
  ① 把综合图**复制**成 <原名>_并入<标签>.dwg；
  ② 用 AutoCAD COM 打开这个副本，把 .3ds 里每个矿块加一条闭合多段线，
     放到与品位档同名的图层上（没有该图层就新建，颜色跟人工图层一致）；
  ③ 存盘、关闭副本，打印"加了哪几块、放在哪层"。

原件始终不动；你复核副本没问题后再自己决定要不要替换原件。
"""
from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

LAYER_COLOR = {"0.500-1.000": 4, "1.000-1.500": 5,
               "1.500-3.000": 1, "3.000-999.000": 2}


def read_3ds_blocks(path: Path):
    """读自家格式的 .3ds：返回 [(label, [(x, y), ...]), ...]（x=E, y=N）。"""
    txt = Path(path).read_bytes().decode("gbk", "replace")
    blocks, cur, label = [], [], None
    for line in txt.splitlines():
        s = line.strip()
        if not s:
            continue
        f = [t.strip() for t in s.split(",")]
        # 字符串头形如 "<id>,7,0,1.00,…,Continuous,<档位名>"（id 从 1 递增，
        # 所以不能只认 f[0]=="1"）；末段是档位名
        if len(f) >= 11 and f[1] == "7" and f[0].isdigit():
            if cur:
                blocks.append((label, cur))
            cur, label = [], f[-1]
        elif f[0] == "1" and 4 <= len(f) <= 6:      # 顶点行 1,N,E,Z,
            try:
                cur.append((float(f[2]), float(f[1])))
            except Exception:
                pass
    if cur:
        blocks.append((label, cur))
    return [b for b in blocks if len(b[1]) >= 3]


def _acad(start: bool = False, timeout_s: float = 120.0):
    import pythoncom
    import win32com.client
    pythoncom.CoInitialize()
    if start:
        out = __import__("subprocess").run(
            ["tasklist", "/FI", "IMAGENAME eq acad.exe"], capture_output=True,
            text=True, errors="replace").stdout
        if "acad.exe" not in out.lower():
            for exe in (r"E:\gzRJ\CAD\AutoCAD 2023\acad.exe",
                        r"C:\Program Files\Autodesk\AutoCAD 2023\acad.exe"):
                if Path(exe).exists():
                    __import__("subprocess").Popen([exe], cwd=str(Path(exe).parent))
                    break
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        try:
            return win32com.client.Dispatch("AutoCAD.Application")
        except Exception:
            time.sleep(2)
    return None


def merge(comp_dwg: Path, tds: Path, out_dwg: Path = None, start: bool = False):
    comp_dwg, tds = Path(comp_dwg), Path(tds)
    if not comp_dwg.exists():
        return False, "找不到综合图：%s" % comp_dwg, None
    if not tds.exists():
        return False, "找不到 .3ds：%s" % tds, None
    blocks = read_3ds_blocks(tds)
    if not blocks:
        return False, "没从 .3ds 里读出矿块", None
    import re as _re
    m = _re.search(r"(\d{3,4})(?!.*\d)", tds.stem)
    tag = m.group(1) if m else (tds.stem.replace("矿块边界线", "").strip() or "new")
    out_dwg = Path(out_dwg) if out_dwg else \
        comp_dwg.with_name("%s_并入%s.dwg" % (comp_dwg.stem, tag))
    # 交给 AutoCAD COM 的路径必须是绝对的（相对路径 COM 会按 AutoCAD 的工作目录去找）
    out_dwg = out_dwg.resolve()
    comp_dwg = comp_dwg.resolve()
    shutil.copy2(comp_dwg, out_dwg)          # 只动副本
    acad = _acad(start=start)
    if acad is None:
        return False, "AutoCAD COM 未就绪（副本已复制：%s）" % out_dwg, out_dwg
    doc = None
    try:
        doc = acad.Documents.Open(str(out_dwg), False)
        time.sleep(1.5)
        have = {}
        for ly in doc.Layers:
            try:
                have[ly.Name] = True
            except Exception:
                pass
        for label, _pts in blocks:
            if label and label not in have:
                doc.Layers.Add(label)
                try:
                    doc.Layers.Item(label).Color = LAYER_COLOR.get(label, 7)
                except Exception:
                    pass
                have[label] = True
        msp = doc.ModelSpace
        added = 0
        import pythoncom
        from win32com.client import VARIANT
        for label, pts in blocks:
            flat = []
            for x, y in pts:
                flat += [float(x), float(y)]
            try:
                # COM 要的是 VARIANT 的双精度数组，直接传 list 会报"发生意外"
                arr = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, flat)
                pl = msp.AddLightWeightPolyline(arr)
                pl.Closed = True
                if label:
                    pl.Layer = label
                added += 1
            except Exception as exc:
                print("  加多段线失败 %s: %s" % (label, exc))
        doc.Save()
        msg = "并入 %d 块 -> %s" % (added, out_dwg)
        return True, msg, out_dwg
    except Exception as exc:
        return False, "并入失败：%s（副本保留在 %s）" % (exc, out_dwg), out_dwg
    finally:
        if doc is not None:
            try:
                doc.Close(True)
            except Exception:
                pass


def preview(comp_dwg: Path, blocks, out_png: Path, cache_json: Path = None):
    """出一张"并入后长什么样"的预览：综合图轮廓（灰）+ 本次并入的块（彩色）。"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun"]
        plt.rcParams["axes.unicode_minus"] = False
        from shapely.geometry import box, LineString
        import json as _json
    except Exception as exc:
        return None, "预览图跳过：%s" % exc
    cand = Path(cache_json) if cache_json else \
        Path(comp_dwg).with_name(Path(comp_dwg).stem + "_scan.json")
    xs = [p[0] for _, pts in blocks for p in pts]
    ys = [p[1] for _, pts in blocks for p in pts]
    pad = 25.0
    bb = (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)
    fig, ax = plt.subplots(figsize=(11, 11), dpi=100)
    n_draw = 0
    if cand.exists():
        try:
            data = _json.loads(cand.read_text(encoding="utf-8"))
            region = box(*bb)
            for pl in data.get("polylines", []):
                pts = pl.get("pts") or []
                if len(pts) < 2:
                    continue
                ln = LineString(pts)
                if not ln.intersects(region):
                    continue
                xs2, ys2 = ln.xy
                ax.plot(xs2, ys2, color="#9a9a9a", lw=0.7, zorder=2)
                n_draw += 1
        except Exception:
            pass
    colors = {"0.500-1.000": "#a9d6d0", "1.000-1.500": "#b4a7d6",
              "1.500-3.000": "#ffd966", "3.000-999.000": "#f4b183"}
    for label, pts in blocks:
        ax.fill([p[0] for p in pts], [p[1] for p in pts],
                color=colors.get(label, "#cccccc"), alpha=0.75, zorder=3)
        ax.plot([p[0] for p in pts] + [pts[0][0]], [p[1] for p in pts] + [pts[0][1]],
                color="#c00000", lw=1.6, zorder=4)
    ax.set_xlim(bb[0], bb[2])
    ax.set_ylim(bb[1], bb[3])
    ax.set_aspect("equal")
    ax.grid(alpha=0.2)
    ax.set_title("并入预览：彩色=本次并入的 %d 块，灰线=综合图原有" % len(blocks))
    fig.tight_layout()
    fig.savefig(str(out_png))
    plt.close(fig)
    return out_png, "预览已出（综合图原有线条 %d 条）" % n_draw


def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__)
        return
    out = None
    for a in sys.argv[3:]:
        if not a.startswith("--"):
            out = Path(a)
    ok, msg, out_dwg = merge(Path(sys.argv[1]), Path(sys.argv[2]), out,
                             start="--start" in sys.argv)
    print(("OK  " if ok else "FAIL ") + msg)
    if ok and out_dwg:
        blocks = read_3ds_blocks(Path(sys.argv[2]))
        png = Path(str(out_dwg)).with_name(Path(str(out_dwg)).stem + "_预览.png")
        r = preview(Path(sys.argv[1]), blocks, png)
        if r[0]:
            print("     ", r[1], "->", r[0])
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
