# -*- coding: utf-8 -*-
"""抽查成品 DWG：DWG→DXF（accoreconsole，无界面）后看关键实体。

用法: python dwg_check.py <a.dwg>
关注：报告表是不是矢量 TEXT、有没有外部 IMAGE 参照、矿块轮廓几条。
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))
from dxf2dwg import _find_accore      # noqa: E402


def main():
    src = Path(sys.argv[1])
    acc = _find_accore()
    if acc is None:
        print("没找到 accoreconsole.exe")
        return 2
    with tempfile.TemporaryDirectory(prefix="dwg_check_") as td:
        td = Path(td)
        a = td / "a.dwg"
        out = td / "a.dxf"
        shutil.copy2(src, a)
        scr = td / "e.scr"
        scr.write_text("_DXFOUT\n%s\n16\n_QUIT\n" % out, encoding="ascii")
        subprocess.run([str(acc), "/i", str(a), "/s", str(scr)],
                       capture_output=True, text=True, timeout=600, errors="replace")
        if not out.exists():
            print("DXFOUT 失败")
            return 2
        import ezdxf
        msp = ezdxf.readfile(str(out)).modelspace()
        texts = [e for e in msp if e.dxftype() == "TEXT"]
        mtexts = [e for e in msp if e.dxftype() == "MTEXT"]
        imgs = [e for e in msp if e.dxftype() == "IMAGE"]
        heads = [t.dxf.text for t in texts if t.dxf.text in
                 ("类型", "体号", "体积", "重量", "平均品位(Au)", "金属量（百克）")]
        stat = [t.dxf.text for t in texts if "炮孔品位统计" in str(t.dxf.text)]
        blocks = [e for e in msp if e.dxftype() == "LWPOLYLINE"
                  and e.dxf.layer in ("0.500-1.000", "1.000-1.500",
                                      "1.500-3.000", "3.000-999.000")]
        labs = [str(e.text) for e in mtexts if str(e.text).endswith("号矿块")]
        print("DWG:", src)
        print("  报告表表头:", heads)
        print("  品位统计:", stat)
        print("  IMAGE 参照:", len(imgs))
        print("  矿块轮廓:", len(blocks), "个；矿块号:", labs)
        ok = len(heads) == 6 and bool(stat) and not imgs and len(blocks) == len(labs)
        print("  结论:", "通过" if ok else "不通过")
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
