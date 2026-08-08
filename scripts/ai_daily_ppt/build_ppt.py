#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the v4 AI daily brief from the Zhende template.

Deck structure is fixed at 15 pages: cover, global TOC, 4 chapters x
(chapter image page + 2 detailed item pages), back cover.  Each chapter has
exactly two items.  Chapter pages reuse the template divider and add a large
brand image plus two preview rows.  Detail pages use the blank content
skeleton: header, left text panel (summary / key points / impact / source)
and right AI brand image.  Text frames keep PowerPoint auto-shrink enabled so
long headlines cannot spill out of their frame.
"""

import argparse
import copy
import json
import os
import sys
from io import BytesIO

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt


BRAND_BLUE = RGBColor(0x15, 0x3C, 0x86)
ACCENT_BLUE = RGBColor(0x29, 0x3F, 0x8E)
LIGHT_BLUE = RGBColor(0xE8, 0xEF, 0xFA)
DARK_TEXT = RGBColor(0x22, 0x2B, 0x36)
BODY_TEXT = RGBColor(0x3A, 0x44, 0x52)
META_TEXT = RGBColor(0x7A, 0x85, 0x96)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
CARD_LINE = RGBColor(0xC9, 0xD7, 0xEA)
LIGHT_LINE = RGBColor(0xE4, 0xEA, 0xF3)
FONT = "Microsoft YaHei"

CHAPTER_COUNT = 4
ITEMS_PER_CHAPTER = 2
SLIDE_W = 13.333
SLIDE_H = 7.5
MARGIN = 0.76


def _apply_typeface(rPr, name):
    for tag in ("a:ea", "a:cs"):
        el = rPr.find(qn(tag))
        if el is None:
            el = rPr.makeelement(qn(tag), {})
            anchor = rPr.find(qn("a:sym"))
            if anchor is None:
                anchor = rPr.find(qn("a:hlinkClick"))
            if anchor is None:
                anchor = rPr.find(qn("a:hlinkMouseOver"))
            if anchor is None:
                anchor = rPr.find(qn("a:rtl"))
            if anchor is not None:
                anchor.addprevious(el)
            else:
                rPr.append(el)
        el.set("typeface", name)


def set_run_font(run, size=None, bold=None, color=None, name=None):
    f = run.font
    if size is not None:
        f.size = Pt(size)
    if bold is not None:
        f.bold = bold
    if color is not None:
        f.color.rgb = color
    if name:
        f.name = name
        _apply_typeface(run._r.get_or_add_rPr(), name)


def set_existing_text(shape, text, size=None, bold=None, color=None, name=None,
                      align=None, anchor=None, line_spacing=1.08):
    """Replace a template text box with a single clean run and auto-shrink."""
    tf = shape.text_frame
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
    tf.margin_left = Inches(0.04)
    tf.margin_right = Inches(0.04)
    tf.margin_top = Inches(0.02)
    tf.margin_bottom = Inches(0.02)
    if anchor is not None:
        tf.vertical_anchor = anchor
    for extra in list(tf.paragraphs[1:]):
        extra._p.getparent().remove(extra._p)
    p = tf.paragraphs[0]
    for run in list(p.runs):
        run._r.getparent().remove(run._r)
    run = p.add_run()
    run.text = text
    set_run_font(run, size=size, bold=bold, color=color, name=name)
    if align is not None:
        p.alignment = align
    p.line_spacing = line_spacing
    p.space_after = Pt(0)
    return run


def set_cell_text(cell, text):
    tf = cell.text_frame
    p = tf.paragraphs[0]
    runs = list(p.runs)
    if runs:
        run = runs[0]
        for extra in runs[1:]:
            extra._r.getparent().remove(extra._r)
    else:
        run = p.add_run()
    run.text = text
    if not runs:
        set_run_font(run, size=10.5, color=DARK_TEXT, name=FONT)
    for extra in list(tf.paragraphs[1:]):
        extra._p.getparent().remove(extra._p)


def find_shape(slide, name):
    for sh in slide.shapes:
        if sh.name == name:
            return sh
    return None


def find_slide(prs, predicate, label):
    for slide in prs.slides:
        if predicate(slide):
            return slide
    raise ValueError("template slide not found: %s" % label)


def duplicate_slide(prs, source):
    new_slide = prs.slides.add_slide(source.slide_layout)
    sp_tree = new_slide.shapes._spTree
    for shape in source.shapes:
        sp_tree.append(copy.deepcopy(shape._element))
    _strip_custom_data(sp_tree)
    _remap_image_rels(source, new_slide)
    return new_slide


def _strip_custom_data(sp_tree):
    for el in list(sp_tree.iter(qn("p:custDataLst"))):
        el.getparent().remove(el)


def _remap_image_rels(source, new_slide):
    for blip in new_slide.shapes._spTree.iter(qn("a:blip")):
        embed = blip.get(qn("r:embed"))
        if embed:
            try:
                part = source.part.related_part(embed)
            except KeyError:
                continue
            image_part, new_rId = new_slide.part.get_or_add_image_part(BytesIO(part.blob))
            blip.set(qn("r:embed"), new_rId)
            continue
        link = blip.get(qn("r:link"))
        if link:
            try:
                part = source.part.related_part(link)
            except KeyError:
                continue
            new_rId = new_slide.part.relate_to(part, part.reltype)
            blip.set(qn("r:link"), new_rId)


def drop_original_slides(prs, rids):
    sldIdLst = prs.slides._sldIdLst
    for sldId in list(sldIdLst):
        rId = sldId.get(qn("r:id"))
        if rId in rids:
            prs.part.drop_rel(rId)
            sldIdLst.remove(sldId)


def add_textbox(slide, name, left, top, width, height, text, size,
                bold=False, color=None, align=None, anchor=None,
                line_spacing=1.08, auto_size=True):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    box.name = name
    tf = box.text_frame
    tf.word_wrap = True
    if auto_size:
        tf.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
    tf.margin_left = Inches(0.04)
    tf.margin_right = Inches(0.04)
    tf.margin_top = Inches(0.02)
    tf.margin_bottom = Inches(0.02)
    if anchor is not None:
        tf.vertical_anchor = anchor
    p = tf.paragraphs[0]
    p.alignment = align if align is not None else PP_ALIGN.LEFT
    p.line_spacing = line_spacing
    p.space_after = Pt(0)
    run = p.add_run()
    run.text = text
    set_run_font(run, size=size, bold=bold, color=color, name=FONT)
    return box


def add_rect(slide, name, left, top, width, height, color, line=False):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height)
    )
    shape.name = name
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    if line:
        shape.line.color.rgb = CARD_LINE
        shape.line.width = Pt(1)
    else:
        shape.line.fill.background()
    shape.shadow.inherit = False
    return shape


def add_outline(slide, name, left, top, width, height, line_color=CARD_LINE):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height)
    )
    shape.name = name
    shape.fill.background()
    shape.line.color.rgb = line_color
    shape.line.width = Pt(1)
    shape.shadow.inherit = False
    return shape


def add_rounded_rect(slide, name, left, top, width, height, fill=WHITE,
                     line_color=CARD_LINE, radius=0.08):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height)
    )
    shape.name = name
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    if line_color is None:
        shape.line.fill.background()
    else:
        shape.line.color.rgb = line_color
        shape.line.width = Pt(1)
    shape.shadow.inherit = False
    try:
        shape.adjustments[0] = radius
    except Exception:
        pass
    return shape


def add_image(slide, name, image_path, left, top, width=None, height=None):
    if width is not None and height is not None:
        pic = slide.shapes.add_picture(
            image_path, Inches(left), Inches(top), Inches(width), Inches(height)
        )
    else:
        pic = slide.shapes.add_picture(image_path, Inches(left), Inches(top))
    pic.name = name
    return pic


def add_header(slide, date_text, chapter_title, page_no, page_total):
    kicker = "AI 动态日报 · %s · 第 %d 页 / 共 %d 页" % (date_text, page_no, page_total)
    add_textbox(slide, "page_kicker", MARGIN, 0.38, 10.6, 0.30, kicker, 10,
                color=META_TEXT, line_spacing=1.0)
    add_textbox(slide, "page_title", MARGIN, 0.70, 9.4, 0.56, chapter_title, 26,
                bold=True, color=BRAND_BLUE, line_spacing=1.0)
    add_rect(slide, "accent", MARGIN + 0.02, 1.34, 1.10, 0.07, ACCENT_BLUE)
    add_rect(slide, "page_rule", MARGIN, 1.52, SLIDE_W - 2 * MARGIN, 0.012, LIGHT_LINE)


def resolve_image(base_dir, path):
    if os.path.isabs(path):
        return path
    return os.path.join(base_dir, path)


def add_chapter_page(prs, divider_src, chapter_no, chapter, base_dir, page_no, page_total):
    slide = duplicate_slide(prs, divider_src)
    for name in ("TextBox 1", "TextBox 5"):
        sh = find_shape(slide, name)
        if sh is not None:
            sh._element.getparent().remove(sh._element)

    chapter_image = resolve_image(base_dir, chapter["image"])
    add_image(slide, "chapter_image", chapter_image, 0.72, 0.62, 5.95, 3.35)
    add_outline(slide, "chapter_image_frame", 0.72, 0.62, 5.95, 3.35)

    chip = add_rounded_rect(slide, "chapter_chip", 7.02, 0.76, 1.30, 0.42,
                            fill=BRAND_BLUE, line_color=None, radius=0.5)
    add_textbox(slide, "chapter_chip_text", 7.02, 0.76, 1.30, 0.42,
                "第 %d 章" % chapter_no, 11, bold=True, color=WHITE,
                align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, line_spacing=1.0,
                auto_size=False)

    title_box = find_shape(slide, "TextBox 4")
    title_box.left = Inches(8.42)
    title_box.top = Inches(0.72)
    title_box.width = Inches(4.22)
    title_box.height = Inches(0.52)
    set_existing_text(title_box, chapter["title"], size=21, bold=False,
                      color=DARK_TEXT, name=FONT, anchor=MSO_ANCHOR.MIDDLE)

    statement_box = find_shape(slide, "TextBox 6")
    statement_box.left = Inches(7.02)
    statement_box.top = Inches(1.38)
    statement_box.width = Inches(5.62)
    statement_box.height = Inches(1.12)
    set_existing_text(statement_box, chapter["statement"], size=15, bold=False,
                      color=BODY_TEXT, name=FONT, anchor=MSO_ANCHOR.TOP,
                      line_spacing=1.2)

    add_textbox(slide, "chapter_preview_label", 0.72, 4.28, 2.6, 0.32,
                "本章精选 · 2 条", 12, bold=True, color=ACCENT_BLUE, line_spacing=1.0)
    add_rect(slide, "chapter_preview_rule", 0.72, 4.68, 11.85, 0.012, LIGHT_LINE)

    preview_left = 0.72
    preview_top = 4.88
    preview_w = 5.90
    preview_h = 0.92
    for idx, item in enumerate(chapter["items"]):
        left = preview_left + idx * (preview_w + 0.05)
        prefix = "chapter_preview_%d" % (idx + 1)
        add_rounded_rect(slide, prefix, left, preview_top, preview_w, preview_h,
                         fill=WHITE, line_color=CARD_LINE, radius=0.10)
        badge = add_rounded_rect(
            slide, prefix + "_badge", left + 0.16, preview_top + 0.20,
            0.52, 0.52, fill=ACCENT_BLUE, line_color=None, radius=0.14,
        )
        add_textbox(slide, prefix + "_badge_text", left + 0.16, preview_top + 0.20,
                    0.52, 0.52, "%02d" % (chapter_no * 10 + idx + 1), 12, bold=True,
                    color=WHITE, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE,
                    line_spacing=1.0, auto_size=False)
        add_textbox(slide, prefix + "_title", left + 0.86, preview_top + 0.06,
                    preview_w - 1.05, 0.42, item["title"], 15, bold=True,
                    color=DARK_TEXT, anchor=MSO_ANCHOR.MIDDLE, line_spacing=1.05)
        add_textbox(slide, prefix + "_summary", left + 0.86, preview_top + 0.50,
                    preview_w - 1.05, 0.36, item["summary"], 10.5, color=META_TEXT,
                    anchor=MSO_ANCHOR.MIDDLE, line_spacing=1.0)

    add_textbox(slide, "chapter_page_footer", 0.72, 6.92, 8.0, 0.30,
                "第 %02d 章 · 第 %d 页 / 共 %d 页" % (chapter_no, page_no, page_total),
                9, color=META_TEXT, line_spacing=1.0)
    return slide


def add_detail_page(prs, content_src, date_text, chapter_no, chapter, item_no,
                    item, page_no, page_total, base_dir):
    slide = duplicate_slide(prs, content_src)
    add_header(slide, date_text, chapter["title"], page_no, page_total)

    chip = add_rounded_rect(slide, "detail_chip", MARGIN, 1.66, 1.05, 0.38,
                            fill=BRAND_BLUE, line_color=None, radius=0.5)
    add_textbox(slide, "detail_chip_text", MARGIN, 1.66, 1.05, 0.38,
                "%02d" % (chapter_no * 10 + item_no), 12, bold=True, color=WHITE,
                align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, line_spacing=1.0,
                auto_size=False)

    add_textbox(slide, "detail_title", 2.06, 1.58, 6.05, 0.62, item["title"], 20,
                bold=True, color=BRAND_BLUE, anchor=MSO_ANCHOR.MIDDLE, line_spacing=1.05)
    add_rect(slide, "detail_rule", MARGIN, 2.36, 6.95, 0.012, LIGHT_LINE)

    add_textbox(slide, "detail_summary_label", MARGIN, 2.52, 1.2, 0.28,
                "背景摘要", 11, bold=True, color=ACCENT_BLUE, line_spacing=1.0)
    add_textbox(slide, "detail_summary", MARGIN, 2.84, 6.90, 1.05, item["summary"],
                13, color=BODY_TEXT, anchor=MSO_ANCHOR.TOP, line_spacing=1.22)

    add_rect(slide, "detail_kp_bg", MARGIN, 4.02, 6.95, 1.42, LIGHT_BLUE)
    add_textbox(slide, "detail_kp_label", MARGIN + 0.12, 4.12, 1.5, 0.26,
                "要点解读", 11, bold=True, color=BRAND_BLUE, line_spacing=1.0)
    kp_left = MARGIN + 0.12
    kp_top = 4.46
    kp_w = 6.70
    kp_h = 0.23
    for idx, point in enumerate(item["key_points"]):
        add_textbox(
            slide, "detail_kp_%d" % (idx + 1), kp_left, kp_top + idx * 0.245,
            kp_w, kp_h, "%d. %s" % (idx + 1, point), 11.5, color=DARK_TEXT,
            anchor=MSO_ANCHOR.MIDDLE, line_spacing=1.0,
        )

    add_textbox(slide, "detail_impact_label", MARGIN, 5.62, 1.2, 0.28,
                "影响判断", 11, bold=True, color=ACCENT_BLUE, line_spacing=1.0)
    add_textbox(slide, "detail_impact", MARGIN, 5.94, 6.90, 0.92, item["impact"],
                12.5, color=BODY_TEXT, anchor=MSO_ANCHOR.TOP, line_spacing=1.2)
    add_textbox(slide, "detail_source", MARGIN, 6.92, 6.90, 0.34,
                "来源：%s · %s · %s" % (item["source"], item["meta"], item["link"]),
                9, color=META_TEXT, anchor=MSO_ANCHOR.MIDDLE, line_spacing=1.0)

    item_image = resolve_image(base_dir, item["image"])
    add_image(slide, "detail_image", item_image, 8.06, 1.70, 4.50, 3.375)
    add_outline(slide, "detail_image_frame", 8.06, 1.70, 4.50, 3.375)
    add_textbox(slide, "detail_image_caption", 8.06, 5.18, 4.50, 0.30,
                "AI 品牌配图 · 概念视觉", 9.5, color=META_TEXT,
                align=PP_ALIGN.CENTER, line_spacing=1.0)
    return slide


def set_cover(cover, meta):
    publisher = find_shape(cover, "文本框 13")
    publisher.height = Inches(0.42)
    set_existing_text(publisher, meta["publisher"],
                      size=24, bold=False, name="思源黑体 CN Light")
    title = find_shape(cover, "文本框 12")
    title.top = Inches(4.32)
    set_existing_text(title, meta["title"],
                      size=38, bold=False, color=BRAND_BLUE, name="思源黑体 CN Medium")
    set_existing_text(find_shape(cover, "文本框 1"), meta["date"],
                      size=16, bold=False, name="思源黑体 CN Regular")
    table = find_shape(cover, "表格 7").table
    values = {
        (0, 1): meta["classification"],
        (0, 3): meta["confidentiality"],
        (1, 1): meta["department"],
        (1, 3): meta["author"],
        (2, 1): meta["created"],
        (2, 3): meta["scope"],
    }
    for (row, col), value in values.items():
        set_cell_text(table.cell(row, col), value)


def set_toc_entry(box, idx, title):
    tf = box.text_frame
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
    tf.margin_left = Inches(0.04)
    tf.margin_right = Inches(0.04)
    tf.margin_top = Inches(0.02)
    tf.margin_bottom = Inches(0.02)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    for extra in list(tf.paragraphs[1:]):
        extra._p.getparent().remove(extra._p)
    p = tf.paragraphs[0]
    for run in list(p.runs):
        run._r.getparent().remove(run._r)
    r1 = p.add_run()
    r1.text = "%d.  " % idx
    set_run_font(r1, size=20, bold=True, color=ACCENT_BLUE, name=FONT)
    r2 = p.add_run()
    r2.text = title
    set_run_font(r2, size=20, bold=False, color=DARK_TEXT, name=FONT)
    p.alignment = PP_ALIGN.LEFT
    p.line_spacing = 1.0
    p.space_after = Pt(0)


def set_global_toc(toc, chapters):
    boxes = ["TextBox 2", "TextBox 3", "TextBox 4", "TextBox 6"]
    for idx, chapter in enumerate(chapters):
        box = find_shape(toc, boxes[idx])
        box.left = Inches(4.72)
        box.top = Inches(1.94 + idx * 0.78)
        box.width = Inches(6.4)
        box.height = Inches(0.62)
        set_toc_entry(box, idx + 1, chapter["title"])
    for name in boxes[len(chapters):]:
        sh = find_shape(toc, name)
        if sh is not None:
            sh._element.getparent().remove(sh._element)
    for name in ("TextBox 7", "TextBox 8"):
        sh = find_shape(toc, name)
        if sh is not None:
            sh._element.getparent().remove(sh._element)


def build(prs, content, base_dir):
    meta = content["meta"]
    chapters = content["chapters"]
    if len(chapters) != CHAPTER_COUNT:
        raise ValueError("需要 %d 章，当前 %d 章" % (CHAPTER_COUNT, len(chapters)))
    for chapter in chapters:
        if len(chapter["items"]) != ITEMS_PER_CHAPTER:
            raise ValueError("每章需要 %d 条：%s" % (ITEMS_PER_CHAPTER, chapter["title"]))

    cover_src = find_slide(prs, lambda s: find_shape(s, "表格 7") is not None, "cover")
    global_toc_src = find_slide(prs, lambda s: find_shape(s, "TextBox 2") is not None, "global toc")
    divider_src = find_slide(
        prs,
        lambda s: s.slide_layout.name == "2_Custom Layout" and find_shape(s, "TextBox 1") is not None
        and find_shape(s, "TextBox 4") is not None,
        "divider",
    )
    content_src = find_slide(
        prs,
        lambda s: s.slide_layout.name == "Picture with Caption" and len(s.shapes) == 0,
        "content skeleton",
    )
    back_src = find_slide(prs, lambda s: find_shape(s, "文本框 3") is not None, "back cover")

    original_rids = [sldId.get(qn("r:id")) for sldId in prs.slides._sldIdLst]

    cover = duplicate_slide(prs, cover_src)
    set_cover(cover, meta)
    global_toc = duplicate_slide(prs, global_toc_src)
    set_global_toc(global_toc, chapters)

    page_no = 1
    page_total = 15
    for chapter_no, chapter in enumerate(chapters, start=1):
        add_chapter_page(prs, divider_src, chapter_no, chapter, base_dir,
                         page_no, page_total)
        page_no += 1
        for item_no, item in enumerate(chapter["items"], start=1):
            add_detail_page(prs, content_src, meta["date"], chapter_no, chapter,
                            item_no, item, page_no, page_total, base_dir)
            page_no += 1

    duplicate_slide(prs, back_src)
    drop_original_slides(prs, original_rids)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True)
    ap.add_argument("--content", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--assets-dir", default=".", help="base dir for relative image paths")
    args = ap.parse_args()
    with open(args.content, encoding="utf-8") as f:
        content = json.load(f)
    prs = Presentation(args.template)
    build(prs, content, args.assets_dir)
    prs.save(args.out)
    print("saved %s (%d slides)" % (args.out, len(prs.slides._sldIdLst)))


if __name__ == "__main__":
    main()
