# -*- coding: utf-8 -*-
"""自检：并入前的"文件是否已保存并关闭"检测。

覆盖 6 件事：

1. 普通文件 → 判定为可用；
2. 被别的进程**独占**打开 → 判定为占用（这是 Excel / Access / CAD 的真实表现，
   这里用 `CreateFileW(share=0)` 模拟，不依赖真的开 Excel）；
3. 只有 `~$` 残留锁文件、但文件能写 → 判为"残留"，**不拦**；
4. 只有 `.ldb` 残留（Access 崩溃常见）→ 同样不拦；
5. 同一路径重复传入只报一次；
6. 提示文字里带文件名、且给出"保存并关闭"的动作指引。

用法::

    python tests/test_locks.py
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.daily_merge import locks  # noqa: E402

_checks: list[tuple[bool, str]] = []
_handles: list = []


def check(ok: bool, message: str) -> None:
    _checks.append((bool(ok), message))
    print("  %s  %s" % ("OK  " if ok else "FAIL", message))


def hold(path: str):
    """以 share=0 独占打开文件，模拟"被 Excel 打开"。返回句柄，最后统一关。"""
    import ctypes

    GENERIC_READ = 0x80000000
    OPEN_EXISTING = 3
    FILE_ATTRIBUTE_NORMAL = 0x80
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateFileW.restype = ctypes.c_void_p
    handle = kernel32.CreateFileW(path, GENERIC_READ, 0, None, OPEN_EXISTING,
                                  FILE_ATTRIBUTE_NORMAL, None)
    _handles.append(handle)
    return handle


def release_all() -> None:
    import ctypes

    kernel32 = ctypes.windll.kernel32
    for handle in _handles:
        if handle and handle != ctypes.c_void_p(-1).value:
            kernel32.CloseHandle(ctypes.c_void_p(handle))
    _handles.clear()


def main() -> int:
    if not sys.platform.startswith("win"):
        print("非 Windows，跳过（占用检测依赖 Windows 的共享锁语义）")
        return 0

    tmp = tempfile.mkdtemp(prefix="locks_test_")
    try:
        plain = os.path.join(tmp, "1、炮孔数据库.xls")
        mdb = os.path.join(tmp, "2、炮孔数据库.mdb")
        for path in (plain, mdb):
            with open(path, "wb") as fh:
                fh.write(b"placeholder")

        print("=" * 74)
        print("[1/6] 普通文件不拦")
        blocking, stale = locks.check([(plain, "单日"), (mdb, "总表")])
        check(not blocking, "没被打开 → blocking 为空")
        check(not stale, "没有锁文件残留 → stale 为空")

        print("\n[2/6] 被独占打开 → 拦住")
        hold(plain)
        blocking, stale = locks.check([(plain, "总表")])
        check(len(blocking) == 1, "检出 1 个占用文件")
        check(blocking and "占用" in " ".join(blocking[0].reasons),
              "原因写明被占用：%s" % (blocking[0].reasons if blocking else ""))
        check(blocking and blocking[0].name == os.path.basename(plain),
              "报告里带文件名")
        release_all()

        print("\n[3/6] 只有 ~$ 残留（文件能写）→ 不拦")
        owner = os.path.join(tmp, "~$" + os.path.basename(plain))
        with open(owner, "wb") as fh:
            fh.write(b"owner")
        blocking, stale = locks.check([(plain, "单日")])
        check(not blocking, "不当作占用")
        check(len(stale) == 1 and "~$" in stale[0].reasons[0],
              "识别为残留锁：%s" % (stale[0].reasons if stale else ""))
        os.remove(owner)

        print("\n[4/6] 只有 .ldb 残留 → 不拦")
        ldb = mdb + ".ldb"
        with open(ldb, "wb") as fh:
            fh.write(b"lock")
        blocking, stale = locks.check([(mdb, "总表")])
        check(not blocking, "不当作占用")
        check(len(stale) == 1, "识别为残留锁")
        os.remove(ldb)

        print("\n[5/6] 重复路径只报一次")
        hold(mdb)
        blocking, _ = locks.check([(mdb, "总表"), (mdb, "单日")])
        check(len(blocking) == 1, "同一文件传入两次也只报 1 条")
        release_all()

        print("\n[6/6] 提示文字")
        hold(plain)
        blocking, stale = locks.check([(plain, "总表")])
        text = locks.format_message(blocking, stale)
        check("保存并关闭" in text, "给出动作指引")
        check(os.path.basename(plain) in text, "点名是哪个文件")
        check("--allow-open" in text, "提供硬闯开关")
        release_all()
    finally:
        release_all()
        shutil.rmtree(tmp, ignore_errors=True)

    passed = sum(1 for ok, _ in _checks if ok)
    print("\n" + "=" * 74)
    print("共 %d 项检查，%d 项通过" % (len(_checks), passed))
    print("结论：" + ("全部一致 ✓" if passed == len(_checks) else "存在问题 ✗"))
    return 0 if passed == len(_checks) else 1


if __name__ == "__main__":
    sys.exit(main())
