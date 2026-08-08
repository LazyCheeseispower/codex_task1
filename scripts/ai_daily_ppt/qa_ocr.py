#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OCR-backed layout QA for rendered slides.

Reads the geometry report from inspect_ppt.py and the OCR word boxes from
ocr_slides.ps1, then verifies that rendered text stays inside its expected
frame and inside the surrounding card. This catches clipping, spill-over and
text that visually collides with neighbouring regions.
"""

import argparse
import json
import re
import sys


SCALE = 96.0  # 13.333in x 7.5in -> 1280 x 720 PNG
TOL = 10  # px


def norm(text):
    return re.sub(r"[\s·—\-_（）()【】《》「」『』:：,，。；;！？!?\"'“”‘’]", "", text)


def word_box(word):
    return (word["x"], word["y"], word["x"] + word["w"], word["y"] + word["h"])


def center_in(rect, cx, cy):
    x0, y0, x1, y1 = rect
    return x0 <= cx <= x1 and y0 <= cy <= y1


def expanded(rect, tol):
    x0, y0, x1, y1 = rect
    return (x0 - tol, y0 - tol, x1 + tol, y1 + tol)


def contains(outer, inner, tol=0):
    ox0, oy0, ox1, oy1 = outer
    ix0, iy0, ix1, iy1 = inner
    return ox0 - tol <= ix0 and oy0 - tol <= iy0 and ix1 <= ox1 + tol and iy1 <= oy1 + tol


def scale_rect(rect_in):
    return (
        rect_in["left"] * SCALE,
        rect_in["top"] * SCALE,
        (rect_in["left"] + rect_in["width"]) * SCALE,
        (rect_in["top"] + rect_in["height"]) * SCALE,
    )


def text_shape_names(slide_shapes):
    names = set()
    for sh in slide_shapes:
        tf = sh.get("text_frame")
        if tf and tf.get("text"):
            names.add(sh["name"])
    return names


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inspect", required=True)
    ap.add_argument("--ocr", required=True)
    ap.add_argument("--qa", required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()

    with open(args.inspect, encoding="utf-8") as f:
        inspect = json.load(f)
    with open(args.ocr, encoding="utf-8") as f:
        ocr = json.load(f)
    with open(args.qa, encoding="utf-8") as f:
        qa = json.load(f)

    ocr_by_slide = {int(item["slide"]) - 1: item for item in ocr}
    roles = {item["index"]: item["role"] for item in qa.get("slides", [])}
    issues = []
    warnings = []

    for slide_meta in inspect["slides"]:
        idx = slide_meta["index"]
        ocr_slide = ocr_by_slide.get(idx)
        if ocr_slide is None:
            issues.append("slide %d has no OCR data" % (idx + 1))
            continue
        words = []
        for line in ocr_slide.get("lines", []):
            words.extend(line.get("words", []))
        if not words:
            issues.append("slide %d OCR found no words" % (idx + 1))
            continue

        shapes = slide_meta["shapes"]
        shape_rects = {}
        for sh in shapes:
            tf = sh.get("text_frame")
            if tf and tf.get("text"):
                shape_rects[sh["name"]] = scale_rect(sh["rect"])

        for sh in shapes:
            tf = sh.get("text_frame")
            if not tf or not tf.get("text"):
                continue
            rect = scale_rect(sh["rect"])
            for word in words:
                bx0, by0, bx1, by1 = word_box(word)
                cx = (bx0 + bx1) / 2.0
                cy = (by0 + by1) / 2.0
                if center_in(rect, cx, cy) and not contains(expanded(rect, TOL), (bx0, by0, bx1, by1)):
                    issues.append(
                        "slide %d: %r word %r spills out of frame (word %d,%d %dx%d)"
                        % (idx + 1, sh["name"], word["text"], bx0, by0, bx1 - bx0, by1 - by0)
                    )

        if roles.get(idx) == "content":
            for sh in shapes:
                name = sh["name"]
                if not name.startswith("card_") or name.endswith(("_title", "_summary", "_meta", "_chip", "_chip_text", "_accent")):
                    continue
                card_rect = scale_rect(sh["rect"])
                for word in words:
                    bx0, by0, bx1, by1 = word_box(word)
                    cx = (bx0 + bx1) / 2.0
                    cy = (by0 + by1) / 2.0
                    if center_in(card_rect, cx, cy) and not contains(expanded(card_rect, TOL), (bx0, by0, bx1, by1)):
                        issues.append(
                            "slide %d: card %r text %r spills out of card (%d,%d %dx%d)"
                            % (idx + 1, name, word["text"], bx0, by0, bx1 - bx0, by1 - by0)
                        )

        # Coverage per generated text frame, so missing glyphs/OCR failures surface.
        for sh in shapes:
            tf = sh.get("text_frame")
            if not tf or not tf.get("text"):
                continue
            name = sh["name"]
            if not (name.startswith("card_") or name in ("page_title", "page_kicker")):
                continue
            rect = shape_rects[name]
            inside = "".join(
                word["text"] for word in words
                if center_in(rect, (word_box(word)[0] + word_box(word)[2]) / 2.0,
                             (word_box(word)[1] + word_box(word)[3]) / 2.0)
            )
            expected = norm(tf["text"])
            recognized = norm(inside)
            if not expected:
                continue
            matched = 0
            pos = 0
            for ch in recognized:
                idx2 = expected.find(ch, pos)
                if idx2 >= 0:
                    matched += 1
                    pos = idx2 + 1
            ratio = matched / len(expected)
            if ratio < 0.55:
                warnings.append(
                    "slide %d: OCR coverage low for %r (%.0f%%): expected=%s recognized=%s"
                    % (idx + 1, name, ratio * 100, expected, recognized)
                )

    report = {
        "ok": not issues,
        "issues": issues,
        "warnings": warnings,
    }
    with open(args.report, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("OCR QA: issues=%d warnings=%d" % (len(issues), len(warnings)))
    for issue in issues[:60]:
        print(" -", issue)
    for warning in warnings[:30]:
        print(" ?", warning)
    if issues:
        sys.exit(1)


if __name__ == "__main__":
    main()
