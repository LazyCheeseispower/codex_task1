#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Structural QA for generated AI daily briefs.

Checks deck structure, template fidelity, text limits, shape bounds and that
every expected card exists. Writes a machine-readable report used by the pixel
QA step.
"""

import argparse
import json
import math
import sys

from pptx import Presentation
from pptx.util import Emu, Inches


MAX_CHAPTERS = 6
MAX_ITEMS_PER_CHAPTER = 4
MAX_TITLE_CHARS = 26
MAX_SUMMARY_CHARS = 66


def est_lines(text, size_pt, width_in):
    width = 0.0
    cjk = size_pt / 72.0
    latin = cjk * 0.52
    for ch in text:
        if ord(ch) > 0x2E80 or ch in "，。：；！？·、（）「」—":
            width += cjk
        else:
            width += latin
    return max(1, math.ceil(width / max(width_in, 0.1)))


def shape_text(shape):
    if not shape.has_text_frame:
        return ""
    return shape.text_frame.text.strip()


def check_bounds(shape, slide_w, slide_h, issues, where):
    left = shape.left if shape.left is not None else 0
    top = shape.top if shape.top is not None else 0
    width = shape.width if shape.width is not None else 0
    height = shape.height if shape.height is not None else 0
    tol = Inches(0.02)
    if left < -tol or top < -tol or left + width > slide_w + tol or top + height > slide_h + tol:
        issues.append("%s shape %r out of bounds" % (where, shape.name))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pptx", required=True)
    ap.add_argument("--content", required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()

    with open(args.content, encoding="utf-8") as f:
        content = json.load(f)
    chapters = content["chapters"]
    prs = Presentation(args.pptx)
    slide_w = prs.slide_width
    slide_h = prs.slide_height
    issues = []

    expected_pages = 2  # cover + global toc
    for chapter in chapters:
        expected_pages += 2  # divider + chapter toc
        expected_pages += math.ceil(len(chapter["items"]) / MAX_ITEMS_PER_CHAPTER)
    expected_pages += 1  # back cover

    slides = list(prs.slides)
    if len(slides) != expected_pages:
        issues.append("slide count %d != expected %d" % (len(slides), expected_pages))

    report_slides = []
    idx = 0

    def record(role, cards=None):
        nonlocal idx
        report_slides.append({
            "index": idx,
            "role": role,
            "cards": cards,
        })
        idx += 1

    if len(slides) >= 1:
        cover = slides[0]
        if shape_text(find(cover, "文本框 12")) != content["meta"]["title"]:
            issues.append("cover title mismatch")
        if shape_text(find(cover, "文本框 13")) != content["meta"]["publisher"]:
            issues.append("cover publisher mismatch")
        if not shape_text(find(cover, "文本框 1")):
            issues.append("cover date empty")
        table = find(cover, "表格 7").table
        for (row, col) in [(0, 1), (0, 3), (1, 1), (1, 3), (2, 1), (2, 3)]:
            if not table.cell(row, col).text.strip():
                issues.append("cover table cell (%d,%d) empty" % (row, col))
        record("cover")

    if len(slides) >= 2:
        toc = slides[1]
        boxes = ["TextBox 2", "TextBox 3", "TextBox 4", "TextBox 6", "TextBox 7", "TextBox 8"]
        for box_no, chapter in zip(boxes, chapters):
            box = find(toc, box_no)
            if box is None or chapter["title"] not in shape_text(box):
                issues.append("global toc missing %s" % chapter["title"])
        if len(chapters) < len(boxes) and find(toc, boxes[len(chapters)]) is not None:
            issues.append("unused global toc box should be removed")
        record("toc")

    for chapter_no, chapter in enumerate(chapters, start=1):
        if idx >= len(slides):
            issues.append("missing divider for %s" % chapter["title"])
            break
        divider = slides[idx]
        number_box = find(divider, "TextBox 1")
        if number_box is None:
            number_box = find(divider, "TextBox 5")
        if shape_text(number_box) != "%02d" % chapter_no:
            issues.append("divider number wrong for %s" % chapter["title"])
        if shape_text(find(divider, "TextBox 4")) != chapter["title"]:
            issues.append("divider title wrong for %s" % chapter["title"])
        if not shape_text(find(divider, "TextBox 6")):
            issues.append("divider statement empty for %s" % chapter["title"])
        record("divider")

        if idx >= len(slides):
            issues.append("missing chapter toc for %s" % chapter["title"])
            break
        toc = slides[idx]
        if shape_text(find(toc, "TextBox 17")) != "%02d" % chapter_no:
            issues.append("chapter toc number wrong for %s" % chapter["title"])
        if shape_text(find(toc, "TextBox 15")) != chapter["title"]:
            issues.append("chapter toc title wrong for %s" % chapter["title"])
        agenda_names = ["agenda_01", "agenda_02", "agenda_03", "agenda_04"]
        for item_no, item in enumerate(chapter["items"], start=1):
            name = agenda_names[item_no - 1]
            card = find(toc, name)
            if card is None:
                issues.append("chapter toc card %s missing for %s" % (name, chapter["title"]))
                continue
            title_box = find(toc, name + "_title")
            if title_box is None or item["title"] not in shape_text(title_box):
                issues.append("chapter toc item %d missing for %s" % (item_no, chapter["title"]))
        for name in agenda_names[len(chapter["items"]):]:
            if find(toc, name) is not None:
                issues.append("unused chapter toc card %s should be removed" % name)
        for sh in toc.shapes:
            if sh.name.startswith("agenda_"):
                check_bounds(sh, slide_w, slide_h, issues, "chapter_toc")
        record("chapter_toc")

        chunks = [
            chapter["items"][i:i + MAX_ITEMS_PER_CHAPTER]
            for i in range(0, len(chapter["items"]), MAX_ITEMS_PER_CHAPTER)
        ]
        for chunk in chunks:
            if idx >= len(slides):
                issues.append("missing content page for %s" % chapter["title"])
                break
            slide = slides[idx]
            if shape_text(find(slide, "page_title")) != chapter["title"]:
                issues.append("content page title wrong for %s" % chapter["title"])
            if not shape_text(find(slide, "page_kicker")):
                issues.append("content page kicker empty for %s" % chapter["title"])
            if find(slide, "accent") is None:
                issues.append("content page accent missing for %s" % chapter["title"])
            cards = [
                sh for sh in slide.shapes
                if sh.name.startswith("card_")
                and not sh.name.endswith(("_title", "_summary", "_meta", "_chip", "_chip_text", "_accent"))
            ]
            if len(cards) != len(chunk):
                issues.append("content page has %d cards, expected %d" % (len(cards), len(chunk)))
            for card in cards:
                for suffix in ("_title", "_summary", "_meta", "_chip_text", "_accent"):
                    if find(slide, card.name + suffix) is None:
                        issues.append("missing %s on %s" % (suffix, card.name))
            for item in chunk:
                if len(item["title"]) > MAX_TITLE_CHARS:
                    issues.append("title too long (%d): %s" % (len(item["title"]), item["title"]))
                if len(item["summary"]) > MAX_SUMMARY_CHARS:
                    issues.append("summary too long (%d): %s" % (len(item["summary"]), item["title"]))
            for sh in slide.shapes:
                if sh.name.startswith("card_") or sh.name in ("page_title", "page_kicker", "accent", "page_rule"):
                    check_bounds(sh, slide_w, slide_h, issues, "content")
            record("content", cards=len(cards))

    if idx < len(slides):
        back = slides[-1]
        if find(back, "文本框 3") is None:
            issues.append("back cover missing slogan")
        record("back")

    report = {
        "ok": not issues,
        "slide_count": len(slides),
        "expected_count": expected_pages,
        "issues": issues,
        "slides": report_slides,
    }
    with open(args.report, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    if issues:
        print("QA FAILED")
        for issue in issues:
            print(" -", issue)
        sys.exit(1)
    print("QA OK: %d slides, roles=%s" % (len(slides), ",".join(s["role"] for s in report_slides)))


def find(slide, name):
    for sh in slide.shapes:
        if sh.name == name:
            return sh
    return None


if __name__ == "__main__":
    main()
