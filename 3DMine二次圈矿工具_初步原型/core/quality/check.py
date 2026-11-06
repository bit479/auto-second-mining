# -*- coding: utf-8 -*-
"""数据质量检查（T02）。

对 `data.readers.read_holes()` 的结果做**只读**校验，输出结构化 Issue 列表。
不修改源文件、不写回任何数据、不改变生产算量口径。

判定规则里的阈值都集中在 `CHECK_CONFIG`，凡标「待确认」的都应由地质/生产负责人拍板
（见项目计划书「待确认事项」）。
"""
from __future__ import annotations

import math

from data import models

# 待确认阈值（默认值是保守占位，不代表已批准）
CHECK_CONFIG = {
    "min_hole_gap_m": 1.0,        # 两孔距离 < 此值视为「近重复孔位」—— 待确认
    "high_grade_limit": 30.0,     # Au 高于此值告警（g/t）—— 待确认
    "max_interval_count": 1,      # 同一工程号化验段数 > 此值告警（多段汇总规则待确认）
    "outlier_enable": False,      # 空间离群检测开关 —— 待确认后启用
    "outlier_k": 3,               # k 近邻距离
    "outlier_factor": 5.0,        # kNN 距离 > factor × 中位数 视为离群 —— 待确认
}


def check(ds: models.Dataset, cfg: dict | None = None) -> list:
    """返回 Issue 列表（含读取阶段 issues 的引用 + 业务校验）。"""
    cfg = dict(CHECK_CONFIG, **(cfg or {}))
    issues = list(ds.issues)

    loc = ds.loc_by_hid()
    ints = ds.intervals_by_hid()

    # 1) 定位表重复工程号（会静默覆盖 → 阻断）
    seen = {}
    for h in ds.loc_rows:
        if not h.hid:
            continue
        if h.hid in seen:
            issues.append(models.Issue(
                "dup_hid", models.SEV_ERROR,
                "工程号 %s 在定位表里出现多次（第 %d 行与第 %d 行），会互相覆盖"
                % (h.hid, seen[h.hid], h.row),
                "定位表/%s" % h.hid,
                "保留唯一记录，并核对哪一条是对的"))
        else:
            seen[h.hid] = h.row

    # 2) 缺失坐标 / 缺失孔深（读取阶段已标 non_numeric，这里补「缺失」语义）
    for h in ds.loc_rows:
        if not h.hid:
            continue
        if h.x is None or h.y is None:
            issues.append(models.Issue("missing_coord", models.SEV_ERROR,
                                       "工程号 %s 缺坐标（E/N）" % h.hid,
                                       "定位表/行%d/%s" % (h.row, h.hid)))
        if h.depth is None or h.depth <= 0:
            issues.append(models.Issue("bad_depth", models.SEV_ERROR,
                                       "工程号 %s 孔深缺失或 ≤0（算量 gradeLenght 会变成 0）" % h.hid,
                                       "定位表/行%d/%s" % (h.row, h.hid)))

    # 3) 近重复孔位
    _near_dup(issues, ds.loc_rows, cfg["min_hole_gap_m"])

    # 4) 缺失品位（定位表有、pit_blast 无）—— 必须与「真实低品位」区分
    blast_hids = set(ints.keys())
    for hid in loc:
        if hid not in blast_hids:
            issues.append(models.Issue(
                "missing_grade", models.SEV_ERROR,
                "工程号 %s 在 pit_blast 里没有化验记录 —— 是「缺失品位」，不是低品位"
                % hid, "定位表/%s" % hid,
                "补化验，或明确按废孔/缺失处理（口径待确认）"))

    # 5) 多余工程号（pit_blast 有、定位表无）
    for hid in blast_hids:
        if hid not in loc:
            issues.append(models.Issue("orphan_interval", models.SEV_WARNING,
                                       "工程号 %s 只在 pit_blast 里有化验、定位表里没有" % hid,
                                       "pit_blast/%s" % hid))

    # 6) 负品位 / 异常高品位
    for s in ds.intervals:
        if s.grade is None:
            issues.append(models.Issue("missing_grade_value", models.SEV_WARNING,
                                       "工程号 %s 的 Au 这一格是空的" % s.hid,
                                       "pit_blast/行%d/%s" % (s.row, s.hid)))
        elif s.grade < 0:
            issues.append(models.Issue("negative_grade", models.SEV_ERROR,
                                       "工程号 %s 的 Au 是负数（%.3f）" % (s.hid, s.grade),
                                       "pit_blast/行%d/%s" % (s.row, s.hid)))
        elif s.grade > cfg["high_grade_limit"]:
            issues.append(models.Issue("high_grade", models.SEV_WARNING,
                                       "工程号 %s 的 Au=%.3f 超过告警阈值 %.1f"
                                       % (s.hid, s.grade, cfg["high_grade_limit"]),
                                       "pit_blast/行%d/%s" % (s.row, s.hid),
                                       "阈值待确认；可能为特高品位，需人工复核"))

    # 7) 多段化验（汇总规则待确认）
    for hid, segs in ints.items():
        if len(segs) > cfg["max_interval_count"]:
            issues.append(models.Issue(
                "multi_interval", models.SEV_WARNING,
                "工程号 %s 有 %d 段化验（从/至 区间），当前按「最后一段」取品位 —— 汇总口径待确认"
                % (hid, len(segs)), "pit_blast/%s" % hid,
                "段：%s" % "；".join("从%s 至%s Au=%s"
                                    % (s.frm if s.frm is not None else "?",
                                       s.to if s.to is not None else "?",
                                       s.grade if s.grade is not None else "缺失")
                                    for s in segs)))

    # 7.5) 化验区间校验（T02.1）：逆序 / 与孔深一致性
    for s in ds.intervals:
        if s.frm is not None and s.to is not None and s.frm > s.to:
            issues.append(models.Issue(
                "interval_reversed", models.SEV_ERROR,
                "工程号 %s 的化验区间「从=%.3f」大于「至=%.3f」（逆序）" % (s.hid, s.frm, s.to),
                "pit_blast/行%d/%s" % (s.row, s.hid),
                "核对「从/至」是否写反；不自动改写原始记录"))
        rec = loc.get(s.hid)
        if rec is not None and rec.depth is not None and s.to is not None \
                and s.to > rec.depth + 1e-6:
            issues.append(models.Issue(
                "interval_exceeds_depth", models.SEV_WARNING,
                "工程号 %s 的化验区间「至=%.3f」大于定位表最大孔深 %.3f"
                % (s.hid, s.to, rec.depth),
                "pit_blast/行%d/%s" % (s.row, s.hid),
                "区间与孔深不一致，需核对；不自动截断"))

    # 8) 空间离群（默认关，待确认）
    if cfg["outlier_enable"]:
        _spatial_outlier(issues, ds.loc_rows, cfg)

    return issues


