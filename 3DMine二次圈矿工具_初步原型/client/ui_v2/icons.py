# -*- coding: utf-8 -*-
"""统一图标系统（Lucide 风格线性图标，内联 SVG，无外部资源、无运行时网络）。

v1.16 修复要点（原实现导致全站图标残缺/遮挡的根本原因）
------------------------------------------------------------
旧代码::

    px = QPixmap(size * dpr, size * dpr)
    px.setDevicePixelRatio(dpr)          # ← 先设置 DPR
    painter = QPainter(px)
    renderer.render(painter, QRectF(0, 0, size * dpr, size * dpr))   # ← 又按设备像素铺满

Qt 在 ``QPainter`` 开始时就会按 pixmap 的 devicePixelRatio 自动缩放坐标系，
再按 ``size * dpr`` 绘制，等于把 24×24 的图放大 ``dpr`` 倍后塞进同一张画布，
结果只画进了左上角 1/dpr² 的区域 —— 表现就是「图标只剩左上角一小段线段」
（浏览按钮的文件夹只剩一个折角、导航 target 只剩半圈）。

修复方式：先以设备像素坐标绘制满画布，**绘制结束之后**再 setDevicePixelRatio，
这样逻辑尺寸 == size，且不经过二次缩放；同时为 1/1.25/1.5/2/2.5/3 六档 DPR
各缓存一张位图供 QIcon 精确匹配，避免 Windows 125%/150% 下的非整数缩放模糊。

规范
----
* viewBox 固定 24×24，描边 1.75，圆角端点 + 圆角连接；
* ``ICON_NAV`` 20px（导航）、``ICON_BTN`` 16px（按钮内）、``ICON_CARD`` 22px（功能卡片）；
* 一律通过 ``label()`` 生成固定尺寸的 QLabel 承载图标，避免被布局压缩；
* 颜色由调用方传入，始终与当前主题前景色一致。
"""

from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import QByteArray, QRectF, QSize, Qt
from PySide6.QtGui import QGuiApplication, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QLabel, QWidget

from . import theme

ICON_NAV = 20
ICON_BTN = 16
ICON_CARD = 22

