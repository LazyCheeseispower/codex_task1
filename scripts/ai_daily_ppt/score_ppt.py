#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Score a generated AI daily deck against the quality spec.

Combines structural QA, content constraints, pixel metrics and brand-color
checks into one 0-100 report. This is the objective half of the scoring; the
human/MCP visual review notes are merged in afterwards.
"""

import argparse
import json
import math
import os
import sys

from PIL import Image, ImageStat
from pptx import Presentation


MAX_TITLE_CHARS = 26
MAX_SUMMARY_CHARS = 66
BRAND_BLUE = (0x15, 0x3C, 0x86)
ACCENT_BLUE = (0x29, 0x3F, 0x8E)


def dist_to_brand(px):
    dr = abs(px[0] - BRAND_BLUE[0]) + abs(px[1] - BRAND_BLUE[1]) + abs(px[2] - BRAND_BLUE[2])
    da = abs(px[0] - ACCENT_BLUE[0]) + abs(px[1] - ACCENT_BLUE[1]) + abs(px[2] - ACCENT_BLUE[2])
    return min(dr, da)


def pixel_metrics(render_dir, slides_meta):
    metrics = []
    total_dark = 0.0
    total_brand = 0.0
    total_px = 0
    ok = True
    for meta in slides_meta:
        i = meta["index"]
        path = os.path.join(render_dir, "Slide%d.PNG" % (i + 1))
        if not os.path.exists(path):
            path = os.path.join(render_dir, "Slide%d.png" % (i + 1))
        if not os.path.exists(path):
            metrics.append({"index": i, "missing": True})
            ok = False
            continue
        img = Image.open(path).convert("RGB")
        gray = img.convert("L")
        stat = ImageStat.Stat(gray)
        dark = 0
        brand = 0
        for px in img.getdata():
            lum = 0.299 * px[0] + 0.587 * px[1] + 0.114 * px[2]
            if lum < 120:
                dark += 1
            if dist_to_brand(px) < 120:
                brand += 1
        total_px += img.width * img.height
        total_dark += dark
        total_brand += brand
        dark_ratio = dark / (img.width * img.height)
        brand_ratio = brand / (img.width * img.height)
        card_std = None
        if meta["role"] == "content":
            crop = img.crop((int(img.width * 0.05), int(img.height * 0.18),
                             int(img.width * 0.95), int(img.height * 0.88)))
            card_std = ImageStat.Stat(crop.convert("L")).stddev[0]
        metrics.append({
            "index": i,
            "role": meta["role"],
            "stddev": stat.stddev[0],
            "dark_ratio": round(dark_ratio, 4),
            "brand_ratio": round(brand_ratio, 4),
            "card_std": round(card_std, 2) if card_std is not None else None,
        })
    return {
        "metrics": metrics,
        "avg_dark_ratio": round(total_dark / total_px, 4) if total_px else 0,
        "avg_brand_ratio": round(total_brand / total_px, 4) if total_px else 0,
        "ok": ok,
    }


def content_stats(content):
    chapters = content["chapters"]
    items = [item for ch in chapters for item in ch["items"]]
    long_titles = [it["title"] for it in items if len(it["title"]) > MAX_TITLE_CHARS]
    long_summaries = [it["title"] for it in items if len(it["summary"]) > MAX_SUMMARY_CHARS]
    missing_fields = []
    for it in items:
        for field in ("title", "summary", "source", "meta", "link"):
            if not str(it.get(field, "")).strip():
                missing_fields.append((it.get("title", ""), field))
    empty_statements = [ch["title"] for ch in chapters if not str(ch.get("statement", "")).strip()]
    dup_titles = len(items) - len({it["title"] for it in items})
    dup_summaries = len(items) - len({it["summary"] for it in items})
    return {
        "chapter_count": len(chapters),
        "item_count": len(items),
        "per_chapter_counts": [len(ch["items"]) for ch in chapters],
        "max_title_len": max((len(it["title"]) for it in items), default=0),
        "max_summary_len": max((len(it["summary"]) for it in items), default=0),
        "long_titles": long_titles,
        "long_summaries": long_summaries,
        "missing_fields": missing_fields,
        "empty_statements": empty_statements,
        "dup_titles": dup_titles,
        "dup_summaries": dup_summaries,
    }


def score_deck(qa, content, pixels):
    cs = content_stats(content)
    dims = {}

    # A. structure and logic (25)
    a = 0
    notes_a = []
    if qa.get("ok") and qa.get("slide_count") == qa.get("expected_count"):
        a += 10
    else:
        notes_a.append("slide count mismatch")
    roles = [s["role"] for s in qa.get("slides", [])]
    expected_roles = ["cover", "toc"]
    for _ in range(cs["chapter_count"]):
        expected_roles += ["divider", "chapter_toc", "content"]
    expected_roles.append("back")
    if roles == expected_roles:
        a += 7
    else:
        notes_a.append("slide role order mismatch")
    if 5 <= cs["chapter_count"] <= 6:
        a += 4
    else:
        notes_a.append("chapter count out of 5-6 range")
    if 12 <= cs["item_count"] <= 18:
        a += 4
    else:
        notes_a.append("item count %d outside 12-18" % cs["item_count"])
        a += max(0, 4 - abs(cs["item_count"] - 15))
    dims["structure"] = {"score": a, "max": 25, "notes": notes_a}

    # B. template fidelity (25)
    b = 0
    notes_b = []
    if qa.get("ok"):
        b += 12
    else:
        notes_b.append("structural QA issues")
    if cs["chapter_count"] >= 5:
        b += 4
    if cs["per_chapter_counts"] and max(cs["per_chapter_counts"]) <= 4:
        b += 4
    else:
        notes_b.append("a chapter exceeds 4 items")
    if pixels.get("avg_brand_ratio", 0) >= 0.01:
        b += 5
    else:
        notes_b.append("brand color presence below threshold")
    dims["template_fidelity"] = {"score": b, "max": 25, "notes": notes_b}

    # C. content quality (20)
    c = 0
    notes_c = []
    if not cs["long_titles"]:
        c += 6
    else:
        notes_c.append("titles exceed 26 chars: %s" % cs["long_titles"])
    if not cs["long_summaries"]:
        c += 6
    else:
        notes_c.append("summaries exceed 66 chars")
    if not cs["missing_fields"]:
        c += 4
    else:
        notes_c.append("missing item fields: %s" % cs["missing_fields"])
    if not cs["empty_statements"]:
        c += 2
    else:
        notes_c.append("empty chapter statements")
    if cs["dup_titles"] == 0 and cs["dup_summaries"] == 0:
        c += 2
    dims["content"] = {"score": c, "max": 20, "notes": notes_c}

    # D. visual readability (20)
    d = 0
    notes_d = []
    m = pixels["metrics"]
    if pixels["ok"] and len(m) == qa.get("slide_count"):
        d += 8
    nonblank = all(mm.get("stddev", 0) >= 6 for mm in m)
    readable = all(0.001 <= mm.get("dark_ratio", 0) <= 0.4 for mm in m)
    if nonblank:
        d += 4
    if readable:
        d += 4
    else:
        notes_d.append("some slides too sparse or too dense")
    flat_cards = [mm for mm in m if mm.get("card_std") is not None and mm["card_std"] < 12]
    if not flat_cards:
        d += 4
    else:
        notes_d.append("flat card regions on %d content slides" % len(flat_cards))
    dims["visual"] = {"score": d, "max": 20, "notes": notes_d}

    # E. render integrity (10)
    e = 0
    notes_e = []
    if pixels["ok"]:
        e += 4
    else:
        notes_e.append("missing rendered slides")
    if len(m) == qa.get("slide_count"):
        e += 3
    if pixels.get("unique") == qa.get("slide_count"):
        e += 3
    else:
        notes_e.append("duplicate renders found")
    dims["render"] = {"score": e, "max": 10, "notes": notes_e}

    total = sum(d["score"] for d in dims.values())
    notes_all = [n for d in dims.values() for n in d["notes"]]
    return {
        "total": total,
        "max": 100,
        "dimensions": dims,
        "notes": notes_all,
        "content_stats": cs,
        "pixel_summary": {
            "avg_dark_ratio": pixels["avg_dark_ratio"],
            "avg_brand_ratio": pixels["avg_brand_ratio"],
            "unique_renders": pixels.get("unique", 0),
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pptx", required=True)
    ap.add_argument("--content", required=True)
    ap.add_argument("--qa", required=True)
    ap.add_argument("--render-dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    with open(args.content, encoding="utf-8") as f:
        content = json.load(f)
    with open(args.qa, encoding="utf-8") as f:
        qa = json.load(f)

    prs = Presentation(args.pptx)
    pixels = pixel_metrics(args.render_dir, qa.get("slides", []))
    # uniqueness of rendered slides
    hashes = []
    for mm in pixels["metrics"]:
        path = os.path.join(args.render_dir, "Slide%d.PNG" % (mm["index"] + 1))
        if not os.path.exists(path):
            path = os.path.join(args.render_dir, "Slide%d.png" % (mm["index"] + 1))
        if os.path.exists(path):
            with open(path, "rb") as fh:
                import hashlib
                hashes.append(hashlib.md5(fh.read()).hexdigest())
    pixels["unique"] = len(set(hashes))

    report = score_deck(qa, content, pixels)
    report["pptx"] = args.pptx
    report["slide_count"] = qa.get("slide_count")
    report["brand_colors"] = {"primary": "#153C86", "accent": "#293F8E"}
    report["pixel_summary"]["metrics"] = pixels["metrics"]
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("SCORE %d/100" % report["total"])
    for name, dim in report["dimensions"].items():
        print("  %-16s %2d/%2d" % (name, dim["score"], dim["max"]))
    print("avg dark ratio=%s avg brand ratio=%s unique=%s" % (
        pixels["avg_dark_ratio"], pixels["avg_brand_ratio"], pixels["unique"]))


if __name__ == "__main__":
    main()
