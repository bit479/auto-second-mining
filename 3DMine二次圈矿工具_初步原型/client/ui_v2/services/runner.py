# -*- coding: utf-8 -*-
"""后台任务（QProcess）：实时日志、状态、取消、防重复启动。

界面线程绝不跑长任务 —— 圈矿、DWG 转换、批量、验收全部走这里。
命令行参数与原工具**完全一致**（只是把 "python 脚本" 换成"exe 自派发"，见 paths.child_command）。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Iterable

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, Signal

from . import paths


@dataclass
class Task:
    tid: str
    name: str
    key: str
    argv: list[str]
    state: str = "排队中"                 # 排队中 / 运行中 / 完成 / 失败 / 已取消
    code: int | None = None
    started: float = field(default_factory=time.time)
    ended: float | None = None
    lines: list[str] = field(default_factory=list)
    process: QProcess | None = None

    @property
    def elapsed(self) -> float:
        return (self.ended or time.time()) - self.started


class TaskRunner(QObject):
    """全局单例：页面调用 ``run(...)``，订阅信号刷界面。"""

    log = Signal(str, str)          # (tid, line)
    state = Signal(str, str)        # (tid, 状态)
    finished = Signal(str, int)     # (tid, 退出码)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.tasks: dict[str, Task] = {}
        self._seq = 0

    # ---------------- 查询 ----------------

    def task(self, tid: str) -> Task | None:
        return self.tasks.get(tid)

    def running(self, key: str | None = None) -> bool:
        for t in self.tasks.values():
            if t.state in ("排队中", "运行中") and (key is None or t.key == key):
                return True
        return False

    def running_names(self) -> list[str]:
        return [t.name for t in self.tasks.values() if t.state in ("排队中", "运行中")]

    # ---------------- 启动 ----------------

    def run(self, name: str, rel_script: str, args: Iterable = (), *,
            key: str = "", cwd: str | None = None, env_extra: dict | None = None) -> str:
        """跑一个脚本。``key`` 相同的任务在执行期间不会被重复启动。"""
        key = key or rel_script
        if self.running(key):
            # 找到正在跑的那个，直接把它的日志给调用方
            for t in self.tasks.values():
                if t.key == key and t.state in ("排队中", "运行中"):
                    self.log.emit(t.tid, "[提示] 同一任务正在执行，不重复启动。")
                    return t.tid
        self._seq += 1
        tid = "t%03d" % self._seq
        argv = paths.child_command(rel_script, list(args))

        task = Task(tid=tid, name=name, key=key, argv=argv, state="运行中")
        self.tasks[tid] = task

        proc = QProcess(self)
        proc.setProcessChannelMode(QProcess.MergedChannels)
        penv = QProcessEnvironment()
        base = paths.child_env()
        if env_extra:
            base.update(env_extra)
        for k, v in base.items():
            penv.insert(k, str(v))
        proc.setProcessEnvironment(penv)
        if cwd:
            proc.setWorkingDirectory(cwd)
        elif not paths.is_frozen():
            proc.setWorkingDirectory(str(paths.bundle_root()))

        task.process = proc
        proc.readyReadStandardOutput.connect(lambda: self._drain(task))
        proc.finished.connect(lambda code, _s: self._on_finished(task, code))
        proc.errorOccurred.connect(lambda err: self._on_error(task, err))

        self.log.emit(tid, "[开始] %s" % name)
        self.log.emit(tid, "[命令] %s" % " ".join('"%s"' % a if " " in a else a for a in argv))
        self.state.emit(tid, "运行中")
        proc.start(argv[0], argv[1:])
        return tid

    # ---------------- 取消 ----------------

    def cancel(self, tid: str) -> None:
        t = self.tasks.get(tid)
        if not t or t.process is None or t.state != "运行中":
            return
        t.process.kill()
        self.log.emit(tid, "[取消] 已终止该任务")

    def cancel_all(self) -> None:
        for tid in list(self.tasks):
            self.cancel(tid)

    # ---------------- 内部 ----------------

    def _drain(self, task: Task) -> None:
        proc = task.process
        if proc is None:
            return
        raw = bytes(proc.readAllStandardOutput())
        if not raw:
            return
        text = raw.decode("utf-8", errors="replace")
        # 保留半行：QProcess 分片可能把一行切断
        pending = getattr(task, "_pending", "")
        text = pending + text
        lines = text.split("\n")
        task._pending = lines.pop() if lines else ""
        for line in lines:
            line = line.rstrip("\r")
            task.lines.append(line)
            del task.lines[:-4000]
            self.log.emit(task.tid, line)

    def _flush(self, task: Task) -> None:
        pending = getattr(task, "_pending", "")
        if pending:
            task.lines.append(pending)
            self.log.emit(task.tid, pending)
            task._pending = ""

    def _on_finished(self, task: Task, code: int) -> None:
        self._flush(task)
        task.code = int(code)
        task.ended = time.time()
        if code == 0:
            task.state = "完成"
        elif code in (2, 3) and any("取消" in l for l in task.lines[-3:]):
            task.state = "已取消"
        else:
            task.state = "失败"
        self.log.emit(task.tid, "[结束] 退出码 %s（用时 %.1f 秒）" % (code, task.elapsed))
        self.state.emit(task.tid, task.state)
        self.finished.emit(task.tid, int(code))

    def _on_error(self, task: Task, err) -> None:
        if err == QProcess.FailedToStart:
            task.state = "失败"
            self.log.emit(task.tid, "[错误] 启动失败：%s" % task.argv[0])
            self.state.emit(task.tid, task.state)
            self.finished.emit(task.tid, -1)


RUNNER: TaskRunner | None = None


def runner() -> TaskRunner:
    global RUNNER
    if RUNNER is None:
        RUNNER = TaskRunner()
    return RUNNER