# 24×24 / 1.75 描边 / 圆角端点 —— 所有图标共用的外壳
_SVG = {
    # ---------------- 导航 ----------------
    "dashboard": '<rect x="3" y="3" width="7.4" height="9.4" rx="1.6"/>'
                 '<rect x="13.6" y="3" width="7.4" height="5.6" rx="1.6"/>'
                 '<rect x="3" y="15.6" width="7.4" height="5.4" rx="1.6"/>'
                 '<rect x="13.6" y="11.8" width="7.4" height="9.2" rx="1.6"/>',
    "target": '<circle cx="12" cy="12" r="7.6"/><circle cx="12" cy="12" r="2.6"/>'
              '<path d="M12 2.4v2.6M12 19v2.6M2.4 12H5M19 12h2.6"/>',
    "layers": '<path d="M12 3.4 3.4 7.8 12 12.2l8.6-4.4L12 3.4Z"/>'
              '<path d="m3.4 12.6 8.6 4.4 8.6-4.4"/>',
    "crosshair": '<circle cx="12" cy="12" r="4.6"/>'
                 '<path d="M12 2.6v4M12 17.4v4M2.6 12h4M17.4 12h4"/>',
    "pen": '<path d="M12.5 20.2H21"/><path d="M16.8 3.4a2.2 2.2 0 0 1 3.1 3.1L7.4 19l-4.2 1 1-4.2L16.8 3.4Z"/>',
    "map": '<path d="M9 4 3.6 6.2v13.4L9 17.4l6 2.2 5.4-2.2V4L15 6.2 9 4Z"/>'
           '<path d="M9 4v13.4M15 6.2v13.4"/>',
    "table": '<rect x="3" y="4.6" width="18" height="14.8" rx="2"/>'
             '<path d="M3 9.6h18M9.2 9.6v9.8"/>',
    "spreadsheet": '<rect x="3" y="4.6" width="18" height="14.8" rx="2"/>'
                   '<path d="M3 9.6h18M11.4 9.6v9.8"/>',
    "database": '<ellipse cx="12" cy="6" rx="7" ry="2.8"/>'
                '<path d="M5 6v12c0 1.55 3.13 2.8 7 2.8s7-1.25 7-2.8V6"/>'
                '<path d="M5 12c0 1.55 3.13 2.8 7 2.8s7-1.25 7-2.8"/>',
    "sliders": '<path d="M6 4v16M12 4v16M18 4v16"/>'
               '<circle cx="6" cy="9" r="2"/><circle cx="12" cy="15" r="2"/>'
               '<circle cx="18" cy="8" r="2"/>',
    "shield": '<path d="M12 3 5 5.8v5.4c0 4.2 2.9 7.5 7 9.3 4.1-1.8 7-5.1 7-9.3V5.8L12 3Z"/>'
              '<path d="m9 11.8 2.1 2.1 4-4.2"/>',
    "settings": '<path d="M3.6 7.6h8.2M17.4 7.6h3M3.6 16.4h3M12.2 16.4h8.2"/>'
                '<circle cx="14.6" cy="7.6" r="2.6"/><circle cx="9.4" cy="16.4" r="2.6"/>',
    "clipboard": '<rect x="4.6" y="4.6" width="14.8" height="16" rx="2"/>'
                 '<path d="M9 4.6V3.4h6v1.2"/><path d="m8.8 12.4 2 2 4.4-4.4"/>',

    # ---------------- 操作 ----------------
    "pick": '<path d="m14.2 13.4-7.7 7.7a2.1 2.1 0 0 1-3-3l7.7-7.7"/>'
            '<path d="m16.2 16.2 5.6-5.6"/><path d="m8.4 8.4 5.6-5.6"/>'
            '<path d="m9.4 7.4 7.4 7.4"/><path d="M20.6 11.4 12.6 3.4"/>',
    "play": '<path d="M9 5.6v12.8L18.6 12 9 5.6Z"/>',
    "pause": '<path d="M9 5.5v13M15 5.5v13"/>',
    "folder": '<path d="M3 7.6A1.6 1.6 0 0 1 4.6 6h4.2l1.8 2.1h8.8A1.6 1.6 0 0 1 21 9.7v8.7'
              'A1.6 1.6 0 0 1 19.4 20H4.6A1.6 1.6 0 0 1 3 18.4V7.6Z"/>',
    "folder-open": '<path d="M3 18.4V7.6A1.6 1.6 0 0 1 4.6 6h4.2l1.8 2.1h8.8A1.6 1.6 0 0 1 21 9.7v1.1"/>'
                   '<path d="M3 18.4 5.6 11h16.2l-2.6 7.4a1.6 1.6 0 0 1-1.5 1.1H4.6A1.6 1.6 0 0 1 3 18.4Z"/>',
    "file": '<path d="M13.6 3H7A1.7 1.7 0 0 0 5.3 4.7v14.6A1.7 1.7 0 0 0 7 21h10a1.7 1.7 0 0 0 1.7-1.7V8.1L13.6 3Z"/>'
            '<path d="M13.4 3.2v5h5.2"/>',
    "file-text": '<path d="M13.6 3H7A1.7 1.7 0 0 0 5.3 4.7v14.6A1.7 1.7 0 0 0 7 21h10a1.7 1.7 0 0 0 1.7-1.7V8.1L13.6 3Z"/>'
                 '<path d="M13.4 3.2v5h5.2M9 13.2h6M9 16.6h4.4"/>',
    "check": '<circle cx="12" cy="12" r="8.6"/><path d="m8.4 12.2 2.5 2.5 4.7-5"/>',
    "alert": '<path d="M12 4.4 3.4 19.4h17.2L12 4.4Z"/><path d="M12 9.6v4.2M12 16.7v.1"/>',
    "x": '<path d="m6.6 6.6 10.8 10.8M17.4 6.6 6.6 17.4"/>',
    "x-circle": '<circle cx="12" cy="12" r="8.6"/><path d="m9.2 9.2 5.6 5.6M14.8 9.2l-5.6 5.6"/>',
    "refresh": '<path d="M20.2 12a8.2 8.2 0 1 1-2.7-6.1"/><path d="M20.2 4.6v5.2h-5.2"/>',
    "save": '<path d="M5.6 4.4h8.8L19.6 9.6v10A1.4 1.4 0 0 1 18.2 21H5.6A1.4 1.4 0 0 1 4.2 19.6V5.8A1.4 1.4 0 0 1 5.6 4.4Z"/>'
            '<path d="M8.2 4.4v5h7v-5M8.2 21v-6.2h7.6V21"/>',
    "external": '<path d="M14 4h6v6"/><path d="M20 4 11.4 12.6"/>'
                '<path d="M18.4 14.6V19a1.4 1.4 0 0 1-1.4 1.4H5.4A1.4 1.4 0 0 1 4 19V7.4A1.4 1.4 0 0 1 5.4 6H10"/>',
    "plus": '<path d="M12 5.2v13.6M5.2 12h13.6"/>',
    "upload": '<path d="M12 16.2V4.8"/><path d="m7.6 9 4.4-4.4L16.4 9"/>'
              '<path d="M4.6 15.6v3A1.4 1.4 0 0 0 6 20h12a1.4 1.4 0 0 0 1.4-1.4v-3"/>',
    "image": '<rect x="3" y="4.6" width="18" height="14.8" rx="2"/>'
             '<circle cx="8.6" cy="9.6" r="1.5"/>'
             '<path d="m4.4 17.6 4.8-4.4 3.2 2.9 3.2-2.8 4 4.3"/>',
    "clock": '<circle cx="12" cy="12" r="8.6"/><path d="M12 7.4V12l3.2 2"/>',
    "info": '<circle cx="12" cy="12" r="8.6"/><path d="M12 11.2v5.2M12 7.9v.1"/>',
    "copy": '<rect x="9" y="9" width="11.4" height="11.4" rx="2"/>'
            '<path d="M6 15H5a1.6 1.6 0 0 1-1.6-1.6V5A1.6 1.6 0 0 1 5 3.4h8.4A1.6 1.6 0 0 1 15 5v1"/>',
    "grid": '<rect x="3.4" y="3.4" width="17.2" height="17.2" rx="2"/>'
            '<path d="M3.4 9.4h17.2M3.4 14.8h17.2M9.4 3.4v17.2M14.8 3.4v17.2"/>',
    "activity": '<path d="M3 12h3.4L9 4.6l4.2 14.8L15.8 12H21"/>',
    "mountain": '<path d="m2.8 19.4 6.6-11.2 3.5 5.6 2.6-4 5.7 9.6H2.8Z"/>',
    "dot": '<circle cx="12" cy="12" r="3.2"/>',
    "chevron": '<path d="m9.6 6.4 5.6 5.6-5.6 5.6"/>',
    "chevron-down": '<path d="m6.4 9.6 5.6 5.6 5.6-5.6"/>',
    "arrow-right": '<path d="M4.6 12h14.2"/><path d="m13.4 6.6 5.4 5.4-5.4 5.4"/>',
}

