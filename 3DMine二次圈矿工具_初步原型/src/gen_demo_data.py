# -*- coding: utf-8 -*-
"""
模拟炮粉数据库数据生成器（PoC 演示用）
----------------------------------------
按项目计划书《十二、数据标准与数据字典设计》中的 tbl_blast_hole / tbl_sample_assay
字段结构，生成一个 1220 平台的模拟爆区 BL-2026-015。

品位场为人工构造，包含：
  - 主矿体（椭圆，峰值 ~3.2 g/t）
  - 副矿体（圆形，峰值 ~2.0 g/t）
  - 主矿体内部夹石包体（低品位，用于演示"最小夹石剔除厚度"规则）
  - 废石背景（0.1~0.4 g/t 噪声）

该文件仅为演示数据，非真实矿山数据；真实数据接入后由 data_loader 直接读取生产库。
"""
from __future__ import annotations

import random
from pathlib import Path

import numpy as np
import pandas as pd

BENCH_Z = 1220.0          # 台阶高程（m）
HOLE_DEPTH = 6.0          # 设计孔深（m）
SAMPLE_LEN = 2.0          # 单样段长度（m）
HOLE_SPACING = 6.0        # 孔距（m）
CUTOFF_GT = 1.0           # 边界品位（g/t），仅用于构造矿/废标签参考

BLAST_ID = "BL-2026-015"
BENCH_ID = "1220"


def grade_field(x: float, y: float) -> float:
    """人工品位场：返回 (x, y) 处的理论品位（g/t）。"""
    g = 0.15  # 废石背景
    # 主矿体：椭圆，中心 (45030, 32120)，长轴沿 X 方向旋转 20°；
    # 半轴 26m/16m、峰值 3.6 g/t、品位线性衰减，
    # 保证 0.5-1 / 1-1.5 / 1.5-3 / ≥3 四个等级都有连续的环带
    cx1, cy1 = 45030.0, 32120.0
    dx, dy = x - cx1, y - cy1
    rot = 20.0 * np.pi / 180.0
    xr = dx * np.cos(rot) + dy * np.sin(rot)
    yr = -dx * np.sin(rot) + dy * np.cos(rot)
    e1 = (xr / 26.0) ** 2 + (yr / 16.0) ** 2
    if e1 <= 1.0:
        g = max(g, 3.6 * (1.0 - e1))   # 中心 3.6 → 边缘 0，线性衰减
    # 夹石包体：主矿体高品位核心区内的低品位透镜体（中心取孔位 (45028,32118)，
    # 半径 6.5 m、覆盖 5 个孔位，面积约 133 m²，小于"最小夹石剔除面积 200 m²"，
    # 用于演示夹石剔除/合并规则）
    d2 = np.hypot(x - 45028.0, y - 32118.0)
    if d2 <= 6.5:
        g = 0.25                       # 夹石：低品位
    # 副矿体：圆形，中心 (45058, 32152)
    d3 = np.hypot(x - 45058.0, y - 32152.0)
    if d3 <= 11.0:
        g += 2.0 * (1.0 - 0.7 * d3 / 11.0)
    # 孤立小矿体：爆区边缘小透镜体（中心取孔位 (45070,32082)，面积约 38 m²
    # < 最小可采面积 100 m²，峰值品位 1.8 g/t，用于演示"孤立小矿体剔除"规则）
    d4 = np.hypot(x - 45070.0, y - 32082.0)
    if d4 <= 3.5:
        g = max(g, 1.8 * (1.0 - 0.6 * d4 / 3.5))
    # 随机扰动，模拟化验误差
    g += random.gauss(0, 0.05)
    return max(0.0, round(g, 4))


def build_blast_holes() -> pd.DataFrame:
    """生成炮孔及化验样品数据。"""
    x_min, x_max = 44980.0, 45080.0
    y_min, y_max = 32070.0, 32170.0

    rows = []
    hole_no = 0
    xs = np.arange(x_min, x_max + 1e-6, HOLE_SPACING)
    ys = np.arange(y_min, y_max + 1e-6, HOLE_SPACING)
    for xi in xs:
        for yi in ys:
            hole_no += 1
            hole_id = f"BL2026-015-{hole_no:03d}"
            base_grade = grade_field(xi, yi)
            # 每个孔 3 段样品（垂直孔简化，分段品位略有波动）
            for seg in range(3):
                from_m = seg * SAMPLE_LEN
                to_m = from_m + SAMPLE_LEN
                seg_grade = max(0.0, base_grade + random.gauss(0, 0.04))
                rock = "ORE" if base_grade >= CUTOFF_GT else ("WASTE" if base_grade < 0.8 else "LOW_ORE")
                rows.append({
                    "Hole_ID": hole_id,
                    "Blast_ID": BLAST_ID,
                    "Bench_ID": BENCH_ID,
                    "X": round(xi, 3),
                    "Y": round(yi, 3),
                    "Z": BENCH_Z,
                    "Depth_m": HOLE_DEPTH,
                    "Azimuth": 0.0,
                    "Dip": -90.0,
                    "From_m": from_m,
                    "To_m": to_m,
                    "Length_m": SAMPLE_LEN,
                    "Au_g_t": round(seg_grade, 4),
                    "Rock_Type": rock,
                    "QC_Type": 0,
                })
    return pd.DataFrame(rows)


def main() -> None:
    out_dir = Path(__file__).resolve().parent.parent / "sample_data"
    out_dir.mkdir(parents=True, exist_ok=True)
    df = build_blast_holes()
    out_csv = out_dir / "blast_BL2026-015.csv"
    # utf-8-sig：便于 Windows Excel 直接打开
    df.to_csv(out_csv, index=False, encoding="utf-8-sig")
    # 汇总信息
    hole_count = df["Hole_ID"].nunique()
    sample_count = len(df)
    print(f"输出文件：{out_csv}")
    print(f"炮孔数：{hole_count}，样品段数：{sample_count}")
    print(f"坐标范围：X[{df['X'].min():.1f}, {df['X'].max():.1f}]  Y[{df['Y'].min():.1f}, {df['Y'].max():.1f}]")
    print(f"品位范围：{df['Au_g_t'].min():.3f} ~ {df['Au_g_t'].max():.3f} g/t")
    print(f"品位>=1.0 g/t 的孔占比：{(df.groupby('Hole_ID')['Au_g_t'].mean() >= CUTOFF_GT).mean():.1%}")


if __name__ == "__main__":
    main()
