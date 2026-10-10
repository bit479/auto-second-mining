"""生成 Excel 差异对比工具的图标 (app.ico 多尺寸 + app.png)。

设计思路: 蓝色圆角底(专业"数据软件"感) + 两页重叠表格(代表"两个文件对比")
+  amber 放大镜(代表"查找差异") + 一个高亮单元格(代表"被改动的格")。

运行: python tools/make_icon.py
依赖: Pillow
"""
from __future__ import annotations

import os
import sys

from PIL import Image, ImageDraw

# ---- 配色 ----
BG_TOP = (45, 127, 249)      # #2D7FF9
BG_BOT = (21, 94, 212)       # #155ED4
SHEET_BACK = (150, 184, 236)  # 后页(浅蓝)
SHEET_FRONT = (255, 255, 255)  # 前页(白)
GRID = (198, 208, 226)        # 网格线
MAG_RING = (245, 166, 35)     # 放大镜外圈 amber #F5A623
MAG_FILL = (255, 255, 255)    # 镜面
HILITE = (255, 209, 102)      # 高亮单元格(=改动, 与报告"修改"色一致)

SIZES = [16, 24, 32, 48, 64, 128, 256]
BASE = 256.0


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _rounded_bg(S):
    """生成带竖直渐变圆角底的 RGBA 图层。"""
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for y in range(S):
        t = y / max(1, S - 1)
        c = _lerp(BG_TOP, BG_BOT, t)
        d.line([(0, y), (S, y)], fill=c + (255,))
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, S - 1, S - 1], radius=int(S * 0.22), fill=255)
    img.putalpha(mask)
    return img


def _sheet(d, S, x0, y0, x1, y1, fill):
    d.rounded_rectangle([x0, y0, x1, y1], radius=int(S * 0.06), fill=fill)


def _grid(d, S, x0, y0, x1, y1, cols, rows):
    w = x1 - x0
    h = y1 - y0
    lw = max(1, int(S * 0.012))
    for i in range(1, cols):
        cx = x0 + w * i / cols
        d.line([(cx, y0 + lw), (cx, y1 - lw)], fill=GRID, width=lw)
    for j in range(1, rows):
        cy = y0 + h * j / rows
        d.line([(x0 + lw, cy), (x1 - lw, cy)], fill=GRID, width=lw)


def draw_icon(S):
    img = _rounded_bg(S)
    d = ImageDraw.Draw(img)

    # 后页(右上, 代表文件 B)
    _sheet(d, S, S * 0.36, S * 0.08, S * 0.94, S * 0.70, SHEET_BACK)

    # 前页(左下, 代表文件 A)
    fx0, fy0, fx1, fy1 = S * 0.06, S * 0.24, S * 0.66, S * 0.88
    _sheet(d, S, fx0, fy0, fx1, fy1, SHEET_FRONT)
    _grid(d, S, fx0, fy0, fx1, fy1, cols=3, rows=4)

    # 高亮一个单元格(表示"这里有差异")
    cw = (fx1 - fx0) / 3
    rh = (fy1 - fy0) / 4
    hx0 = fx0 + cw
    hy0 = fy0 + rh
    d.rectangle([hx0 + S * 0.01, hy0 + S * 0.01,
                 hx0 + cw - S * 0.01, hy0 + rh - S * 0.01], fill=HILITE)

    # 放大镜(查找差异)
    cx, cy, r = S * 0.60, S * 0.60, S * 0.175
    ring = max(2, int(S * 0.045))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=MAG_FILL,
              outline=MAG_RING, width=ring)
    # 手柄(指向右下角)
    hx, hy = S * 0.82, S * 0.82
    hw = max(2, int(S * 0.060))
    d.line([(cx + r * 0.72, cy + r * 0.72), (hx, hy)], fill=MAG_RING, width=hw)

    return img


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    assets = os.path.join(os.path.dirname(here), "assets")
    os.makedirs(assets, exist_ok=True)

    # 以高分辨率绘制，交由 Pillow 按 sizes 生成各档尺寸（更顺滑）
    hi = draw_icon(256)

    ico_path = os.path.join(assets, "app.ico")
    hi.save(ico_path, format="ICO", sizes=[(s, s) for s in SIZES])
    print("written:", ico_path)

    png_path = os.path.join(assets, "app.png")
    hi.save(png_path)
    print("written:", png_path)


if __name__ == "__main__":
    main()