def _near_dup(issues, rows, gap_m: float) -> None:
    """两孔坐标距离 < gap_m 视为近重复。"""
    pts = [(h.hid, h.x, h.y, h.row) for h in rows if h.x is not None and h.y is not None]
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            a, b = pts[i], pts[j]
            d = math.hypot(a[1] - b[1], a[2] - b[2])
            if d < gap_m:
                issues.append(models.Issue(
                    "near_dup_coord", models.SEV_WARNING,
                    "工程号 %s 与 %s 坐标距离 %.2f m（< %.1f m），疑似重复孔位"
                    % (a[0], b[0], d, gap_m),
                    "定位表/行%d 与 行%d" % (a[3], b[3]),
                    "阈值待确认；确认是否为重复孔"))


def _spatial_outlier(issues, rows, cfg) -> None:
    """k 近邻距离显著偏大的孔 → 空间离群提示。"""
    k = int(cfg["outlier_k"])
    pts = [(h.hid, h.x, h.y) for h in rows if h.x is not None and h.y is not None]
    if len(pts) <= k:
        return
    knn = []
    for a in pts:
        ds = sorted(math.hypot(a[1] - b[1], a[2] - b[2]) for b in pts if b[0] != a[0])
        knn.append(ds[k - 1] if len(ds) >= k else ds[-1])
    med = sorted(knn)[len(knn) // 2]
    if med <= 0:
        return
    for (hid, x, y), d in zip(pts, knn):
        if d > cfg["outlier_factor"] * med:
            issues.append(models.Issue(
                "spatial_outlier", models.SEV_WARNING,
                "工程号 %s 的第 %d 近邻距离 %.1f m 显著大于中位数 %.1f m，疑似离群孔"
                % (hid, k, d, med), "定位表/%s" % hid,
                "阈值待确认；交由地质人员核验"))
