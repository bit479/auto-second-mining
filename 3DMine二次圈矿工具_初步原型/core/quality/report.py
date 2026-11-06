# -*- coding: utf-8 -*-
"""数据质量报告渲染（T02）。

把 `quality.check.check()` 的 Issue 列表渲染成文本 / Markdown 报告，
含按级别统计的汇总与逐条明细。只读、不写源数据。
"""
from __future__ import annotations

from data import models

_SEV_ORDER = {models.SEV_ERROR: 0, models.SEV_WARNING: 1, models.SEV_INFO: 2}
_SEV_LABEL = {models.SEV_ERROR: "阻断", models.SEV_WARNING: "警告", models.SEV_INFO: "提示"}


def summary(issues) -> dict:
    """按级别统计：{error: n, warning: n, info: n, total: n}。"""
    s = {"error": 0, "warning": 0, "info": 0, "total": len(issues)}
    for it in issues:
        if it.severity in s:
            s[it.severity] += 1
    return s


def render_text(issues, title: str = "数据质量检查报告") -> str:
    """纯文本报告（控制台/日志用）。"""
    s = summary(issues)
    lines = ["=" * 60, title,
             "阻断 %d ｜ 警告 %d ｜ 提示 %d ｜ 合计 %d"
             % (s["error"], s["warning"], s["info"], s["total"]), "=" * 60]
    if not issues:
        lines.append("未发现异常。")
    for it in sorted(issues, key=lambda x: (_SEV_ORDER.get(x.severity, 9), x.code)):
        lines.append(it.as_line())
    return "\n".join(lines)


def render_markdown(issues, source: str = "", title: str = "数据质量检查报告") -> str:
    """Markdown 报告。"""
    s = summary(issues)
    md = ["# %s" % title, ""]
    if source:
        md += ["- 来源文件：`%s`" % source, ""]
    md += ["| 级别 | 数量 |", "|---|---|",
           "| 阻断 | %d |" % s["error"],
           "| 警告 | %d |" % s["warning"],
           "| 提示 | %d |" % s["info"],
           "| **合计** | **%d** |" % s["total"], ""]
    if not issues:
        md.append("未发现异常。")
        return "\n".join(md)
    md += ["| 级别 | 错误码 | 说明 | 位置 | 建议 |", "|---|---|---|---|---|"]
    for it in sorted(issues, key=lambda x: (_SEV_ORDER.get(x.severity, 9), x.code)):
        md.append("| %s | %s | %s | %s | %s |"
                  % (_SEV_LABEL.get(it.severity, it.severity), it.code,
                     it.message.replace("|", "\\|"), it.where.replace("|", "\\|"),
                     it.hint.replace("|", "\\|")))
    return "\n".join(md)
