# -*- coding: utf-8 -*-
"""全局文件拖放管理器。

实现方式（刻意不碰页面）
------------------------
在主窗口上开启 ``acceptDrops``（Qt 会因此向 Windows 注册 OLE 放置目标），
再由本管理器作为 **QApplication 事件过滤器** 拦截 ``DragEnter / DragMove / Drop``：

* 过滤器比任何页面控件都先拿到事件 → 不管用户停在哪一页、哪个控件上都能接住；
* 只拦截单个 ``.txt`` / ``.dat`` 文件；其它类型（xls/dwg/3ds…）原样放行，
  页面里既有的 ``FileRow`` 拖放行为完全不受影响；
* 用 ``_busy`` 与"上一次落点的 路径+大小+修改时间"做去重：一个文件只会被处理一次，
  连续拖入同一文件不会重复解析，拖入不同文件才会替换任务；
* 解析在 ``QThreadPool`` 里跑，主线程只收信号 → 大文件不卡界面；Esc 可取消。
"""

from __future__ import annotations

import os
import threading

from PySide6.QtCore import QEvent, QObject, QRunnable, QThreadPool, Qt, Signal
from PySide6.QtWidgets import QApplication, QWidget

from . import txt_import


class _JobSignals(QObject):
    done = Signal(object)        # TxtImportTask
    failed = Signal(str)


class _ParseJob(QRunnable):
    def __init__(self, path: str):
        super().__init__()
        self.path = path
        self.signals = _JobSignals()
        self._cancel = threading.Event()

    def cancel(self) -> None:
        self._cancel.set()

    def is_cancelled(self) -> bool:
        return self._cancel.is_set()

    def run(self) -> None:
        try:
            task = txt_import.parse_txt_file(self.path, should_cancel=self._cancel.is_set)
            self.signals.done.emit(task)
        except txt_import.ParseCancelled:
            self.signals.failed.emit("已取消本次解析")
        except Exception as exc:              # noqa: BLE001 - 解析异常不能带崩界面
            self.signals.failed.emit("解析失败：%s" % exc)


