#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate branded placeholder assets for the AI daily brief.

These are local concept visuals used until real imagegen assets are enabled.
They share the Zhende blue palette, contain only short labels, and stay
deliberately free of real company logos.
"""

import argparse
import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont


BRAND = (21, 60, 134)
ACCENT = (41, 63, 142)
LIGHT = (232, 239, 250)
WHITE = (255, 255, 255)
STEEL = (148, 170, 205)
CYAN = (120, 190, 220)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def blend(a, b, alpha):
    return tuple(int(a[i] * (1 - alpha) + b[i] * alpha) for i in range(3))


def load_font(size):
    candidates = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/msyhbd.ttc",
        "C:/Windows/Fonts/simhei.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def gradient_base(w, h):
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        color = lerp(BRAND, ACCENT, t)
        for x in range(w):
            px[x, y] = color
    return img


def radial_glow(draw, w, h, cx, cy, radius, color, alpha):
    for r in range(radius, 0, -8):
        a = int(alpha * (1 - r / radius) ** 1.6)
        draw.ellipse(
            (cx - r, cy - r, cx + r, cy + r),
            fill=color + (a,),
        )


def circuit_trace(draw, w, h, seed):
    rng = random.Random(seed)
    x = rng.randint(80, 220)
    y = rng.randint(80, h - 120)
    points = [(x, y)]
    while x < w - 60:
        step = rng.choice([70, 110, 150])
        if rng.random() < 0.55:
            x += step
        else:
            x += step // 2
            y += rng.choice([-90, -45, 45, 90])
            y = max(70, min(h - 70, y))
        points.append((x, y))
    draw.line(points, fill=blend(WHITE, BRAND, 0.12), width=4)
    for px, py in points:
        draw.ellipse((px - 5, py - 5, px + 5, py + 5), fill=CYAN)


def render_asset(out_path, w, h, label, number, seed):
    img = gradient_base(w, h)
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    radial_glow(draw, w, h, int(w * 0.18), int(h * 0.16),
                int(w * 0.55), LIGHT, 62)
    radial_glow(draw, w, h, int(w * 0.86), int(h * 0.12),
                int(w * 0.42), CYAN, 34)

    for gx in range(0, w, 90):
        draw.line((gx, 0, gx, h), fill=WHITE + (16,), width=2)
    for gy in range(0, h, 90):
        draw.line((0, gy, w, gy), fill=WHITE + (14,), width=2)

    draw.polygon(
        [(int(w * 0.55), h), (w, int(h * 0.42)), (w, h)],
        fill=WHITE + (24,),
    )
    draw.polygon(
        [(int(w * 0.62), h), (w, int(h * 0.55)), (w, h)],
        fill=STEEL + (24,),
    )

    panel = int(min(w, h) * 0.24)
    draw.rounded_rectangle(
        (int(w * 0.06), int(h * 0.62), int(w * 0.06) + panel, int(h * 0.62) + panel),
        radius=18, fill=WHITE + (30,), outline=WHITE + (80,), width=2,
    )
    draw.rounded_rectangle(
        (int(w * 0.70), int(h * 0.16), int(w * 0.70) + int(panel * 0.7),
         int(h * 0.16) + int(panel * 0.7)),
        radius=14, fill=WHITE + (22,), outline=STEEL + (90,), width=2,
    )
    draw.rounded_rectangle(
        (int(w * 0.56), int(h * 0.68), int(w * 0.56) + int(panel * 0.56),
         int(h * 0.68) + int(panel * 0.56)),
        radius=12, fill=CYAN + (36,), outline=WHITE + (70,), width=2,
    )

    rng = random.Random(seed + 7)
    for _ in range(5):
        cx = rng.randint(80, w - 80)
        cy = rng.randint(70, h - 90)
        radius = rng.randint(30, 90)
        draw.arc(
            (cx - radius, cy - radius, cx + radius, cy + radius),
            start=rng.randint(0, 180), end=rng.randint(200, 340),
            fill=WHITE + (70,), width=3,
        )

    circuit_trace(draw, w, h, seed)
    rng = random.Random(seed + 11)
    for _ in range(700):
        x = rng.randint(0, w - 1)
        y = rng.randint(0, h - 1)
        color = rng.choice([WHITE, LIGHT, STEEL, CYAN]) + (rng.randint(24, 52),)
        r = rng.randint(1, 3)
        draw.ellipse((x, y, x + r, y + r), fill=color)

    img = Image.alpha_composite(img.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(img)
    font_big = load_font(int(min(w, h) * 0.045))
    font_num = load_font(int(min(w, h) * 0.075))
    draw.text((int(w * 0.07), int(h * 0.80)), label, font=font_big, fill=WHITE)
    draw.text((int(w * 0.07), int(h * 0.855)), number, font=font_num, fill=CYAN)

    img = img.filter(ImageFilter.GaussianBlur(0.4))
    img.convert("RGB").save(out_path, "PNG", optimize=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="assets directory for the date")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    chapters = ["模型与发布", "产品与工具", "行业与公司", "政策与观点"]
    for idx, label in enumerate(chapters, start=1):
        render_asset(
            os.path.join(args.out, "chapter_%02d.png" % idx),
            1600, 900, label, "%02d" % idx, seed=idx,
        )
    for idx in range(1, 9):
        render_asset(
            os.path.join(args.out, "item_%02d.png" % idx),
            1200, 900, "AI 品牌配图", "%02d" % idx, seed=idx + 40,
        )
    print("generated 12 placeholder assets in %s" % args.out)


if __name__ == "__main__":
    main()
