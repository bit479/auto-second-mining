# -*- coding: utf-8 -*-
"""统一线性图标（内联 SVG，不依赖外部资源文件）。

全部 24×24 viewBox、1.6 描边、圆角端点 —— 与界面其余部分保持同一手感。
颜色由调用方给（默认正文色），导航栏里用浅色。
"""

from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import QByteArray, QRectF, QSize, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from . import theme

_SVG = {
    "dashboard": '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/>'
                 '<rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    "target": '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3.2"/><path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3"/>',
    "layers": '<path d="M12 3.2 3.6 7.6 12 12l8.4-4.4L12 3.2Z"/><path d="m3.6 12.2 8.4 4.4 8.4-4.4"/>'
              '<path d="m3.6 16.6 8.4 4.4 8.4-4.4"/>',
    "crosshair": '<path d="M12 3v4M12 17v4M3 12h4M17 12h4"/><circle cx="12" cy="12" r="5.2"/>'
                 '<circle cx="12" cy="12" r="1"/>',
    "map": '<path d="M9 4 3.6 6v14L9 18l6 2 5.4-2V4L15 6 9 4Z"/><path d="M9 4v14M15 6v14"/>',
    "table": '<rect x="3" y="4.5" width="18" height="15" rx="2"/><path d="M3 9.5h18M9 9.5v10M15 9.5v10"/>',
    "database": '<ellipse cx="12" cy="6" rx="7.2" ry="2.8"/><path d="M4.8 6v6c0 1.5 3.2 2.8 7.2 2.8s7.2-1.3 7.2-2.8V6"/>'
                '<path d="M4.8 12v6c0 1.5 3.2 2.8 7.2 2.8s7.2-1.3 7.2-2.8v-6"/>',
    "sliders": '<path d="M5 4v6M5 14v6M12 4v10M12 18v2M19 4v3M19 11v9"/>'
               '<circle cx="5" cy="12" r="1.8"/><circle cx="12" cy="16" r="1.8"/><circle cx="19" cy="9" r="1.8"/>',
    "shield": '<path d="M12 3 5 6v5.5c0 4.3 3 7.6 7 9.5 4-1.9 7-5.2 7-9.5V6l-7-3Z"/><path d="m9 12 2.2 2.2L15.4 10"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.87l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.7 1.7 0 0 0-2.9 1.2v.17a2 2 0 1 1-4 0v-.09A1.7 1.7 0 0 0 7 19.4a1.7 1.7 0 0 0-1.87.34l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.7 1.7 0 0 0 2.6 14a1.7 1.7 0 0 0-1.2-1.55H1.2a2 2 0 1 1 0-4h.17A1.7 1.7 0 0 0 3 7a1.7 1.7 0 0 0-.34-1.87l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.7 1.7 0 0 0 7 2.6h.09A1.7 1.7 0 0 0 8.64 1.2V1.2a2 2 0 1 1 4 0v.17A1.7 1.7 0 0 0 14 3a1.7 1.7 0 0 0 1.87-.34l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.7 1.7 0 0 0 20.4 7v.09a1.7 1.7 0 0 0 1.2 1.55h.17a2 2 0 1 1 0 4h-.17a1.7 1.7 0 0 0-1.55 1.2Z"/>',
    "play": '<path d="M8 5.4v13.2L19 12 8 5.4Z"/>',
    "folder": '<path d="M3 7.5A1.5 1.5 0 0 1 4.5 6h4.2l1.8 2H19.5A1.5 1.5 0 0 1 21 9.5v8A1.5 1.5 0 0 1 19.5 19h-15A1.5 1.5 0 0 1 3 17.5v-10Z"/>',
    "file": '<path d="M14 3H7a1.6 1.6 0 0 0-1.6 1.6v14.8A1.6 1.6 0 0 0 7 21h10a1.6 1.6 0 0 0 1.6-1.6V7.6L14 3Z"/><path d="M13.6 3v4.6H18.4"/>',
    "check": '<circle cx="12" cy="12" r="8.6"/><path d="m8.4 12.2 2.5 2.5 4.7-5"/>',
    "alert": '<path d="M12 4.2 3.2 19.4h17.6L12 4.2Z"/><path d="M12 9.6v4.2M12 16.6v.2"/>',
    "x": '<circle cx="12" cy="12" r="8.6"/><path d="m9 9 6 6M15 9l-6 6"/>',
    "refresh": '<path d="M20 11a8 8 0 1 0-.6 4"/><path d="M20 5v6h-6"/>',
    "save": '<path d="M5 4.5h10L19.5 9v10a1.5 1.5 0 0 1-1.5 1.5H5A1.5 1.5 0 0 1 3.5 19V6A1.5 1.5 0 0 1 5 4.5Z"/>'
            '<path d="M7.5 4.5v5h7v-5M8 20v-6h8v6"/>',
    "external": '<path d="M14 4h6v6"/><path d="M20 4 11 13"/><path d="M18 14.5V19a1.5 1.5 0 0 1-1.5 1.5H5A1.5 1.5 0 0 1 3.5 19V7.5A1.5 1.5 0 0 1 5 6h4.5"/>',
    "plus": '<path d="M12 5.5v13M5.5 12h13"/>',
    "upload": '<path d="M12 16V4.8"/><path d="m7.6 9 4.4-4.4L16.4 9"/><path d="M4.5 15.5v3A1.5 1.5 0 0 0 6 20h12a1.5 1.5 0 0 0 1.5-1.5v-3"/>',
    "image": '<rect x="3" y="4.5" width="18" height="15" rx="2"/><circle cx="8.6" cy="9.8" r="1.6"/>'
             '<path d="m4 17 4.6-4.2 3.4 3 3-2.6L20 17.5"/>',
    "clock": '<circle cx="12" cy="12" r="8.6"/><path d="M12 7.4V12l3.2 2"/>',
    "info": '<circle cx="12" cy="12" r="8.6"/><path d="M12 11v5.2M12 8v.2"/>',
    "chevron": '<path d="m9.5 6.5 5.5 5.5-5.5 5.5"/>',
    "pick": '<path d="M4 20l7.6-7.6"/><path d="M9.2 6.6c1.6-1.6 4.6-2.2 7-1.6l-1.2 3.2 3.4-.6c.6 2.4-.2 5.2-1.8 6.8-2.4 2.4-6.4 2.2-8.6 0s-1.2-5.4 1.2-7.8Z"/>',
    "grid": '<rect x="3.5" y="3.5" width="17" height="17" rx="2"/><path d="M3.5 9.4h17M3.5 14.9h17M9.4 3.5v17M14.9 3.5v17"/>',
}


@lru_cache(maxsize=256)
def _render(name: str, color: str, size: int, dpr: float) -> QPixmap:
    body = _SVG.get(name, _SVG["info"])
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" '
        f'fill="none" stroke="{color}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
        f'{body}</svg>'
    )
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    px = QPixmap(int(size * dpr), int(size * dpr))
    px.setDevicePixelRatio(dpr)
    px.fill(Qt.transparent)
    painter = QPainter(px)
    painter.setRenderHint(QPainter.Antialiasing, True)
    renderer.render(painter, QRectF(0, 0, size * dpr, size * dpr))
    painter.end()
    return px


def pixmap(name: str, color: str = theme.TEXT, size: int = 18, dpr: float = 2.0) -> QPixmap:
    return _render(name, color, int(size), float(dpr))


def icon(name: str, color: str = theme.TEXT, size: int = 18) -> QIcon:
    return QIcon(pixmap(name, color, size))


def has(name: str) -> bool:
    return name in _SVG


def names() -> list[str]:
    return sorted(_SVG)


def size_hint(name: str, size: int = 18) -> QSize:
    return QSize(size, size)
