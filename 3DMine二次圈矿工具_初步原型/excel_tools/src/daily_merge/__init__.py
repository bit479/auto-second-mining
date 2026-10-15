"""单日数据并入总表 —— 业务层。

把某一天的三个文件按类型并入三份 2026 年总表：

===============  ======================  =========================
单日文件          总表                     做法
===============  ======================  =========================
炮孔数据库 .xls   1、…炮孔数据库-2026.xls    定位表/测斜表/pit_blast 逐行追加
炮孔数据库 .mdb   2、…炮孔数据库-2026.mdb    同上（Access SQL 插入）
炮孔数据报告 .xlsx  3、…炮孔数据报告-2026综合.xlsx  整体粘贴"标题→合计"汇总块
===============  ======================  =========================

对外主入口是 :func:`~src.daily_merge.pipeline.run`：

.. code-block:: python

    from src.daily_merge.pipeline import DailyMergeOptions, run, summarize

    report = run(DailyMergeOptions(day_dir=r"D:\\…\\北部山头3940平台-1008"))
    print("\\n".join(summarize(report)))
"""

from __future__ import annotations

from .discover import DailyMergeOptions, DailyMergePlan, resolve_plan
from .pipeline import backup_file, restore, run, summarize, verify

__all__ = [
    "DailyMergeOptions",
    "DailyMergePlan",
    "resolve_plan",
    "run",
    "summarize",
    "verify",
    "backup_file",
    "restore",
]
