"""炮孔数据报告汇总工具 —— 命令行入口。

用法示例
--------
按文件逐个指定::

    python main.py -i "D:\\handle\\工作簿1.xlsx" "D:\\handle\\工作簿2.xlsx" ^
                   -o "D:\\handle\\3940平台 1008炮孔数据报告.xlsx"

按目录批量收集::

    python main.py -d "D:\\handle" -p "工作簿*.xlsx" ^
                   -o "D:\\handle\\3940平台 1008炮孔数据报告.xlsx"

不带任何参数则启动图形界面。
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.blast_report.builder import MergeOptions, merge_reports  # noqa: E402
from src.excel_core.reader import find_input_files, natural_key_compat  # noqa: E402

natural_key = natural_key_compat

DEFAULT_PATTERN = "*.xls*"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="炮孔报告汇总",
        description="把若干份 3DMine 炮孔数据库报告汇总成一份炮孔数据报告",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("-i", "--inputs", nargs="*", default=None,
                   help="输入文件（可含通配符，或直接给目录）")
    p.add_argument("-d", "--dir", default=None, help="批量收集输入文件的目录")
    p.add_argument("-p", "--pattern", default=DEFAULT_PATTERN,
                   help="目录收集时的文件名匹配模式，默认 %(default)s")
    p.add_argument("-o", "--output", required=False, default=None,
                   help="输出 xlsx 路径")
    p.add_argument("-t", "--title", default=None,
                   help="报告大标题，默认取输出文件名（不含扩展名）")
    p.add_argument("--no-appendix", action="store_true",
                   help="不在下方追加各源文件的原始报告")
    p.add_argument("--values", action="store_true",
                   help="小计/合计写死数值而不是公式（默认写公式）")
    p.add_argument("--gap", type=int, default=8,
                   help="汇总区与附录区之间的空行数，默认 8")
    p.add_argument("--gui", action="store_true", help="启动图形界面")
    return p


def run(args: argparse.Namespace) -> int:
    files = find_input_files(args.inputs, args.dir, args.pattern)
    files.sort(key=natural_key)
    if not files:
        print("[错误] 没有找到任何输入文件，请用 -i 或 -d/-p 指定。")
        return 2
    if not args.output:
        print("[错误] 请用 -o 指定输出文件路径。")
        return 2

    print("[输入] 共 %d 个文件：" % len(files))
    for f in files:
        print("       - %s" % f)

    options = MergeOptions(
        title=args.title,
        with_appendix=not args.no_appendix,
        appendix_gap=args.gap,
        use_formula=not args.values,
    )
    result = merge_reports(files, args.output, options)

    print("[输出] %s" % result["output"])
    print("[汇总] 矿块明细 %d 条，品位档 %s" % (result["blocks"], " / ".join(result["tiers"])))
    t = result["total"]
    print("[合计] 体积 %.3f m3 | 重量 %.3f t | 平均品位 %.4f g/t | 金属量 %.3f 百克"
          % (t["体积"], t["重量"], t["平均品位"] or 0, t["金属量"]))
    return 0


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

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
        return launch()

    if not args.output:
        parser.print_help()
        return 0
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
