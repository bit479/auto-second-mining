"""生成程序图标 assets/app.ico。

画面含义：漏斗（多份数据汇入）+ 表格（汇成一张表）——一眼能认出是数据处理/汇总工具。
画在 1024 画布上再降采样，保证各尺寸都平滑；小尺寸自动省略内部细节。
"""

from __future__ import annotations

import os

from PIL import Image, ImageChops, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "assets")
ICO_PATH = os.path.join(OUT_DIR, "app.ico")
PREVIEW_PATH = os.path.join(OUT_DIR, "icon_preview.png")

N = 256                      # 设计坐标系
BLUE = (24, 95, 165, 255)    # #185FA5
WHITE = (255, 255, 255, 255)

SIZES = [(256, 256), (128, 128), (64, 64), (48, 48), (40, 40),
         (32, 32), (24, 24), (20, 20), (16, 16)]


def _rr(draw, box, radius, fill):
    draw.rounded_rectangle(box, radius=radius, fill=fill)


def draw_icon(supersample: int = 4, detail: bool = True) -> Image.Image:
    s = supersample
    size = N * s
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # 底板：圆角方块
    _rr(d, [0, 0, size - 1, size - 1], radius=56 * s, fill=BLUE)

    # 漏斗：多份数据汇入
    funnel = [(56, 28), (200, 28), (144, 106), (144, 128), (112, 128), (112, 106)]
    d.polygon([(x * s, y * s) for x, y in funnel], fill=WHITE)
    if detail:
        # 漏斗里的数据行
        for x0, x1, y in ((84, 172, 50), (104, 152, 76)):
            _rr(d, [x0 * s, y * s, x1 * s, (y + 12) * s], radius=6 * s, fill=BLUE)

    # 表格：汇总成一张表
    sheet = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sheet)
    sd.rectangle([48 * s, 136 * s, 208 * s, 216 * s], fill=WHITE)
    sd.rectangle([48 * s, 136 * s, 208 * s, 168 * s], fill=BLUE)   # 表头带
    if detail:
        w = max(2, 6 * s)
        sd.line([(101 * s, 168 * s), (101 * s, 216 * s)], fill=BLUE, width=w)
        sd.line([(155 * s, 168 * s), (155 * s, 216 * s)], fill=BLUE, width=w)
        sd.line([(48 * s, 192 * s), (208 * s, 192 * s)], fill=BLUE, width=w)

    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [48 * s, 136 * s, 208 * s, 216 * s], radius=16 * s, fill=255)
    sheet.putalpha(ImageChops.multiply(sheet.split()[3], mask))

    img = Image.alpha_composite(img, sheet)
    return img


def build() -> str:
    os.makedirs(OUT_DIR, exist_ok=True)

    big = draw_icon(supersample=4, detail=True).resize((256, 256), Image.LANCZOS)
    big.save(ICO_PATH, format="ICO", sizes=SIZES)

    # 预览图：256 / 48 / 32 / 16 并排，便于人工检查小尺寸是否还认得出
    preview = Image.new("RGBA", (256 + 48 + 32 + 16 + 4 * 12, 256), (255, 255, 255, 255))
    x = 0
    for w in (256, 48, 32, 16):
        thumb = draw_icon(supersample=4, detail=w >= 32).resize((w, w), Image.LANCZOS)
        preview.paste(thumb, (x, (256 - w) // 2), thumb)
        x += w + 12
    preview.save(PREVIEW_PATH)

    return ICO_PATH


if __name__ == "__main__":
    print("图标已生成：", build())