_HEADER = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" '
    'fill="none" stroke="{color}" stroke-width="1.75" stroke-linecap="round" '
    'stroke-linejoin="round">{body}</svg>'
)

_DPRS = (1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0)


@lru_cache(maxsize=512)
def _render(name: str, color: str, size: int, dpr: float) -> QPixmap:
    body = _SVG.get(name) or _SVG["info"]
    renderer = QSvgRenderer(QByteArray(_HEADER.format(color=color, body=body).encode("utf-8")))
    side = max(1, int(round(size * dpr)))
    px = QPixmap(side, side)
    px.fill(Qt.transparent)
    painter = QPainter(px)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.TextAntialiasing, True)
    # 设备像素坐标下铺满 0..side；绘制完成后再设 DPR，避免 Qt 自动二次缩放
    renderer.render(painter, QRectF(0, 0, side, side))
    painter.end()
    px.setDevicePixelRatio(dpr)
    return px


def screen_dpr() -> float:
    scr = QGuiApplication.primaryScreen()
    return float(scr.devicePixelRatio()) if scr is not None else 1.0


def pixmap(name: str, color: str = theme.TEXT, size: int = 18, dpr: float | None = None) -> QPixmap:
    """固定逻辑尺寸的位图（size×size）；dpr=None 时取当前屏幕 DPR。"""
    return _render(name, color, int(size), float(dpr or screen_dpr()))


def icon(name: str, color: str = theme.TEXT, size: int = 18) -> QIcon:
    """QIcon：内置 7 档 DPR 位图，Windows 125%/150% 下无需再次重采样。"""
    ic = QIcon()
    for dpr in _DPRS:
        ic.addPixmap(_render(name, color, int(size), dpr))
    return ic


def label(name: str, color: str = theme.TEXT, size: int = 18,
          parent: QWidget | None = None, opacity: float = 1.0) -> QLabel:
    """把图标装进固定尺寸的 QLabel：不会被文字/布局压缩，也不会被裁切。"""
    lab = QLabel(parent)
    pm = pixmap(name, color, size)
    if opacity < 1.0:
        from PySide6.QtGui import QPainter as _P

        faded = QPixmap(pm)
        faded.fill(Qt.transparent)
        p = _P(faded)
        p.setOpacity(max(0.0, min(1.0, opacity)))
        p.drawPixmap(0, 0, pm)
        p.end()
        pm = faded
    lab.setPixmap(pm)
    lab.setFixedSize(QSize(size, size))
    lab.setAlignment(Qt.AlignCenter)
    lab.setAttribute(Qt.WA_TranslucentBackground, True)
    lab.setStyleSheet("background: transparent; border: none;")
    return lab


def has(name: str) -> bool:
    return name in _SVG


def names() -> list[str]:
    return sorted(_SVG)


def size_hint(name: str, size: int = 18) -> QSize:
    return QSize(size, size)
