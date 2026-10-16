"""把单日的二次圈矿矿块图复制进总目录的「6、…二次圈矿矿块图」文件夹。

这一步是**复制 + 改名**，不是合并：

* 源：``<单日目录>\\5、北部山头3970平台二次圈矿矿块图1011.dwg``
* 目标：``<总目录>\\6、北部山头3970平台二次圈矿矿块图\\北部山头3970平台二次圈矿矿块图1011.dwg``
  （文件名去掉开头的「N、」前缀）

判重规则（保证反复运行安全）：

* 目标已有同名文件且**内容相同** -> 跳过，什么都不做；
* 目标已有同名文件但**内容不同** -> 先备份成 ``<原名>_并入<日>.bak`` 再覆盖；
* 目标不存在 -> 直接复制。
"""

from __future__ import annotations

import filecmp
import os
import shutil

from .schema import KIND_DWG, KIND_LABELS, map_target_name

__all__ = ["copy_map", "files_identical"]


def files_identical(left: str, right: str) -> bool:
    """两个文件是否内容相同（先比大小再逐字节比，省时间）。"""
    try:
        if os.path.getsize(left) != os.path.getsize(right):
            return False
        return filecmp.cmp(left, right, shallow=False)
    except OSError:
        return False


def _backup(path: str) -> str:
    """把旧图备份成 ``<原名>.bak``（与 6、文件夹里既有的 1003.bak 习惯一致）。"""
    stem = os.path.splitext(path)[0]
    candidate = "%s.bak" % stem
    index = 2
    while os.path.exists(candidate):
        candidate = "%s.bak-%d" % (stem, index)
        index += 1
    shutil.copy2(path, candidate)
    return candidate


def copy_map(src_file: str, dst_dir: str, *,
             backup: bool = True,
             dry_run: bool = False) -> dict:
    """把 ``src_file`` 复制进 ``dst_dir``，文件名去掉编号前缀。

    返回与其他几类一致的统计字典，便于统一打印。
    """
    if not src_file or not os.path.isfile(src_file):
        raise FileNotFoundError("找不到单日矿块图：%s" % src_file)
    if not dst_dir:
        raise ValueError("没有指定矿块图目标文件夹")

    target = os.path.join(dst_dir, map_target_name(src_file))
    info = {
        "kind": KIND_DWG,
        "src": os.path.abspath(src_file),
        "dst": os.path.abspath(target),
        "dir": os.path.abspath(dst_dir),
        "written": False,
        "added": 0,
        "skipped": False,
        "backup": "",
        "reason": "",
    }

    if os.path.isfile(target) and files_identical(src_file, target):
        info.update(skipped=True, reason="目标文件夹里已有同名且内容相同的图，未重复复制")
        return info

    replacing = os.path.isfile(target)
    if dry_run:
        info["reason"] = ("目标已有同名图，内容不同 —— 会先备份再覆盖" if replacing
                          else "目标还没有这张图 —— 会直接复制")
        info["added"] = 1
        return info

    os.makedirs(dst_dir, exist_ok=True)
    if replacing and backup:
        info["backup"] = _backup(target)
    shutil.copy2(src_file, target)

    info.update(written=True, added=1,
                reason="已覆盖旧图（原件已备份）" if replacing else "已复制")
    return info


def describe(info: dict) -> str:
    """把结果整理成一行中文日志。"""
    name = os.path.basename(info["src"])
    label = KIND_LABELS[KIND_DWG]
    if info.get("skipped"):
        return "[跳过] %s：%s（%s）" % (label, name, info["reason"])
    if not info.get("written"):
        tail = "" if not info.get("reason") else "；%s" % info["reason"]
        return "[预演] %s：%s -> %s%s" % (label, name, os.path.basename(info["dst"]), tail)
    extra = "，旧图已备份为 %s" % os.path.basename(info["backup"]) if info.get("backup") else ""
    return "[复制] %s：%s -> %s%s" % (label, name, os.path.basename(info["dst"]), extra)
