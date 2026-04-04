"""
Fly Straight Onboarding PDF Generator
Parses custom markup tags and generates branded onboarding PDFs.

Purpose-built for the fitness onboarding document type.
Leaner than offer_pdf_generator.py — no offer-specific tags
(BOX_INVESTMENT, TABLE_OPTIONS, WEEK_ARC, PHOTO_NOTES, METRIC, CHECKLIST).

New vs offer generator:
  - draw_header callback: thin gold rule + 'FLY STRAIGHT' label on every
    content page (page 2 onward). Cover page gets header only.
  - draw_footer callback: 'FLY STRAIGHT TRANSFORMATION' centered footer,
    same as offer generator.
  - STEP tag: [STEP]Bold Title|Body description[/STEP]
    Renders a two-part onboarding step — bold title on its own line,
    body indented below. Replaces cramped H3+BODY pattern.
  - BOX_PREP tag: [BOX_PREP]content[/BOX_PREP]
    Thin-ruled preparation list. Items separated by light horizontal
    rules rather than rendered as bullet points. Clean, readable.
  - BOX_RED tag: red background callout box for CTA.
    Distinct from offer generator's red box — uses stronger fill
    so the booking CTA reads as primary action.
  - Cover page: COVER_CLIENT block vertically centered with breathing
    room. Second GOLD_RULE at end of cover content closes the frame.
  - H3 spaceBefore reduced vs offer generator — onboarding subsection
    headers are functional dividers, not major section breaks.
"""

import io
import re
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.platypus.flowables import Flowable


# ─── BRAND COLORS ────────────────────────────────────────────────────────────
BLACK        = colors.HexColor('#000000')
NEAR_BLACK   = colors.HexColor('#1A1A1A')
WHITE        = colors.HexColor('#FFFFFF')
GOLD         = colors.HexColor('#FFD000')
GOLD_LIGHT   = colors.HexColor('#FFF8DC')
RED          = colors.HexColor('#9B0F12')

GREEN        = colors.HexColor('#1B5E20')
GREEN_LIGHT  = colors.HexColor('#E8F5E9')
GREEN_BORDER = colors.HexColor('#2E7D32')

RED_BG       = colors.HexColor('#FFEBEE')
RED_BORDER   = colors.HexColor('#C62828')
RED_STRONG   = colors.HexColor('#B71C1C')   # CTA box — stronger than body red

GRAY_BG      = colors.HexColor('#F5F5F5')
GRAY_BORDER  = colors.HexColor('#424242')
GRAY_LIGHT   = colors.HexColor('#E0E0E0')   # thin rule inside BOX_PREP
GRAY         = colors.HexColor('#666666')
LIGHT_GRAY   = colors.HexColor('#EEEEEE')

QUOTE_BORDER = colors.HexColor('#2E7D32')
QUOTE_BG     = colors.HexColor('#F9FBE7')

PAGE_W, PAGE_H = letter
CONTENT_W    = PAGE_W - 1.5 * inch          # 0.75in margins each side


