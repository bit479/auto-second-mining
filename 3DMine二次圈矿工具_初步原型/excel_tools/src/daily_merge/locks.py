"""并入前先确认：这些文件**没有被 Excel / Access / 3DMine / AutoCAD 打开着**。

为什么要查
----------
1. 要写总表，被 Excel 打开时写不进去（`PermissionError`），甚至写到一半失败；
2. 单日文件虽然只读，但被别人开着时**磁盘上还是上次保存的内容**，
   改了没保存就并入 → 读进来的是旧数据，而且完全看不出来。

怎么判
------
* **写探测**：`os.open(path, O_RDWR)` 打不开 → 说明被别家占了写权限。
  Excel 打开工作簿、Access 打开 .mdb、CAD 打开 .dwg 都是这个表现。
* **锁文件**：Excel 会留 `~$<文件名>`，Access 留 `<文件名>.ldb`，
  AutoCAD 留 `<文件名>.dwl` / `.dwl2`。这些是**辅助证据**：
  程序崩溃后锁文件会残留，所以只有锁文件、但写探测能过 → 判为"残留锁"，不拦。

> 自动"保存并退出"没有做：本机没有 Office COM（pywin32 未装），
> 强行结束 Excel/Access 进程有丢数据的风险。所以一律**拦下来让人自己保存关闭**，
> 需要硬闯时用 `--allow-open`。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

__all__ = ["InUse", "write_probe", "lock_markers", "check", "format_message",
           "FilesInUseError"]


class FilesInUseError(RuntimeError):
    """有文件正被别的程序打开，不能安全并入。"""


@dataclass
class InUse:
    """一个"还开着"的文件。"""

    path: str
    role: str                       # "单日" / "总表"
    reasons: list[str] = field(default_factory=list)
    blocking: bool = True

    @property
    def name(self) -> str:
        return os.path.basename(self.path)


def write_probe(path: str) -> str | None:
    """试着以读写方式打开；能开返回 None，开不了返回原因文字。

    只是 open/close，不写任何字节，对文件内容零影响。
    """
    if not os.path.isfile(path):
        return None
    try:
        handle = os.open(path, os.O_RDWR)
    except OSError as exc:
        if isinstance(exc, PermissionError):
            if not os.access(path, os.W_OK):
                return "文件是只读属性（或当前账号没有写权限）"
            return "被其他程序占用（Excel / Access / 3DMine / AutoCAD 打开着）"
        return "打不开：%s" % exc
    else:
        os.close(handle)
        return None


_LOCK_SUFFIXES = (".ldb", ".laccdb", ".dwl", ".dwl2")


def lock_markers(path: str) -> list[str]:
    """同目录里与该文件相关的锁文件（只返回文件名）。"""
    folder, name = os.path.split(path)
    if not folder:
        return []
    found = []
    owner = os.path.join(folder, "~$" + name)
    if os.path.exists(owner):
        found.append(os.path.basename(owner))
    for suffix in _LOCK_SUFFIXES:
        candidate = path + suffix
        if os.path.exists(candidate):
            found.append(os.path.basename(candidate))
    return found


def check(files: list[tuple[str, str]]) -> tuple[list[InUse], list[InUse]]:
    """检查一组 ``(路径, 角色)``。

    返回 ``(拦下的, 仅有残留锁的)``。同一个路径只报一次。
    """
    blocking: list[InUse] = []
    stale: list[InUse] = []
    seen: set[str] = set()

    for path, role in files:
        if not path or not os.path.isfile(path):
            continue
        key = os.path.normcase(os.path.abspath(path))
        if key in seen:
            continue
        seen.add(key)

        problem = write_probe(path)
        markers = lock_markers(path)
        if problem:
            reasons = [problem]
            if markers:
                reasons.append("同目录有锁文件：%s" % "、".join(markers))
            blocking.append(InUse(path, role, reasons))
        elif markers:
            stale.append(InUse(path, role, ["同目录残留锁文件：%s" % "、".join(markers)],
                               blocking=False))
    return blocking, stale


def format_message(blocking: list[InUse], stale: list[InUse], *,
                   hint: str = "请先在 Excel / Access / 3DMine / AutoCAD 里**保存并关闭**这些文件，"
                               "然后重新运行。") -> str:
    """把检查结果拼成一段给人看的话。"""
    lines: list[str] = []
    if blocking:
        lines.append("[中止] 以下文件还开着（或没有写权限），现在并入会失败或读错数据：")
        for item in blocking:
            lines.append("  · [%s] %s" % (item.role, item.name))
            lines.append("        位置：%s" % item.path)
            for reason in item.reasons:
                lines.append("        原因：%s" % reason)
        lines.append("")
        lines.append(hint)
        lines.append("（确认没有未保存的修改后，也可以用 --allow-open 强行继续）")
    if stale:
        if lines:
            lines.append("")
        lines.append("[提示] 这些文件旁边有**残留**锁文件，但文件能正常写入，判定为已关闭，继续：")
        for item in stale:
            lines.append("  · [%s] %s —— %s" % (item.role, item.name, item.reasons[0]))
    return "\n".join(lines)
