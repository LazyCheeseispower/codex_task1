#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pixel QA for rendered slide PNGs produced by render_ppt.ps1."""

import argparse
import hashlib
import json
import os
import sys

from PIL import Image, ImageStat


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()

    with open(args.report, encoding="utf-8") as f:
        report = json.load(f)
    slides = report["slides"]
    issues = []
    hashes = []

    for slide_meta in slides:
        i = slide_meta["index"]
        path = os.path.join(args.dir, "Slide%d.PNG" % (i + 1))
        if not os.path.exists(path):
            path = os.path.join(args.dir, "Slide%d.png" % (i + 1))
        if not os.path.exists(path):
            issues.append("slide %d render missing" % (i + 1))
            continue
        img = Image.open(path).convert("RGB")
        gray = img.convert("L")
        stat = ImageStat.Stat(gray)
        std = stat.stddev[0]
        if std < 6:
            issues.append("slide %d nearly blank (std=%.1f)" % (i + 1, std))
        dark_count = 0
        for px in gray.getdata():
            if px < 120:
                dark_count += 1
        dark_ratio = dark_count / (gray.width * gray.height)
        if dark_ratio < 0.0002:
            issues.append("slide %d has no readable text pixels" % (i + 1))
        digest = hashlib.md5(img.tobytes()).hexdigest()
        if hashes and digest == hashes[-1]:
            issues.append("slide %d identical to previous" % (i + 1))
        hashes.append(digest)

        if slide_meta["role"] == "content":
            crop = img.crop((
                int(img.width * 0.05), int(img.height * 0.18),
                int(img.width * 0.95), int(img.height * 0.88),
            ))
            crop_stat = ImageStat.Stat(crop.convert("L"))
            if crop_stat.stddev[0] < 12:
                issues.append("content slide %d card region too flat" % (i + 1))

    unique = len(set(hashes))
    print("pixel QA: %d slides, %d unique renders" % (len(slides), unique))
    if issues:
        print("PIXEL QA FAILED")
        for issue in issues:
            print(" -", issue)
        sys.exit(1)
    print("PIXEL QA OK")


if __name__ == "__main__":
    main()