# ─── STYLES ──────────────────────────────────────────────────────────────────
def create_styles():
    styles = getSampleStyleSheet()
    return {
        # ── Headers ──────────────────────────────────────────────────────────
        'h1': ParagraphStyle('OB_H1',
            fontName='Helvetica-Bold', fontSize=26,
            textColor=NEAR_BLACK, spaceAfter=10, spaceBefore=16,
            leading=30, alignment=TA_LEFT),

        'h2': ParagraphStyle('OB_H2',
            fontName='Helvetica-Bold', fontSize=18,
            textColor=RED, spaceAfter=8, spaceBefore=14,
            leading=22, alignment=TA_LEFT),

        # Tighter than offer generator — subsection divider, not major break
        'h3': ParagraphStyle('OB_H3',
            fontName='Helvetica-Bold', fontSize=13,
            textColor=NEAR_BLACK, spaceAfter=6, spaceBefore=12,
            leading=16, alignment=TA_LEFT),

        'h4': ParagraphStyle('OB_H4',
            fontName='Helvetica-Bold', fontSize=11,
            textColor=NEAR_BLACK, spaceAfter=4, spaceBefore=8,
            leading=14, alignment=TA_LEFT),

        # ── Body ─────────────────────────────────────────────────────────────
        'body': ParagraphStyle('OB_Body',
            fontName='Helvetica', fontSize=10,
            textColor=NEAR_BLACK, leading=15,
            alignment=TA_JUSTIFY, spaceAfter=8),

        'pullquote': ParagraphStyle('OB_Pullquote',
            fontName='Helvetica-Bold', fontSize=14,
            textColor=RED, leading=20,
            alignment=TA_CENTER, spaceBefore=14, spaceAfter=14,
            leftIndent=40, rightIndent=40),

        # ── Box interiors ─────────────────────────────────────────────────────
        'box_body': ParagraphStyle('OB_BoxBody',
            fontName='Helvetica', fontSize=10,
            textColor=NEAR_BLACK, leading=15,
            alignment=TA_LEFT, spaceAfter=4),

        'box_bold': ParagraphStyle('OB_BoxBold',
            fontName='Helvetica-Bold', fontSize=10,
            textColor=NEAR_BLACK, leading=15,
            alignment=TA_LEFT, spaceAfter=4),

        'box_cta': ParagraphStyle('OB_BoxCTA',
            fontName='Helvetica-Bold', fontSize=11,
            textColor=WHITE, leading=16,
            alignment=TA_CENTER, spaceAfter=4),

        'box_cta_body': ParagraphStyle('OB_BoxCTABody',
            fontName='Helvetica', fontSize=10,
            textColor=WHITE, leading=14,
            alignment=TA_CENTER, spaceAfter=3),

        'quote_body': ParagraphStyle('OB_QuoteBody',
            fontName='Helvetica-Oblique', fontSize=11,
            textColor=NEAR_BLACK, leading=16,
            alignment=TA_LEFT, spaceAfter=4),

        # ── Step tag interior ─────────────────────────────────────────────────
        'step_title': ParagraphStyle('OB_StepTitle',
            fontName='Helvetica-Bold', fontSize=11,
            textColor=NEAR_BLACK, leading=15,
            alignment=TA_LEFT, spaceAfter=3),

        'step_body': ParagraphStyle('OB_StepBody',
            fontName='Helvetica', fontSize=10,
            textColor=NEAR_BLACK, leading=15,
            alignment=TA_LEFT, spaceAfter=4,
            leftIndent=12),

        # ── Cover client block ────────────────────────────────────────────────
        'cover_label': ParagraphStyle('OB_CoverLabel',
            fontName='Helvetica', fontSize=9,
            textColor=GRAY, leading=13,
            alignment=TA_CENTER, spaceAfter=6),

        'cover_name': ParagraphStyle('OB_CoverName',
            fontName='Helvetica-Bold', fontSize=18,
            textColor=NEAR_BLACK, leading=22,
            alignment=TA_CENTER, spaceAfter=6),

        'cover_location': ParagraphStyle('OB_CoverLocation',
            fontName='Helvetica', fontSize=12,
            textColor=GRAY, leading=16,
            alignment=TA_CENTER, spaceAfter=8),

        # ── Header bar / banner ───────────────────────────────────────────────
        'brand_bar': ParagraphStyle('OB_BrandBar',
            fontName='Helvetica-Bold', fontSize=14,
            textColor=WHITE, leading=20,
            alignment=TA_CENTER),

        'banner_text': ParagraphStyle('OB_BannerText',
            fontName='Helvetica-Bold', fontSize=13,
            textColor=WHITE, leading=18,
            alignment=TA_LEFT),

        'header_label': ParagraphStyle('OB_HeaderLabel',
            fontName='Helvetica-Bold', fontSize=8,
            textColor=GRAY, leading=10,
            alignment=TA_RIGHT, spaceAfter=0),
    }


