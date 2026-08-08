#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OCR-backed layout QA for rendered slides.

Reads the geometry report from inspect_ppt.py, the OCR word boxes from
ocr_slides.ps1 and the role report from qa_ppt.py, then verifies rendered
text stays inside its text frame and inside the surrounding preview card or
key-point panel.  Coverage warnings are tolerated; hard issues are not.
"""

import argparse
import json
import re
import sys


SCALE = 96.0  # 13.333in x 7.5in -> 1280 x 720 PNG
TOL = 10  # px
COVERAGE_NAMES = {
    "文本框 12", "文本框 13", "文本框 1", "文本框 3",
    "TextBox 2", "TextBox 3", "TextBox 4", "TextBox 6",
    "chapter_chip_text", "chapter_page_footer",
    "chapter_preview_1_title", "chapter_preview_1_summary",
    "chapter_preview_2_title", "chapter_preview_2_summary",
    "page_kicker", "page_title", "detail_chip_text", "detail_title",
    "detail_summary", "detail_impact", "detail_source",
    "detail_image_caption",
}


def norm(text):
    return re.sub(r"[\W_]+", "", text)


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


def rect_overlap(a, b):
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ox = min(ax1, bx1) - max(ax0, bx0)
    oy = min(ay1, by1) - max(ay0, by0)
    if ox <= 0 or oy <= 0:
        return 0.0
    return ox * oy


def scale_rect(rect_in):
    return (
        rect_in["left"] * SCALE,
        rect_in["top"] * SCALE,
        (rect_in["left"] + rect_in["width"]) * SCALE,
        (rect_in["top"] + rect_in["height"]) * SCALE,
    )


def words_for_slide(ocr_slide):
    words = []
    for line in ocr_slide.get("lines", []):
        words.extend(line.get("words", []))
    return words


def check_container(words, container_rect, label, idx, issues):
    expanded_rect = expanded(container_rect, TOL)
    for word in words:
        wb = word_box(word)
        cx = (wb[0] + wb[2]) / 2.0
        cy = (wb[1] + wb[3]) / 2.0
        if center_in(container_rect, cx, cy) and not contains(expanded_rect, wb):
            issues.append(
                "slide %d: %r text %r spills out of region (%d,%d %dx%d)"
                % (idx + 1, label, word["text"], wb[0], wb[1], wb[2] - wb[0], wb[3] - wb[1])
            )


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

    ocr_by_slide = {}
    for item in ocr:
        try:
            ocr_by_slide[int(item["slide"]) - 1] = item
        except (KeyError, ValueError):
            continue
    roles = {item["index"]: item["role"] for item in qa.get("slides", [])}
    issues = []
    warnings = []

    for slide_meta in inspect["slides"]:
        idx = slide_meta["index"]
        ocr_slide = ocr_by_slide.get(idx)
        if ocr_slide is None:
            issues.append("slide %d has no OCR data" % (idx + 1))
            continue
        words = words_for_slide(ocr_slide)
        if not words:
            issues.append("slide %d OCR found no words" % (idx + 1))
            continue

        shapes = slide_meta.get("shapes", [])
        text_shapes = [
            sh for sh in shapes
            if sh.get("text_frame") and sh["text_frame"].get("text")
        ]
        containers = []
        images = []
        for sh in shapes:
            name = sh["name"]
            if name in ("chapter_image", "detail_image"):
                images.append(sh)
            if name.startswith("chapter_preview_") and not name.endswith(
                ("_title", "_summary", "_badge", "_badge_text")
            ):
                containers.append((name, sh))
            elif name == "detail_kp_bg":
                containers.append((name, sh))

        for sh in text_shapes:
            rect = scale_rect(sh["rect"])
            for word in words:
                wb = word_box(word)
                cx = (wb[0] + wb[2]) / 2.0
                cy = (wb[1] + wb[3]) / 2.0
                if center_in(rect, cx, cy) and not contains(expanded(rect, TOL), wb):
                    issues.append(
                        "slide %d: %r word %r spills out of frame (%d,%d %dx%d)"
                        % (idx + 1, sh["name"], word["text"], wb[0], wb[1],
                           wb[2] - wb[0], wb[3] - wb[1])
                    )

        for name, sh in containers:
            check_container(words, scale_rect(sh["rect"]), name, idx, issues)

        image_rects = [scale_rect(sh["rect"]) for sh in images]
        for sh in text_shapes:
            rect = scale_rect(sh["rect"])
            for image_rect in image_rects:
                overlap = rect_overlap(rect, image_rect)
                if overlap > 8 * 8:
                    issues.append(
                        "slide %d: text %r overlaps image area (%.0f px^2)"
                        % (idx + 1, sh["name"], overlap)
                    )

        for sh in text_shapes:
            name = sh["name"]
            if name not in COVERAGE_NAMES:
                continue
            rect = scale_rect(sh["rect"])
            inside = "".join(
                word["text"] for word in words
                if center_in(rect, (word_box(word)[0] + word_box(word)[2]) / 2.0,
                             (word_box(word)[1] + word_box(word)[3]) / 2.0)
            )
            expected = norm(sh["text_frame"]["text"])
            recognized = norm(inside)
            if not expected:
                continue
            matched = 0
            pos = 0
            for ch in recognized:
                found = expected.find(ch, pos)
                if found >= 0:
                    matched += 1
                    pos = found + 1
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
