"""炮孔数据工具 —— 命令行入口。

两种用法：

1. **报告汇总**：把若干份 3DMine 炮孔数据库报告汇总成一份炮孔数据报告。

   汇总方式有两种（``--mode``，默认 ``total``）：

   * ``total``（1011 起的新口径）—— 每份源文件的「总计」行整体当成一个矿块，
     按矿块品位落档、档位从高到低排、同档内保持文件顺序、体号重新编号；
   * ``detail``（0915/0922/1008 的旧口径）—— 把每行明细拆开按品位档归组。

   .. code-block:: bat

      python main.py -i "工作表1.xls" "工作表2.xls" "工作表3.xls" "工作表4.xls"
      python main.py -d "…\\Desktop\\3940平台\\1011" -p "工作表*.xls"
      python main.py -d "…\\handle" -p "工作簿*.xlsx" --mode detail -o "…\\3940平台 1008炮孔数据报告.xlsx"

   不给 ``-o`` 时输出到第一个输入文件所在目录，文件名按
   「<矿名><平台>平台<日期>炮孔数据报告.xlsx」生成。

2. **单日并入总表**：把某一天的 xls / mdb / 报告 并入 2026 年三份总表。

   .. code-block:: bat

      python main.py --daily -d "D:\\…\\7、单日数据\\北部山头3940平台-1008"

   单日文件与总表都会自动探测；总表目录默认从单日目录向上回溯。

不带任何参数运行则打开图形界面。
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.blast_report.builder import MergeOptions, merge_reports  # noqa: E402
from src.blast_report import naming  # noqa: E402
from src.blast_report.schema import (DEFAULT_MINE_PREFIX, DEFAULT_MODE,  # noqa: E402
                                     MODE_LABELS, MODES)
from src.excel_core.reader import find_input_files, natural_key_compat  # noqa: E402

natural_key = natural_key_compat

DEFAULT_PATTERN = "*.xls*"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="炮孔数据工具",
        description="炮孔数据报告汇总 / 单日数据并入总表",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # ---------- 报告汇总 ----------
    g1 = p.add_argument_group("报告汇总")
    g1.add_argument("-i", "--inputs", nargs="*", default=None,
                    help="输入文件（可含通配符，或直接给目录）")
    g1.add_argument("-d", "--dir", default=None, help="批量收集输入文件的目录")
    g1.add_argument("-p", "--pattern", default=DEFAULT_PATTERN,
                    help="目录收集时的文件名匹配模式，默认 %(default)s")
    g1.add_argument("-o", "--output", required=False, default=None,
                    help="输出 xlsx 路径；留空则写到第一个输入文件所在目录，"
                         "文件名取「<矿名><平台>平台<日期>炮孔数据报告.xlsx」")
    g1.add_argument("-t", "--title", default=None,
                    help="报告大标题，默认按「矿名+平台+日期」推断"
                         "（如 北部山头3940平台1011炮孔数据报告）")
    g1.add_argument("--mode", choices=list(MODES), default=DEFAULT_MODE,
                    help="汇总方式，默认 %(default)s —— "
                         "total=每个文件的「总计」行当一个矿块；detail=把明细行拆开按档汇总")
    g1.add_argument("--mine-prefix", dest="mine_prefix", default=None,
                    help="标题里的矿名前缀，默认 %s" % DEFAULT_MINE_PREFIX)
    g1.add_argument("--no-appendix", action="store_true",
                    help="不在下方追加各源文件的原始报告")
    g1.add_argument("--values", action="store_true",
                    help="小计/合计写死数值而不是公式（默认写公式）")
    g1.add_argument("--gap", type=int, default=8,
                    help="汇总区与附录区之间的空行数，默认 8")

    # ---------- 单日并入总表 ----------
    g2 = p.add_argument_group("单日数据并入总表")
    g2.add_argument("--daily", action="store_true",
                    help="启用「单日数据并入总表」模式")
    g2.add_argument("--day-dir", dest="day_dir", default=None,
                    help="单日数据目录，如 …\\7、单日数据\\北部山头3940平台-1008")
    g2.add_argument("--master-dir", dest="master_dir", default=None,
                    help="总表目录，留空则从单日目录向上自动定位")
    g2.add_argument("--day", default=None, help="日期代号（如 1008），留空自动识别")
    g2.add_argument("--src-xls", default=None, help="指定单日炮孔数据库 .xls")
    g2.add_argument("--src-mdb", default=None, help="指定单日炮孔数据库 .mdb")
    g2.add_argument("--src-report", default=None, help="指定单日炮孔数据报告 .xlsx")
    g2.add_argument("--src-map", default=None,
                    help="指定单日二次圈矿矿块图 .dwg（形如 5、…二次圈矿矿块图1008.dwg）")
    g2.add_argument("--dst-xls", default=None, help="指定总表炮孔数据库 .xls")
    g2.add_argument("--dst-mdb", default=None, help="指定总表炮孔数据库 .mdb")
    g2.add_argument("--dst-report", default=None, help="指定总表综合报告 .xlsx")
    g2.add_argument("--dst-map", default=None,
                    help="指定总表的「6、…二次圈矿矿块图」文件夹，留空自动探测")
    g2.add_argument("--no-map", action="store_true",
                    help="不复制二次圈矿矿块图（默认会顺手把 5、…矿块图 复制进 6、文件夹）")
    g2.add_argument("--allow-duplicates", action="store_true",
                    help="不判重：工程号已存在也照插（默认跳过重复）")
    g2.add_argument("--with-appendix", action="store_true",
                    help="报告并入时连同附录一起搬进总表")
    g2.add_argument("--no-backup", action="store_true",
                    help="写入前不备份总表（默认备份成 *_并入<日>.bak）")
    g2.add_argument("--dry-run", action="store_true",
                    help="只计算不写盘，用于预演")
    g2.add_argument("--restore", action="store_true",
                    help="从 *_并入<日>.bak 还原三份总表")

    # ---------- 通用 ----------
    p.add_argument("--gui", action="store_true", help="启动图形界面")
    p.add_argument("--tab", choices=["report", "daily"], default="report",
                   help="图形界面默认打开哪个标签页")
    return p


# --------------------------------------------------------------------------
# 报告汇总
# --------------------------------------------------------------------------

def run_merge(args: argparse.Namespace) -> int:
    files = find_input_files(args.inputs, args.dir, args.pattern)
    files.sort(key=natural_key)
    if not files:
        print("[错误] 没有找到任何输入文件，请用 -i 或 -d/-p 指定。")
        return 2

    title = args.title or naming.guess_title(files, args.output, args.mine_prefix)
    output = args.output or naming.default_output_path(files, title)

    print("[输入] 共 %d 个文件：" % len(files))
    for f in files:
        print("       - %s" % f)
    print("[方式] %s" % MODE_LABELS.get(args.mode, args.mode))
    print("[标题] %s" % (title or os.path.splitext(os.path.basename(output))[0]))
    print("[输出] %s" % output)

    options = MergeOptions(
        title=args.title,
        with_appendix=not args.no_appendix,
        appendix_gap=args.gap,
        use_formula=not args.values,
        mode=args.mode,
        mine_prefix=args.mine_prefix,
    )
    result = merge_reports(files, output, options)

    print("[汇总] 矿块 %d 个，品位档 %s" % (result["blocks"], " / ".join(result["tiers"])))
    t = result["total"]
    print("[合计] 体积 %.3f m3 | 重量 %.3f t | 平均品位 %.4f g/t | 金属量 %.3f 百克"
          % (t["体积"], t["重量"], t["平均品位"] or 0, t["金属量"]))
    return 0


# --------------------------------------------------------------------------
# 单日并入总表
# --------------------------------------------------------------------------

def run_daily(args: argparse.Namespace) -> int:
    from src.daily_merge.pipeline import (DailyMergeOptions, resolve_plan,
                                          restore, run, summarize)
    from src.daily_merge.schema import KIND_DWG, KIND_MDB, KIND_REPORT, KIND_XLS

    if args.restore:
        master_dir = args.master_dir or args.day_dir
        if not master_dir:
            print("[错误] 还原需要指定总表目录（--master-dir）。")
            return 2
        try:
            done = restore(master_dir, args.day)
        except Exception as exc:  # noqa: BLE001
            print("[失败] %s" % exc)
            return 1
        if not done:
            print("[提示] 没有找到可用的 *_并入*.bak 备份。")
            return 1
        print("[还原] 共还原 %d 份总表：" % len(done))
        for kind, line in done.items():
            print("       %s" % line)
        print("       （原文件已另存为 *_还原前<时间>.bak）")
        return 0

    if not args.day_dir and not any(
            (args.src_xls, args.src_mdb, args.src_report, args.src_map)):
        print("[错误] 请用 --day-dir 指定单日目录，或用 --src-* 逐个指定单日文件。")
        return 2

    options = DailyMergeOptions(
        day_dir=args.day_dir,
        master_dir=args.master_dir,
        src={KIND_XLS: args.src_xls, KIND_MDB: args.src_mdb,
             KIND_REPORT: args.src_report, KIND_DWG: args.src_map},
        dst={KIND_XLS: args.dst_xls, KIND_MDB: args.dst_mdb,
             KIND_REPORT: args.dst_report, KIND_DWG: args.dst_map},
        day_code=args.day,
        skip_duplicates=not args.allow_duplicates,
        with_report_appendix=args.with_appendix,
        with_map=not args.no_map,
        backup=not args.no_backup,
        dry_run=args.dry_run,
    )

    try:
        plan = resolve_plan(options)
    except Exception as exc:  # noqa: BLE001
        print("[失败] %s" % exc)
        return 1

    print("=" * 72)
    for line in plan.describe():
        print(line)
    if plan.missing:
        print("  ── 未匹配到 ──")
        for item in plan.missing:
            print("  · %s" % item)
    print("=" * 72)

    if not plan.executable:
        print("[错误] 没有任何一对文件可执行。")
        return 2

    try:
        report = run(options)
    except Exception as exc:  # noqa: BLE001
        print("[失败] %s" % exc)
        return 1

    for line in summarize(report):
        print(line)

    if report["errors"]:
        print("[结束] 存在失败项，请检查上面日志。")
        return 1
    print("[结束] 全部完成 ✓")
    return 0


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.daily or args.restore:
        return run_daily(args)

    want_gui = args.gui or (argv is None and len(sys.argv) == 1)
    if want_gui:
        try:
            from gui import launch
        except ImportError as exc:
            if args.gui:
                print("[提示] 当前 Python 没有 tkinter，无法启动图形界面：%s" % exc)
                print("       请改用命令行，或换用自带 tkinter 的 Python（官方安装包默认包含）。")
                return 1
            parser.print_help()
            return 0
        return launch(tab=args.tab)

    if not (args.inputs or args.dir):
        parser.print_help()
        return 0
    return run_merge(args)


if __name__ == "__main__":
    raise SystemExit(main())
