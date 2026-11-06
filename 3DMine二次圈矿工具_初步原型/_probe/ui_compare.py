# -*- coding: utf-8 -*-
"""生成 v1.15 → v1.16 关键页面对比图（上：改造前，下：改造后）。"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SHOT = ROOT / "docs" / "screenshots" / "v1.16"
W = 1600
BAR = 44
GAP = 14
FONT = "C:/Windows/Fonts/msyh.ttc"


def label(width: int, text: str, fg: str, bg: str) -> Image.Image:
    img = Image.new("RGB", (width, BAR), bg)
    d = ImageDraw.Draw(img)
    try:
        f = ImageFont.truetype(FONT, 20)
    except OSError:
        f = ImageFont.load_default()
    d.text((18, 11), text, font=f, fill=fg)
    return img


def build(name: str, title: str) -> Path:
    before = Image.open(SHOT / "before" / ("%s.png" % name)).convert("RGB")
    after = Image.open(SHOT / "after" / ("%s.png" % name)).convert("RGB")
    bh = int(before.height * W / before.width)
    ah = int(after.height * W / after.width)
    before = before.resize((W, bh), Image.LANCZOS)
    after = after.resize((W, ah), Image.LANCZOS)

    total = BAR + bh + GAP + BAR + ah
    canvas = Image.new("RGB", (W, total), "#E9EDF2")
    y = 0
    canvas.paste(label(W, "%s · 改造前（v1.15）" % title, "#5A6675", "#DDE3EA"), (0, y))
    y += BAR
    canvas.paste(before, (0, y))
    y += bh + GAP
    canvas.paste(label(W, "%s · 改造后（v1.16）" % title, "#EAF4FC", "#0E1B2A"), (0, y))
    y += BAR
    canvas.paste(after, (0, y))

    out = SHOT / ("对比_%s.png" % name)
    canvas.save(out)
    return out


if __name__ == "__main__":
    for key, title in (("dashboard", "工作台"), ("single", "单炮区二次圈矿"),
                       ("batch", "批量处理")):
        print(build(key, title))
