# -*- coding: utf-8 -*-
"""生成二次圈矿客户端图标 client/assets/app.ico。

画面含义：网格上的炮孔点阵 + 一条闭合的矿块边界圈住其中几个孔
——一眼能认出是"二次圈矿"工具。深板岩底 + 琥珀金矿块，
与汇总工具（蓝白）在任务栏上明显区分。
画在 1024 画布上再降采样；小尺寸自动省略网格线。
"""
from __future__ import annotations

import os

from PIL import Image, ImageChops, ImageDraw

CLIENT = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(CLIENT, "assets")
ICO_PATH = os.path.join(OUT_DIR, "app.ico")
PREVIEW_PATH = os.path.join(OUT_DIR, "icon_preview.png")

N = 256
TILE = (32, 47, 62, 255)        # 深板岩底
GRID = (74, 95, 116, 255)       # 1m 网格
ORE = (239, 159, 39, 255)       # 琥珀金：矿块
ORE_EDGE = (250, 199, 117, 255)  # 矿块边界
HOLE = (245, 248, 250, 255)     # 炮孔点

SIZES = [(256, 256), (128, 128), (64, 64), (48, 48), (40, 40),
         (32, 32), (24, 24), (20, 20), (16, 16)]

# 矿块边界（闭合多边形）
ORE_POLY = [(108, 58), (216, 74), (224, 140), (196, 190), (122, 182), (96, 120)]

# 炮孔点：前 4 个在矿块内，后 2 个在矿块外
HOLES = [(76, 92), (84, 158),                       # 块外
         (132, 80), (188, 96), (196, 164), (140, 148)]  # 块内


def draw_icon(supersample: int = 4, detail: bool = True) -> Image.Image:
    s = supersample
    size = N * s
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # 底板
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=56 * s, fill=TILE)

    # 1m 网格
    if detail:
        w = max(2, 5 * s)
        for p in (64, 128, 192):
            d.line([(p * s, 24 * s), (p * s, 232 * s)], fill=GRID, width=w)
            d.line([(24 * s, p * s), (232 * s, p * s)], fill=GRID, width=w)

    # 矿块：填充 + 边界
    poly = [(x * s, y * s) for x, y in ORE_POLY]
    d.polygon(poly, fill=ORE)
    d.line(poly + [poly[0]], fill=ORE_EDGE, width=max(2, 7 * s), joint="curve")

    # 炮孔点（画在矿块之上，块内的孔压在金色上）
    r = 11 * s
    for hx, hy in HOLES:
        d.ellipse([hx * s - r, hy * s - r, hx * s + r, hy * s + r], fill=HOLE)

    return img


def build() -> str:
    os.makedirs(OUT_DIR, exist_ok=True)
    draw_icon(4, True).resize((256, 256), Image.LANCZOS).save(ICO_PATH, format="ICO", sizes=SIZES)

    preview = Image.new("RGBA", (256 + 48 + 32 + 16 + 4 * 12, 256), (255, 255, 255, 255))
    x = 0
    for w in (256, 48, 32, 16):
        thumb = draw_icon(4, w >= 32).resize((w, w), Image.LANCZOS)
        preview.paste(thumb, (x, (256 - w) // 2), thumb)
        x += w + 12
    preview.save(PREVIEW_PATH)
    return ICO_PATH


if __name__ == "__main__":
    print("图标已生成：", build())
