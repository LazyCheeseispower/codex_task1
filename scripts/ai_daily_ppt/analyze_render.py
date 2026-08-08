#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Print a coarse color grid and dominant palette for rendered slides.

Useful for understanding template backgrounds without relying on vision:
sample a 12x7 grid of pixel colors and list the top quantized colors.
"""

import argparse
import os

from PIL import Image


def quantize(px):
    return tuple((v // 16) * 16 for v in px)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--slides", required=True)
    args = ap.parse_args()
    wanted = [int(x) for x in args.slides.split(",") if x.strip()]
    for slide_no in wanted:
        path = os.path.join(args.dir, "Slide%d.PNG" % slide_no)
        if not os.path.exists(path):
            path = os.path.join(args.dir, "Slide%d.png" % slide_no)
        img = Image.open(path).convert("RGB")
        w, h = img.size
        print("=== slide %d (%dx%d) ===" % (slide_no, w, h))
        for gy in range(7):
            y = int((gy + 0.5) * h / 7)
            row = []
            for gx in range(12):
                x = int((gx + 0.5) * w / 12)
                row.append("#%02X%02X%02X" % img.getpixel((x, y)))
            print(" ".join(row))
        small = img.resize((96, 54))
        counts = {}
        for px in small.getdata():
            key = quantize(px)
            counts[key] = counts.get(key, 0) + 1
        total = 96 * 54
        top = sorted(counts.items(), key=lambda kv: -kv[1])[:10]
        print("palette:", ", ".join("#%02X%02X%02X %.1f%%" % (c[0], c[1], c[2], n * 100.0 / total) for c, n in top))


if __name__ == "__main__":
    main()