# ─── HELPER: inline markup ────────────────────────────────────────────────────
def apply_inline(text):
    """Convert **bold** and *italic* to ReportLab XML tags."""
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.+?)\*',     r'<i>\1</i>', text)
    return text


# ─── HELPER: gold rule ────────────────────────────────────────────────────────
def gold_rule():
    return HRFlowable(
        width='100%', thickness=2, color=GOLD,
        spaceBefore=10, spaceAfter=10
    )


def thin_rule():
    """Light gray hairline rule — used inside BOX_PREP between items."""
    return HRFlowable(
        width='100%', thickness=0.5, color=GRAY_LIGHT,
        spaceBefore=4, spaceAfter=4
    )


# ─── HELPER: section banner ───────────────────────────────────────────────────
def section_banner(text, bg_color, styles):
    data = [[Paragraph(f'<b>{text}</b>', styles['banner_text'])]]
    t = Table(data, colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), bg_color),
        ('LEFTPADDING',   (0, 0), (-1, -1), 14),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 14),
        ('TOPPADDING',    (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    return t


# ─── HELPER: header bar (black, full width) ───────────────────────────────────
def header_bar(text, styles):
    data = [[Paragraph(f'<b>{text}</b>', styles['brand_bar'])]]
    t = Table(data, colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), BLACK),
        ('LEFTPADDING',   (0, 0), (-1, -1), 14),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 14),
        ('TOPPADDING',    (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    return t


# ─── HELPER: standard callout box ─────────────────────────────────────────────
def callout_box(text, bg, border, styles, is_quote=False):
    """
    General callout box. Strips leading bullet/dash chars if model
    outputs them despite the prose mandate (safety net).
    """
    style = styles['quote_body'] if is_quote else styles['box_body']
    lines = text.strip().split('\n')
    paragraphs = []
    for line in lines:
        line = line.strip()
        if not line:
            paragraphs.append(Spacer(1, 4))
            continue
        if line.startswith(('- ', '• ', '* ')):
            line = line[2:]
        line = apply_inline(line)
        paragraphs.append(Paragraph(line, style))

    inner = Table([[p] for p in paragraphs], colWidths=[CONTENT_W - 0.4 * inch])
    inner.setStyle(TableStyle([
        ('LEFTPADDING',   (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
        ('TOPPADDING',    (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('BACKGROUND',    (0, 0), (-1, -1), bg),
    ]))
    outer = Table([[inner]], colWidths=[CONTENT_W])
    outer.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), bg),
        ('BOX',           (0, 0), (-1, -1), 2, border),
        ('LEFTPADDING',   (0, 0), (-1, -1), 14),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 14),
        ('TOPPADDING',    (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    return outer


# ─── HELPER: BOX_RED — CTA box ────────────────────────────────────────────────
def cta_box(text, styles):
    """
    Strong red box for booking CTA. White text, centered.
    First line rendered bold (the heading line).
    Remaining lines rendered as normal body.
    """
    lines = [l.strip() for l in text.strip().split('\n') if l.strip()]
    rows = []
    for i, line in enumerate(lines):
        line_rendered = apply_inline(line)
        if i == 0:
            rows.append(Paragraph(line_rendered, styles['box_cta']))
        else:
            rows.append(Paragraph(line_rendered, styles['box_cta_body']))

    if not rows:
        return Spacer(1, 4)

    inner = Table([[r] for r in rows], colWidths=[CONTENT_W - 0.4 * inch])
    inner.setStyle(TableStyle([
        ('LEFTPADDING',   (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
        ('TOPPADDING',    (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('BACKGROUND',    (0, 0), (-1, -1), RED_STRONG),
    ]))
    outer = Table([[inner]], colWidths=[CONTENT_W])
    outer.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), RED_STRONG),
        ('BOX',           (0, 0), (-1, -1), 0, RED_STRONG),
        ('LEFTPADDING',   (0, 0), (-1, -1), 14),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 14),
        ('TOPPADDING',    (0, 0), (-1, -1), 14),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
    ]))
    return outer


# ─── HELPER: BOX_PREP — preparation list ─────────────────────────────────────
def prep_box(text, styles):
    """
    Clean preparation checklist. Each non-empty line is a separate item
    separated by a thin gray rule. Bold text (**...**) renders inline.
    No bullet points — items stand alone as short paragraphs.
    """
    lines = [l.strip() for l in text.strip().split('\n') if l.strip()]
    if not lines:
        return Spacer(1, 4)

    rows = []
    for i, line in enumerate(lines):
        if line.startswith(('- ', '• ', '* ')):
            line = line[2:]
        line = apply_inline(line)
        rows.append([Paragraph(line, styles['box_body'])])
        if i < len(lines) - 1:
            rows.append([thin_rule()])

    inner = Table(rows, colWidths=[CONTENT_W - 0.4 * inch])
    inner.setStyle(TableStyle([
        ('LEFTPADDING',   (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
        ('TOPPADDING',    (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('BACKGROUND',    (0, 0), (-1, -1), GRAY_BG),
    ]))
    outer = Table([[inner]], colWidths=[CONTENT_W])
    outer.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), GRAY_BG),
        ('BOX',           (0, 0), (-1, -1), 1.5, GRAY_BORDER),
        ('LEFTPADDING',   (0, 0), (-1, -1), 14),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 14),
        ('TOPPADDING',    (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    return outer


# ─── HELPER: STEP tag ─────────────────────────────────────────────────────────
def step_element(content, styles):
    """
    Renders [STEP]Bold Title|Body description[/STEP].
    Pipe separates the bold step title from the body text.
    If no pipe found, renders entire content as bold title.
    """
    content = content.strip()
    if '|' in content:
        title, _, body = content.partition('|')
        title = title.strip()
        body  = body.strip()
    else:
        title = content
        body  = ''

    rows = [[Paragraph(apply_inline(title), styles['step_title'])]]
    if body:
        rows.append([Paragraph(apply_inline(body), styles['step_body'])])

    t = Table(rows, colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ('LEFTPADDING',   (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
        ('TOPPADDING',    (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    return t


# ─── HELPER: COMPONENT card ───────────────────────────────────────────────────
def component_card(inner_content, styles):
    """
    Renders [COMPONENT]...[/COMPONENT] — light gray card with 3pt gold
    left border. Inner content parsed recursively as markup.
    """
    inner_story = parse_markup_to_story(inner_content, styles)
    if not inner_story:
        return Spacer(1, 4)

    rows = [[item] for item in inner_story]
    inner_table = Table(rows, colWidths=[CONTENT_W - 0.35 * inch])
    inner_table.setStyle(TableStyle([
        ('LEFTPADDING',   (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
        ('TOPPADDING',    (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('BACKGROUND',    (0, 0), (-1, -1), GRAY_BG),
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
    ]))
    outer = Table([[inner_table]], colWidths=[CONTENT_W])
    outer.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), GRAY_BG),
        ('LEFTPADDING',   (0, 0), (-1, -1), 14),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 14),
        ('TOPPADDING',    (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LINEBEFORE',    (0, 0), (0, -1),  3, GOLD),
    ]))
    return outer


# ─── HELPER: COVER_CLIENT block ───────────────────────────────────────────────
def cover_client_block(content, styles):
    """
    Renders [COVER_CLIENT]Name|City, Province[/COVER_CLIENT].
    Larger name (18pt vs 16pt in offer generator), more vertical breathing
    room. Sits centered in the middle third of the cover page.
    """
    content = content.strip()
    if '|' in content:
        name, _, location = content.partition('|')
        name     = apply_inline(name.strip())
        location = location.strip()
    else:
        name     = apply_inline(content)
        location = ''

    rows = [
        [Paragraph('Prepared Exclusively For:', styles['cover_label'])],
        [Paragraph(f'<b>{name}</b>', styles['cover_name'])],
    ]
    if location:
        rows.append([Paragraph(location, styles['cover_location'])])

    t = Table(rows, colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ('LEFTPADDING',   (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    return t


# ─── PAGE CALLBACKS ───────────────────────────────────────────────────────────
def draw_header_and_footer(canvas, doc):
    """
    Every page: footer with 'FLY STRAIGHT TRANSFORMATION'.
    Pages 2 onward: thin gold rule at top + 'FLY STRAIGHT' right-aligned label.
    """
    canvas.saveState()

    # Footer — all pages
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(GRAY)
    canvas.drawCentredString(
        PAGE_W / 2.0,
        0.45 * inch,
        'FLY STRAIGHT TRANSFORMATION'
    )

    # Header — all pages except cover (page 1)
    if doc.page > 1:
        header_y = PAGE_H - 0.45 * inch
        # Gold rule
        canvas.setStrokeColor(GOLD)
        canvas.setLineWidth(1.5)
        canvas.line(0.75 * inch, header_y, PAGE_W - 0.75 * inch, header_y)
        # Label
        canvas.setFont('Helvetica-Bold', 7)
        canvas.setFillColor(GRAY)
        canvas.drawRightString(
            PAGE_W - 0.75 * inch,
            header_y + 4,
            'FLY STRAIGHT'
        )

    canvas.restoreState()


def draw_cover_page(canvas, doc):
    """
    Cover page only: footer + bottom gold rule to close the frame.
    No top header on the cover.
    """
    canvas.saveState()

    # Footer
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(GRAY)
    canvas.drawCentredString(
        PAGE_W / 2.0,
        0.45 * inch,
        'FLY STRAIGHT TRANSFORMATION'
    )

    canvas.restoreState()


# ─── MAIN PARSER ─────────────────────────────────────────────────────────────
def parse_markup_to_story(markup, styles):
    story = []

    markup = markup.replace('\r\n', '\n').replace('\r', '\n')

    tag_re = re.compile(
        r'\[([A-Z_0-9]+)((?:\s+[a-z_]+="[^"]*")*)\](.*?)\[/\1\]'
        r'|\[([A-Z_0-9]+)((?:\s+[a-z_]+="[^"]*")*)\]',
        re.DOTALL
    )

    tokens = []
    last   = 0
    full   = markup

    for m in tag_re.finditer(full):
        if m.start() > last:
            tokens.append(('text', full[last:m.start()]))

        if m.group(1):
            name      = m.group(1)
            attrs_raw = m.group(2) or ''
            inner     = m.group(3) or ''
        else:
            name      = m.group(4)
            attrs_raw = m.group(5) or ''
            inner     = ''

        attrs = dict(re.findall(r'(\w+)="([^"]*)"', attrs_raw))
        tokens.append(('tag', name, attrs, inner))
        last = m.end()

    if last < len(full):
        tokens.append(('text', full[last:]))

    for token in tokens:
        if token[0] == 'text':
            raw = token[1]
            for line in raw.split('\n'):
                line = line.strip()
                if line:
                    story.append(Paragraph(apply_inline(line), styles['body']))
                else:
                    story.append(Spacer(1, 3))
            continue

        _, name, attrs, inner = token

        # ── Layout ───────────────────────────────────────────────────────────
        if name == 'PAGE_BREAK':
            story.append(PageBreak())

        elif name == 'GOLD_RULE':
            story.append(gold_rule())

        elif name == 'HEADER_BAR':
            story.append(Spacer(1, 6))
            story.append(header_bar(inner.strip(), styles))
            story.append(Spacer(1, 6))

        elif name == 'SECTION_BANNER_RED':
            story.append(Spacer(1, 8))
            story.append(section_banner(inner.strip(), RED, styles))
            story.append(Spacer(1, 8))

        elif name == 'SECTION_BANNER_BLACK':
            story.append(Spacer(1, 8))
            story.append(section_banner(inner.strip(), BLACK, styles))
            story.append(Spacer(1, 8))

        elif name == 'SECTION_BANNER_GREEN':
            story.append(Spacer(1, 8))
            story.append(section_banner(inner.strip(), GREEN, styles))
            story.append(Spacer(1, 8))

        elif name == 'COVER_CLIENT':
            story.append(Spacer(1, 30))
            story.append(cover_client_block(inner, styles))
            story.append(Spacer(1, 30))

        # ── Text ─────────────────────────────────────────────────────────────
        elif name == 'H1':
            story.append(Spacer(1, 8))
            story.append(Paragraph(apply_inline(inner.strip()), styles['h1']))

        elif name == 'H2':
            story.append(Spacer(1, 6))
            story.append(Paragraph(apply_inline(inner.strip()), styles['h2']))

        elif name == 'H3':
            story.append(Spacer(1, 4))
            story.append(Paragraph(apply_inline(inner.strip()), styles['h3']))

        elif name == 'H4':
            story.append(Spacer(1, 4))
            story.append(Paragraph(apply_inline(inner.strip()), styles['h4']))

        elif name == 'BODY':
            # Newlines inside a BODY tag become <br/> so multi-line sign-offs
            # render correctly without needing separate tags.
            text = apply_inline(inner.strip())
            text = text.replace('\n', '<br/>')
            story.append(Paragraph(text, styles['body']))
            story.append(Spacer(1, 4))

        elif name == 'PULLQUOTE':
            story.append(Spacer(1, 8))
            story.append(Paragraph(apply_inline(inner.strip()), styles['pullquote']))
            story.append(Spacer(1, 8))

        # ── Callout boxes ─────────────────────────────────────────────────────
        elif name == 'BOX_GREEN':
            story.append(Spacer(1, 6))
            story.append(callout_box(inner, GREEN_LIGHT, GREEN_BORDER, styles))
            story.append(Spacer(1, 6))

        elif name == 'BOX_BLACK':
            story.append(Spacer(1, 6))
            story.append(callout_box(inner, GRAY_BG, GRAY_BORDER, styles))
            story.append(Spacer(1, 6))

        elif name == 'BOX_RED':
            # Strong red CTA box — white text, centered
            story.append(Spacer(1, 8))
            story.append(cta_box(inner, styles))
            story.append(Spacer(1, 8))

        elif name == 'BOX_PREP':
            # Preparation list — items separated by thin rules
            story.append(Spacer(1, 6))
            story.append(prep_box(inner, styles))
            story.append(Spacer(1, 6))

        elif name == 'BOX_QUOTE':
            story.append(Spacer(1, 6))
            story.append(callout_box(
                inner, QUOTE_BG, QUOTE_BORDER, styles, is_quote=True))
            story.append(Spacer(1, 6))

        # ── New tags ──────────────────────────────────────────────────────────
        elif name == 'STEP':
            # [STEP]Bold Title|Body description[/STEP]
            story.append(Spacer(1, 6))
            story.append(step_element(inner, styles))
            story.append(Spacer(1, 4))

        elif name == 'COMPONENT':
            story.append(Spacer(1, 8))
            story.append(component_card(inner, styles))
            story.append(Spacer(1, 6))

    return story


# ─── MAIN ENTRY POINT ────────────────────────────────────────────────────────
def generate_onboarding_pdf(markup_content, client_name):
    """
    Generate Fly Straight branded onboarding PDF from custom markup.
    Returns BytesIO buffer.

    Page callbacks:
      - Cover page (page 1): footer only, via draw_cover_page
      - All subsequent pages: header gold rule + label + footer,
        via draw_header_and_footer
    """
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.60 * inch,       # slightly tighter top — header rule sits here
        bottomMargin=0.75 * inch,
        title=f'Fly Straight Onboarding — {client_name}',
        author='Fly Straight Transformation',
    )

    styles = create_styles()
    story  = parse_markup_to_story(markup_content, styles)

    doc.build(
        story,
        onFirstPage=draw_cover_page,
        onLaterPages=draw_header_and_footer,
    )

    buffer.seek(0)
    return buffer