class GlobalFileDropManager(QObject):
    """接收任意页面拖入的 TXT 坐标文件并交给后台线程解析。"""

    hint = Signal(str, str)          # (kind, text)  kind: drop / hide / busy / reject / info
    busy_changed = Signal(bool)
    finished = Signal(object)        # TxtImportTask
    failed = Signal(str)

    def __init__(self, window: QWidget, parent: QObject | None = None):
        super().__init__(parent or window)
        self.window = window
        self._drag_path = ""
        self._job: _ParseJob | None = None
        self._busy = False
        self._pending_path = ""
        self._last_identity: tuple | None = None
        self._pool = QThreadPool.globalInstance()
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

    # ------------------------------------------------------------ 状态

    @property
    def busy(self) -> bool:
        return self._busy

    def current_identity(self) -> tuple | None:
        return self._last_identity

    def cancel(self) -> None:
        if self._job is not None:
            self._job.cancel()
        self._pending_path = ""
        self._set_busy(False)
        self.hint.emit("hide", "")
        txt_import.cleanup_cache()

    # ------------------------------------------------------------ 事件过滤

    def eventFilter(self, obj, event) -> bool:
        etype = event.type()
        if etype == QEvent.Type.DragEnter:
            return self._on_drag_enter(event)
        if etype == QEvent.Type.DragMove:
            if self._drag_path:
                event.acceptProposedAction()
                return True
            return False
        if etype == QEvent.Type.DragLeave:
            if self._drag_path:
                self._drag_path = ""
                self.hint.emit("hide", "")
                return True
            return False
        if etype == QEvent.Type.Drop:
            return self._on_drop(event)
        if etype == QEvent.Type.KeyPress and self._busy:
            if event.key() == Qt.Key_Escape:
                self.cancel()
                return True
        return False

    def _on_drag_enter(self, event) -> bool:
        paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        if not paths:
            return False
        txts = [p for p in paths if txt_import.is_txt_candidate(p)]

        if self._busy:
            # 解析中又拖入：排队（后来的优先），不打断当前解析
            if txts:
                self._pending_path = txts[0]
                self.hint.emit("info", "已排队：当前文件解析完后自动导入 %s"
                               % os.path.basename(txts[0]))
            else:
                self.hint.emit("reject", "上一个文件还在解析，请稍候")
            event.acceptProposedAction()
            self._drag_path = ""
            return True

        if not txts:
            # 非 TXT：若指针正停在支持拖放的控件上（如文件输入行），交给它自己处理
            if not self._local_target_accepts():
                self.hint.emit("reject", "只支持拖入 .txt 坐标文件（%s）"
                               % os.path.basename(paths[0]))
                event.acceptProposedAction()
                return True
            return False

        if len(txts) > 1:
            self.hint.emit("reject", "一次只能导入一个 TXT 文件")
            event.acceptProposedAction()
            self._drag_path = ""
            return True

        path = txts[0]
        if not os.path.isfile(path):
            self.hint.emit("reject", "文件不存在或无法访问：%s" % os.path.basename(path))
            event.acceptProposedAction()
            return True

        self._drag_path = path
        event.acceptProposedAction()
        self.hint.emit("drop", os.path.basename(path))
        return True

    def _on_drop(self, event) -> bool:
        if not self._drag_path:
            return False
        path, self._drag_path = self._drag_path, ""
        event.acceptProposedAction()
        self.start_import(path)
        return True

    def _local_target_accepts(self) -> bool:
        """指针下面的控件（不含主窗口自己）是否显式接受拖放。"""
        from PySide6.QtGui import QCursor

        w = QApplication.widgetAt(QCursor.pos())
        while w is not None:
            if w is self.window:
                return False
            if w.acceptDrops():
                return True
            w = w.parentWidget()
        return False

    # ------------------------------------------------------------ 入口

    def start_import(self, path: str) -> None:
        """外部也可直接调用（例如页面上的"重新选择文件"）。"""
        path = str(path)
        if self._busy:
            self._pending_path = path
            self.hint.emit("info", "已排队：当前文件解析完后自动导入 %s"
                           % os.path.basename(path))
            return


        if not os.path.isfile(path):
            msg = "文件不存在或无法访问：%s" % os.path.basename(path)
            self.failed.emit(msg)
            self.hint.emit("reject", msg)
            return
        try:
            stat = os.stat(path)
            identity = (path.lower(), int(stat.st_size), int(stat.st_mtime))
        except OSError as exc:
            msg = "无法读取文件信息：%s" % exc
            self.failed.emit(msg)
            self.hint.emit("reject", msg)
            return

        if identity == self._last_identity:
            # 同一个文件再次拖入：不重复解析，直接复用已有任务
            self.hint.emit("info", "这就是当前导入的文件，已直接打开")
            self.finished.emit(self._reuse_task)
            return

        job = _ParseJob(path)
        job.signals.done.connect(
            lambda task, ident=identity, j=job: self._on_done(task, ident, j))
        job.signals.failed.connect(self._on_failed)
        self._job = job
        self._set_busy(True)
        self.hint.emit("busy", os.path.basename(path))
        self._pool.start(job)

    # 上次成功的任务（供"重复拖入同一文件"复用）
    _reuse_task = None

    def _on_done(self, task, identity: tuple, job=None) -> None:
        self._job = None
        self._set_busy(False)
        if job is not None and job.is_cancelled():
            self.hint.emit("info", "已取消本次导入")
            self._start_pending()
            return
        if task.state == "failed":
            self.hint.emit("reject", task.error or "解析失败")
            self.failed.emit(task.error or "解析失败")
            return
        self._last_identity = identity
        self._reuse_task = task
        txt_import.cleanup_cache(keep=task.effective_path)
        self.finished.emit(task)
        self._start_pending()

    def _on_failed(self, message: str) -> None:
        self._job = None
        self._set_busy(False)
        self.hint.emit("reject", message)
        self.failed.emit(message)
        self._start_pending()

    def _start_pending(self) -> None:
        """解析期间又拖进来一个文件 → 等当前结束后自动接着导入（后来的优先）。"""
        path, self._pending_path = getattr(self, "_pending_path", ""), ""
        if not path:
            return
        from PySide6.QtCore import QTimer

        QTimer.singleShot(0, lambda p=path: self.start_import(p))

    def _set_busy(self, busy: bool) -> None:
        if self._busy == busy:
            return
        self._busy = busy
        self.busy_changed.emit(busy)
