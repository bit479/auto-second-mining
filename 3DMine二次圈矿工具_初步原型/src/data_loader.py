# -*- coding: utf-8 -*-
"""
data_loader：炮粉数据库读取与预处理
-------------------------------------
对应项目计划书 4.1 节（炮粉数据库对接与数据处理）：
  - 读取炮孔/化验数据（PoC 阶段从 CSV 读取，接口与数据库读取一致）
  - 数据质量校验（坐标范围、样长、品位非负等）
  - 特高品位切割（Top-cutting）
  - 台阶平面品位合成（按孔长度加权平均，生成台阶平面代表性品位点）
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

# 默认数据质量规则（可配置）
DEFAULT_RULES = {
    "x_range": (44000.0, 46000.0),     # 矿区登记坐标范围（示例）
    "y_range": (31000.0, 33000.0),
    "min_sample_len": 0.3,             # 最小样长（m）
    "grade_upper_limit": 1000.0,       # 品位理论上限（g/t）
    "max_coord_jump": 50.0,            # 孔内相邻样段中心坐标跳变上限（m）
}


def load_blast_data(csv_path: str | Path) -> pd.DataFrame:
    """读取炮孔化验 CSV（或未来改为 SQL/中间库视图读取）。"""
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    required = ["Hole_ID", "X", "Y", "Z", "From_m", "To_m", "Au_g_t"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"数据缺少必需字段：{missing}")
    return df


def run_quality_checks(df: pd.DataFrame, rules: dict | None = None) -> pd.DataFrame:
    """执行数据质量校验，返回带 Qc_Flag / Qc_Message 的结果表。

    按计划书 12.7 数据质量校验规则（PoC 实现核心项）：
      坐标范围、样长、To>From、品位非负/上限、QC 质控样排除。
    """
    rules = rules or DEFAULT_RULES
    out = df.copy()
    msgs = []

    def mark(cond, msg):
        msgs.append(np.where(cond, msg, ""))

    xr, yr = rules["x_range"], rules["y_range"]
    mark(~out["X"].between(*xr) | ~out["Y"].between(*yr), "坐标超矿区范围")
    mark(out["From_m"] >= out["To_m"], "样段起止倒置")
    mark(out["To_m"] - out["From_m"] < rules["min_sample_len"], "样长小于最小样长")
    mark(out["Au_g_t"] < 0, "品位为负")
    mark(out["Au_g_t"] > rules["grade_upper_limit"], "品位超理论上限")
    if "QC_Type" in out.columns:
        mark(out["QC_Type"].astype(int) != 0, "质控样（不参与圈定）")

    out["Qc_Flag"] = (np.sum(np.vstack(msgs).astype(bool), axis=0) > 0) if msgs else False
    if msgs:
        msg_matrix = np.vstack(msgs)
        out["Qc_Message"] = ["|".join(m for m in row if m) for row in msg_matrix.T]
    else:
        out["Qc_Message"] = ""

    n_bad = int(out["Qc_Flag"].sum())
    if n_bad:
        print(f"[质量校验] 发现 {n_bad} 条异常记录，已标记（异常记录不参与圈定）。")
    return out


def top_cut(series: pd.Series, percentile: float = 98.0) -> tuple[pd.Series, float]:
    """特高品位切割（Top-cutting）：高于阈值者替换为阈值。

    阈值默认取历史品位 P98（计划书 14.1）。
    返回 (切割后序列, 切割阈值)。
    """
    values = series.to_numpy(dtype=float)
    threshold = float(np.percentile(values, percentile))
    cut_series = series.clip(upper=threshold)
    n_cut = int((series > threshold).sum())
    if n_cut:
        print(f"[特高品位切割] 阈值={threshold:.3f} g/t，切割 {n_cut} 条记录。")
    return cut_series, threshold


def composite_to_hole(df: pd.DataFrame) -> pd.DataFrame:
    """台阶平面品位合成：按孔长度加权平均，得到每孔一个代表性品位点。

    仅使用通过质量校验的普通样品（QC_Type=0 / Qc_Flag=False）。
    返回列：Hole_ID, Blast_ID, Bench_ID, X, Y, Z, Grade, Samples_Used。
    """
    data = df[~df["Qc_Flag"]].copy()
    if "QC_Type" in data.columns:
        data = data[data["QC_Type"].astype(int) == 0]
    data = data[data["Length_m"] > 0]

    def wavg(g):
        w = g["Length_m"].to_numpy(dtype=float)
        v = g["Au_g_t"].to_numpy(dtype=float)
        return float(np.sum(v * w) / np.sum(w))

    grouped = data.groupby(["Hole_ID", "Blast_ID", "Bench_ID", "X", "Y", "Z"], as_index=False)
    comp = grouped.apply(
        lambda g: pd.Series({
            "Grade": round(wavg(g), 4),
            "Samples_Used": int(len(g)),
        }),
        include_groups=False,
    ).reset_index(drop=True)
    return comp


def prepare_hole_points(csv_path: str | Path, cutoff_top_pct: float | None = 98.0) -> tuple[pd.DataFrame, dict]:
    """一站式预处理：读取 → 校验 → 特高切割（可关闭）→ 合成台阶品位点。

    cutoff_top_pct=None 时不做特高品位切割（Voronoi 分级圈矿用原始品位，
    避免切割阈值切断高品位等级）。
    """
    raw = load_blast_data(csv_path)
    checked = run_quality_checks(raw)
    if cutoff_top_pct is None:
        checked["Au_g_t_cut"] = checked["Au_g_t"]
        top_val = float(checked["Au_g_t"].max())
    else:
        checked["Au_g_t_cut"], top_val = top_cut(checked["Au_g_t"], cutoff_top_pct)
    checked["Au_g_t"] = checked["Au_g_t_cut"]
    comp = composite_to_hole(checked)
    meta = {
        "total_records": int(len(raw)),
        "quality_failed": int(checked["Qc_Flag"].sum()),
        "qc_samples_excluded": int((checked["QC_Type"].astype(int) != 0).sum())
        if "QC_Type" in checked.columns else 0,
        "top_cut_threshold": round(top_val, 4),
        "usable_holes": int(len(comp)),
    }
    return comp, meta
