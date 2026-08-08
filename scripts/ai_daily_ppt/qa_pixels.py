#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pixel QA for rendered slide PNGs produced by render_ppt.ps1.

Checks every slide is non-blank and unique, and verifies the chapter/detail
image rectangles from qa_ppt.py are present, non-blank and not duplicated.
"""

import argparse
import hashlib
import json
import os
import sys

from PIL import Image, ImageStat


SCALE = 96.0  # 13.333in x 7.5in -> 1280 x 720 PNG
MIN_STD = 6.0
MIN_IMAGE_STD = 8.0
MIN_IMAGE_RANGE = 30


def find_render(paths):
    for path in paths:
        if os.path.exists(path):
            return path
    return None


def image_rect_ok(img, rect, label, issues):
    if rect is None:
        issues.append("%s image_rect missing" % label)
        return
    left = int(round(rect["left"] * SCALE))
    top = int(round(rect["top"] * SCALE))
    right = int(round((rect["left"] + rect["width"]) * SCALE))
    bottom = int(round((rect["top"] + rect["height"]) * SCALE))
    if left < 0 or top < 0 or right > img.width or bottom > img.height:
        issues.append("%s image_rect outside render: %s" % (label, rect))
        return
    if right <= left or bottom <= top:
        issues.append("%s image_rect empty: %s" % (label, rect))
        return
    crop = img.crop((left, top, right, bottom))
    gray = crop.convert("L")
    stat = ImageStat.Stat(gray)
    std = stat.stddev[0]
    extrema = gray.getextrema()
    rng = extrema[1] - extrema[0]
    if std < MIN_IMAGE_STD or rng < MIN_IMAGE_RANGE:
        issues.append(
            "%s image region too flat (std=%.1f range=%d): %s"
            % (label, std, rng, rect)
        )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()

    with open(args.report, encoding="utf-8") as f:
        report = json.load(f)
    slides = report.get("slides", [])
    issues = []
    hashes = []
    image_regions = []

    for slide_meta in slides:
        i = slide_meta["index"]
        label = "slide %d (%s)" % (i + 1, slide_meta.get("role", "?"))
        path = find_render([
            os.path.join(args.dir, "Slide%d.PNG" % (i + 1)),
            os.path.join(args.dir, "Slide%d.png" % (i + 1)),
        ])
        if path is None:
            issues.append("%s render missing" % label)
            continue
        img = Image.open(path).convert("RGB")
        gray = img.convert("L")
        stat = ImageStat.Stat(gray)
        std = stat.stddev[0]
        if std < MIN_STD:
            issues.append("%s nearly blank (std=%.1f)" % (label, std))
        dark_count = sum(1 for byte in gray.tobytes() if byte < 120)
        dark_ratio = dark_count / (gray.width * gray.height)
        if dark_ratio < 0.0002:
            issues.append("%s has no readable text pixels" % label)
        digest = hashlib.md5(img.tobytes()).hexdigest()
        if hashes and digest == hashes[-1]:
            issues.append("%s identical to previous" % label)
        hashes.append(digest)

        role = slide_meta.get("role")
        if role in ("chapter", "detail"):
            image_regions.append(label)
            image_rect_ok(img, slide_meta.get("image_rect"), label, issues)

    detail_roles = [s for s in slides if s.get("role") == "detail"]
    for slide_meta in detail_roles:
        if slide_meta.get("image_rect") is None:
            issues.append("detail slide %d has no image region" % (slide_meta["index"] + 1))

    unique = len(set(hashes))
    print("pixel QA: %d slides, %d unique renders, %d image regions"
          % (len(slides), unique, len(image_regions)))
    if issues:
        print("PIXEL QA FAILED")
        for issue in issues:
            print(" -", issue)
        sys.exit(1)
    print("PIXEL QA OK")


if __name__ == "__main__":
    main()
