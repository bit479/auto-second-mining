# -*- coding: utf-8 -*-
"""
二次圈矿全流程一键脚本（可再现）
=================================
输入：一个 3DMine 格式的炮孔数据库 Excel（含 定位表 / 测斜表 / blast 品位表）
输出（3 份成果）：
  1) 2010 格式 DWG 成果图（炮孔十字+完整工程号+品位大字分级着色、方格中心品位网格、
     彩色矿块边界、矿块号引出线、报告图片）
  2) 炮孔数据报告（xlsx，DWG 内以图片形式插入报告 PNG）
  3) 矿块边界线文件（.3ds，3DMine_2009 文本格式，可导入 3DMine）

用法：
  python run_1004_pipeline.py [炮孔数据库Excel路径]
  不传参数时使用默认 1004 数据。

执行三步（均为独立可复用脚本）：
  Step1  _macro_prep_1004_v61.py  Excel -> 圈矿算量 blocks.json（Voronoi 分级 + 矿块合并 + 1m网格 + 品位/体积/重量/金属量）
  Step2  _make_1004_dwg_v4.py     blocks.json -> DXF 成果图 + 报告 PNG + .3ds 边界线
  Step3  _conv_v3.py              DXF -> DWG 2010 (AC1024)，调用本机 AutoCAD COM

换数据库时只需修改三个脚本顶部的 XLS / 输出路径变量。
"""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型")
OUT = ROOT / "sample_data" / "output"
MACRO = OUT / "1004_macro"

DEFAULT_XLS = r"D:\WK\N CRT\北部山头3940平台2026\7、单日数据\北部山头3940平台-1004\1、3940平台 炮孔数据库1004.xls"

STEPS = [
    ("Step1 圈矿算量 (Excel -> blocks.json)", ROOT / "sample_data" / "output" / "_macro_prep_1004_v61.py", None),
    ("Step2 生成 DXF + 报告PNG + .3ds", ROOT / "sample_data" / "output" / "_make_1004_dwg_v5.py", None),
    ("Step3 AutoCAD 转 DWG 2010", ROOT / "3dmine_scripts" / "_conv_v4h.py", None),
]


def main():
    xls = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_XLS
    print(f"炮孔数据库: {xls}")
    if not Path(xls).exists():
        print(f"ERROR: 文件不存在 -> {xls}")
        sys.exit(1)
    for title, script, _ in STEPS:
        print("=" * 60)
        print(title, "->", script.name)
        print("=" * 60)
        subprocess.run([sys.executable, "-X", "utf8", str(script)], check=True)
    print("\n全部完成！3 份成果：")
    print("  1) DWG 2010  :", OUT / "3940平台 1004二次圈矿矿块图_3块版_2010.dwg")
    print("  2) 数据报告  : xlsx（sample_data/output/3940平台 1004炮孔数据报告.xlsx）+ 报告PNG（", MACRO / "1004炮孔数据报告_v5.png", "）")
    print("  3) 矿块边界线:", MACRO / "3940平台 1004矿块边界线.3ds")


if __name__ == "__main__":
    main()
