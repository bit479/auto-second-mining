"""Excel 差异对比工具 —— 命令行入口。

用法:
    python main.py A.xlsx B.xlsx                 # 输出到当前目录 对比报告.xlsx
    python main.py A.xlsx B.xlsx -o out.xlsx     # 指定输出
    python main.py                                # 无参数则启动图形界面

退出码: 0=完成; 1=用法/参数错误; 2=运行错误
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from compare import compare_workbooks, diff_count
from reader import read_workbook
from writer import write_report


def _default_out(path_a: str) -> str:
    base = os.path.splitext(os.path.basename(path_a))[0]
    return os.path.join(os.getcwd(), f"对比报告_{base}.xlsx")


def run(path_a: str, path_b: str, out_path: str) -> dict:
    print(f"[1/3] 读取文件A: {path_a}")
    wb_a = read_workbook(path_a)
    print(f"[2/3] 读取文件B: {path_b}")
    wb_b = read_workbook(path_b)
    print("[3/3] 逐单元格对比中...")
    result = compare_workbooks(wb_a, wb_b)
    write_report(result, path_a, path_b, out_path, source_a=wb_a, source_b=wb_b)
    t = result["totals"]
    n = diff_count(result)
    print("-" * 48)
    print(f"比较非空单元格: {t['compared']}  相等: {t['equal']}")
    print(f"差异合计: {n}  (修改 {t['changed']} / 仅A {t['only_a']} / 仅B {t['only_b']})")
    print(f"报告已生成: {out_path}")
    return result


def _gui():
    import gui
    gui.main()


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        _gui()
        return 0

    paths = [a for a in argv if not a.startswith("-")]
    out_path = None
    for i, a in enumerate(argv):
        if a in ("-o", "--output") and i + 1 < len(argv):
            out_path = argv[i + 1]

    if len(paths) < 2:
        print("用法: python main.py A.xlsx B.xlsx [-o out.xlsx]")
        print("      不传参数则启动图形界面")
        return 1

    path_a, path_b = paths[0], paths[1]
    if out_path is None:
        out_path = _default_out(path_a)

    if not os.path.exists(path_a):
        print(f"找不到文件A: {path_a}")
        return 1
    if not os.path.exists(path_b):
        print(f"找不到文件B: {path_b}")
        return 1

    try:
        run(path_a, path_b, out_path)
    except Exception as e:
        print(f"运行出错: {e}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
