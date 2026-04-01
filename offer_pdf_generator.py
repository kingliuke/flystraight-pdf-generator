"""
Fly Straight Fitness Offer PDF Generator
Parses custom markup tags and generates branded fitness offer PDFs

Changes from v3:
  - Added COVER_CLIENT tag: renders "Prepared Exclusively For:" as small
    gray label, client name at 16pt bold centered, location at 12pt gray
    centered. Format: [COVER_CLIENT]Name|City, Province[/COVER_CLIENT]
  - Added COMPONENT tag: wraps each component/upgrade card with light gray
    background, 3pt gold left border, and inner padding for visual grouping.
    Format: [COMPONENT]...[H4]name[/H4][BODY]desc[/BODY]...[/COMPONENT]
  - Added cover_client_* styles for COVER_CLIENT rendering
  - All v3 features retained (BOX_INVESTMENT, footer, H3/H4, bullet strip)
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

# ─── BRAND COLORS ───────────────────────────────────────────────────────────
BLACK       = colors.HexColor('#000000')
NEAR_BLACK  = colors.HexColor('#1A1A1A')
WHITE       = colors.HexColor('#FFFFFF')
GOLD        = colors.HexColor('#FFD000')
RED         = colors.HexColor('#9B0F12')

GREEN       = colors.HexColor('#1B5E20')
GREEN_LIGHT = colors.HexColor('#E8F5E9')
GREEN_BORDER= colors.HexColor('#2E7D32')

YELLOW_BG   = colors.HexColor('#FFFDE7')
YELLOW_BORDER = colors.HexColor('#F9A825')

RED_BG      = colors.HexColor('#FFEBEE')
RED_BORDER  = colors.HexColor('#C62828')

GRAY_BG     = colors.HexColor('#F5F5F5')
GRAY_BORDER = colors.HexColor('#424242')
GRAY        = colors.HexColor('#666666')
LIGHT_GRAY  = colors.HexColor('#EEEEEE')

QUOTE_BORDER = colors.HexColor('#2E7D32')
QUOTE_BG     = colors.HexColor('#F9FBE7')

TIMELINE_LINE  = GOLD
TIMELINE_DOT   = BLACK
TIMELINE_TEXT  = NEAR_BLACK


# ─── STYLES ─────────────────────────────────────────────────────────────────
def create_styles():
    styles = getSampleStyleSheet()

    return {
        # ── Headers ──────────────────────────────────────────────
        'h1': ParagraphStyle('CI_H1',
            fontName='Helvetica-Bold', fontSize=26,
            textColor=NEAR_BLACK, spaceAfter=10, spaceBefore=16,
            leading=30, alignment=TA_LEFT),

        'h2': ParagraphStyle('CI_H2',
            fontName='Helvetica-Bold', fontSize=18,
            textColor=RED, spaceAfter=8, spaceBefore=14,
            leading=22, alignment=TA_LEFT),

        # H3 spaceBefore increased 10 -> 20 for option header breathing room
        'h3': ParagraphStyle('CI_H3',
            fontName='Helvetica-Bold', fontSize=13,
            textColor=NEAR_BLACK, spaceAfter=6, spaceBefore=20,
            leading=16, alignment=TA_LEFT),

        # H4: component name header (added v2)
        'h4': ParagraphStyle('CI_H4',
            fontName='Helvetica-Bold', fontSize=11,
            textColor=NEAR_BLACK, spaceAfter=4, spaceBefore=8,
            leading=14, alignment=TA_LEFT),

        # ── Body ─────────────────────────────────────────────────
        'body': ParagraphStyle('CI_Body',
            fontName='Helvetica', fontSize=10,
            textColor=NEAR_BLACK, leading=15,
            alignment=TA_JUSTIFY, spaceAfter=8),

        'bold': ParagraphStyle('CI_Bold',
            fontName='Helvetica-Bold', fontSize=10,
            textColor=NEAR_BLACK, leading=15,
            alignment=TA_JUSTIFY, spaceAfter=8),

        'italic': ParagraphStyle('CI_Italic',
            fontName='Helvetica-Oblique', fontSize=10,
            textColor=GRAY, leading=15,
            alignment=TA_LEFT, spaceAfter=6),

        'pullquote': ParagraphStyle('CI_Pullquote',
            fontName='Helvetica-Bold', fontSize=14,
            textColor=RED, leading=20,
            alignment=TA_CENTER, spaceBefore=14, spaceAfter=14,
            leftIndent=40, rightIndent=40),

        # ── Box interiors ─────────────────────────────────────────
        'box_body': ParagraphStyle('CI_BoxBody',
            fontName='Helvetica', fontSize=10,
            textColor=NEAR_BLACK, leading=15,
            alignment=TA_LEFT, spaceAfter=4),

        'box_bold': ParagraphStyle('CI_BoxBold',
            fontName='Helvetica-Bold', fontSize=10,
            textColor=NEAR_BLACK, leading=15,
            alignment=TA_LEFT, spaceAfter=4),

        'quote_body': ParagraphStyle('CI_QuoteBody',
            fontName='Helvetica-Oblique', fontSize=11,
            textColor=NEAR_BLACK, leading=16,
            alignment=TA_LEFT, spaceAfter=4),

        # ── Investment box interiors (BOX_INVESTMENT) ─────────────
        'invest_label': ParagraphStyle('CI_InvestLabel',
            fontName='Helvetica-Bold', fontSize=10,
            textColor=NEAR_BLACK, leading=14,
            alignment=TA_CENTER, spaceAfter=2),

        'invest_amount': ParagraphStyle('CI_InvestAmount',
            fontName='Helvetica-Bold', fontSize=22,
            textColor=GREEN, leading=28,
            alignment=TA_CENTER, spaceAfter=4),

        'invest_body': ParagraphStyle('CI_InvestBody',
            fontName='Helvetica', fontSize=10,
            textColor=NEAR_BLACK, leading=14,
            alignment=TA_CENTER, spaceAfter=2),

        'invest_save': ParagraphStyle('CI_InvestSave',
            fontName='Helvetica-Bold', fontSize=11,
            textColor=GREEN, leading=15,
            alignment=TA_CENTER, spaceAfter=2),

        # ── Cover client block (COVER_CLIENT) ────────────────────
        'cover_label': ParagraphStyle('CI_CoverLabel',
            fontName='Helvetica', fontSize=9,
            textColor=GRAY, leading=13,
            alignment=TA_CENTER, spaceAfter=4),

        'cover_name': ParagraphStyle('CI_CoverName',
            fontName='Helvetica-Bold', fontSize=16,
            textColor=NEAR_BLACK, leading=20,
            alignment=TA_CENTER, spaceAfter=4),

        'cover_location': ParagraphStyle('CI_CoverLocation',
            fontName='Helvetica', fontSize=12,
            textColor=GRAY, leading=16,
            alignment=TA_CENTER, spaceAfter=8),

        # ── Brand bar ─────────────────────────────────────────────
        'brand_bar': ParagraphStyle('CI_BrandBar',
            fontName='Helvetica-Bold', fontSize=14,
            textColor=WHITE, leading=20,
            alignment=TA_CENTER),

        # ── Section banners ───────────────────────────────────────
        'banner_text': ParagraphStyle('CI_BannerText',
            fontName='Helvetica-Bold', fontSize=13,
            textColor=WHITE, leading=18,
            alignment=TA_LEFT),

        # ── Client info ───────────────────────────────────────────
        'client_info': ParagraphStyle('CI_ClientInfo',
            fontName='Helvetica', fontSize=12,
            textColor=GRAY, leading=16,
            alignment=TA_LEFT, spaceAfter=4),

        # ── Note / small ──────────────────────────────────────────
        'note': ParagraphStyle('CI_Note',
            fontName='Helvetica', fontSize=9,
            textColor=GRAY, leading=12,
            alignment=TA_LEFT, spaceAfter=4),

        # ── Checklist ─────────────────────────────────────────────
        'checklist': ParagraphStyle('CI_Checklist',
            fontName='Helvetica', fontSize=10,
            textColor=NEAR_BLACK, leading=16,
            alignment=TA_LEFT, spaceAfter=3,
            leftIndent=12),

        # ── Metric ────────────────────────────────────────────────
        'metric_label': ParagraphStyle('CI_MetricLabel',
            fontName='Helvetica', fontSize=9,
            textColor=GRAY, leading=12,
            alignment=TA_CENTER),

        'metric_value': ParagraphStyle('CI_MetricValue',
            fontName='Helvetica-Bold', fontSize=28,
            textColor=NEAR_BLACK, leading=32,
            alignment=TA_CENTER),

        'metric_unit': ParagraphStyle('CI_MetricUnit',
            fontName='Helvetica', fontSize=10,
            textColor=GRAY, leading=14,
            alignment=TA_CENTER),

        # ── Timeline ─────────────────────────────────────────────
        'timeline_week': ParagraphStyle('CI_TimelineWeek',
            fontName='Helvetica-Bold', fontSize=10,
            textColor=NEAR_BLACK, leading=14,
            alignment=TA_LEFT),

        'timeline_text': ParagraphStyle('CI_TimelineText',
            fontName='Helvetica', fontSize=10,
            textColor=NEAR_BLACK, leading=14,
            alignment=TA_LEFT),

        'timeline_next': ParagraphStyle('CI_TimelineNext',
            fontName='Helvetica-Oblique', fontSize=10,
            textColor=RED, leading=14,
            alignment=TA_LEFT),
    }


# ─── HELPER: inline markup ───────────────────────────────────────────────────
def apply_inline(text):
    """Convert **bold** and *italic* to ReportLab XML tags."""
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.+?)\*',     r'<i>\1</i>', text)
    return text


# ─── HELPER: horizontal gold rule ───────────────────────────────────────────
def gold_rule():
    return HRFlowable(width='100%', thickness=2, color=GOLD,
                      spaceBefore=10, spaceAfter=10)


# ─── HELPER: full-width colored banner ──────────────────────────────────────
def section_banner(text, bg_color, styles):
    data = [[Paragraph(f'<b>{text}</b>', styles['banner_text'])]]
    t = Table(data, colWidths=[6.5 * inch])
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), bg_color),
        ('LEFTPADDING',   (0, 0), (-1, -1), 14),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 14),
        ('TOPPADDING',    (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('ROWBACKGROUNDS',(0, 0), (-1, -1), [bg_color]),
    ]))
    return t


# ─── HELPER: header bar (brand bar) ─────────────────────────────────────────
def header_bar(text, styles):
    data = [[Paragraph(f'<b>{text}</b>', styles['brand_bar'])]]
    t = Table(data, colWidths=[6.5 * inch])
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), BLACK),
        ('LEFTPADDING',   (0, 0), (-1, -1), 14),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 14),
        ('TOPPADDING',    (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    return t


# ─── HELPER: callout box ────────────────────────────────────────────────────
def callout_box(text, bg, border, styles, is_quote=False):
    style = styles['quote_body'] if is_quote else styles['box_body']
    lines = text.strip().split('\n')
    paragraphs = []
    for line in lines:
        line = line.strip()
        if not line:
            paragraphs.append(Spacer(1, 4))
            continue
        # Safety net: strip leading bullet/dash characters if the model
        # produces them inside a box despite the prose mandate.
        if line.startswith(('- ', '• ', '* ')):
            line = line[2:]
        line = apply_inline(line)
        paragraphs.append(Paragraph(line, style))

    inner = Table([[p] for p in paragraphs],
                  colWidths=[6.1 * inch])
    inner.setStyle(TableStyle([
        ('LEFTPADDING',   (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
        ('TOPPADDING',    (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('BACKGROUND',    (0, 0), (-1, -1), bg),
    ]))

    outer = Table([[inner]], colWidths=[6.5 * inch])
    outer.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), bg),
        ('BOX',           (0, 0), (-1, -1), 2, border),
        ('LEFTPADDING',   (0, 0), (-1, -1), 14),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 14),
        ('TOPPADDING',    (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    return outer


# ─── HELPER: investment box (BOX_INVESTMENT) ────────────────────────────────
def investment_box(text, styles):
    """
    Renders BOX_INVESTMENT — a visually prominent value stacking block.

    Expected content (one field per line):
        Total Standalone Value: $3,540
        Your Investment: $997 USD ($1,356 CAD)
        You Save: $2,543 — 72%
        [any additional lines rendered as body text]

    Rendering rules:
    - "Your Investment:" line  → label in normal bold + large green amount
    - "Total Standalone Value:" → bold body centred
    - "You Save:"               → bold green centred
    - All other lines           → normal body centred
    """
    lines = [l.strip() for l in text.strip().split('\n') if l.strip()]
    rows = []

    for line in lines:
        # Strip leading bullet/dash if present
        if line.startswith(('- ', '• ', '* ')):
            line = line[2:]
        line_rendered = apply_inline(line)
        lower = line.lower()

        if lower.startswith('your investment:'):
            parts = line.split(':', 1)
            label  = parts[0].strip() + ':'
            amount = parts[1].strip() if len(parts) > 1 else ''
            rows.append(Paragraph(f'<b>{label}</b>', styles['invest_label']))
            rows.append(Paragraph(amount, styles['invest_amount']))

        elif lower.startswith('you save:'):
            rows.append(Paragraph(f'<b>{line_rendered}</b>',
                                   styles['invest_save']))

        elif lower.startswith('total standalone value:'):
            rows.append(Paragraph(f'<b>{line_rendered}</b>',
                                   styles['invest_body']))

        else:
            rows.append(Paragraph(line_rendered, styles['invest_body']))

    if not rows:
        return Spacer(1, 4)

    inner = Table([[r] for r in rows], colWidths=[6.1 * inch])
    inner.setStyle(TableStyle([
        ('LEFTPADDING',   (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
        ('TOPPADDING',    (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('BACKGROUND',    (0, 0), (-1, -1), GREEN_LIGHT),
    ]))

    outer = Table([[inner]], colWidths=[6.5 * inch])
    outer.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), GREEN_LIGHT),
        ('BOX',           (0, 0), (-1, -1), 2, GREEN_BORDER),
        ('LEFTPADDING',   (0, 0), (-1, -1), 14),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 14),
        ('TOPPADDING',    (0, 0), (-1, -1), 14),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
    ]))
    return outer


# ─── HELPER: cover client block (COVER_CLIENT) ──────────────────────────────
def cover_client_block(content, styles):
    """
    Renders COVER_CLIENT tag — the cover page client name block.

    Format: [COVER_CLIENT]Client Full Name|City, Province[/COVER_CLIENT]
    The pipe character separates name from location.

    Renders as:
      "Prepared Exclusively For:"  — 9pt gray centered label
      "Client Full Name"           — 16pt bold centered
      "City, Province"             — 12pt gray centered
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

    t = Table(rows, colWidths=[6.5 * inch])
    t.setStyle(TableStyle([
        ('LEFTPADDING',   (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
        ('TOPPADDING',    (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    return t


# ─── HELPER: component card (COMPONENT) ──────────────────────────────────────
def component_card(inner_content, styles):
    """
    Renders COMPONENT tag — a visual card wrapping each component or upgrade.

    Inner content is parsed recursively as markup (H4 + BODY tags).
    Renders with:
      - Light gray background (GRAY_BG)
      - 3pt gold left border
      - 12pt horizontal padding, 10pt vertical padding
    """
    # Parse the inner markup into flowables
    inner_story = parse_markup_to_story(inner_content, styles)

    if not inner_story:
        return Spacer(1, 4)

    # Wrap inner flowables in a single-column table for padding
    rows = [[item] for item in inner_story]
    inner_table = Table(rows, colWidths=[6.0 * inch])
    inner_table.setStyle(TableStyle([
        ('LEFTPADDING',   (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
        ('TOPPADDING',    (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('BACKGROUND',    (0, 0), (-1, -1), GRAY_BG),
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
    ]))

    # Outer table: gold left border + padding
    outer = Table([[inner_table]], colWidths=[6.5 * inch])
    outer.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), GRAY_BG),
        ('LEFTPADDING',   (0, 0), (-1, -1), 14),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 14),
        ('TOPPADDING',    (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LINEBEFORE',    (0, 0), (0, -1),  3, GOLD),
    ]))
    return outer


# ─── HELPER: metric display ─────────────────────────────────────────────────
def metric_element(label, value, unit, styles):
    data = [[
        Paragraph(label, styles['metric_label']),
        Paragraph(f'<b>{value}</b>', styles['metric_value']),
        Paragraph(unit, styles['metric_unit']),
    ]]
    t = Table(data, colWidths=[2.0*inch, 2.5*inch, 2.0*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), LIGHT_GRAY),
        ('BOX',           (0, 0), (-1, -1), 1, GOLD),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING',   (0, 0), (-1, -1), 10),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 10),
        ('TOPPADDING',    (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    return t


# ─── HELPER: parse pipe table ────────────────────────────────────────────────
def parse_pipe_table(raw):
    lines = [l.strip() for l in raw.strip().split('\n') if l.strip()]
    lines = [l for l in lines if not re.match(r'^\|[\s\-\|:]+\|$', l)]
    rows = []
    for line in lines:
        cells = [c.strip() for c in line.strip('|').split('|')]
        rows.append(cells)
    return rows


def styled_table(rows, col_widths=None, header_bg=BLACK):
    if not rows:
        return Spacer(1, 4)
    num_cols = len(rows[0])
    available = 6.5 * inch
    if not col_widths:
        col_widths = [available / num_cols] * num_cols

    styled_rows = []
    for i, row in enumerate(rows):
        styled_row = []
        for cell in row:
            cell = apply_inline(str(cell))
            if i == 0:
                p = Paragraph(f'<b>{cell}</b>', ParagraphStyle(
                    'TableHeader', fontName='Helvetica-Bold',
                    fontSize=9, textColor=WHITE, leading=13))
            else:
                p = Paragraph(cell, ParagraphStyle(
                    'TableCell', fontName='Helvetica',
                    fontSize=9, textColor=NEAR_BLACK, leading=13))
            styled_row.append(p)
        styled_rows.append(styled_row)

    t = Table(styled_rows, colWidths=col_widths)
    style_cmds = [
        ('BACKGROUND',    (0, 0), (-1, 0),  header_bg),
        ('TEXTCOLOR',     (0, 0), (-1, 0),  WHITE),
        ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, -1), 9),
        ('ALIGN',         (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('GRID',          (0, 0), (-1, -1), 0.5, GOLD),
        ('LEFTPADDING',   (0, 0), (-1, -1), 8),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
        ('TOPPADDING',    (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]
    for i in range(1, len(styled_rows)):
        bg = WHITE if i % 2 == 1 else LIGHT_GRAY
        style_cmds.append(('BACKGROUND', (0, i), (-1, i), bg))

    t.setStyle(TableStyle(style_cmds))
    return t


# ─── HELPER: weight + waist table (6 columns) ───────────────────────────────
def styled_table_weight_waist(rows):
    """
    Renders TABLE_WEIGHT_WAIST — 6 columns:
    Week | Date | Weight | Change | Waist | Change
    """
    if not rows:
        return Spacer(1, 4)

    col_widths = [
        0.85 * inch,
        1.05 * inch,
        0.90 * inch,
        0.85 * inch,
        0.90 * inch,
        0.95 * inch,
    ]

    header_style = ParagraphStyle(
        'WWHeader', fontName='Helvetica-Bold',
        fontSize=8, textColor=WHITE, leading=12, alignment=TA_CENTER)

    cell_style = ParagraphStyle(
        'WWCell', fontName='Helvetica',
        fontSize=8, textColor=NEAR_BLACK, leading=12, alignment=TA_CENTER)

    cell_bold = ParagraphStyle(
        'WWCellBold', fontName='Helvetica-Bold',
        fontSize=8, textColor=NEAR_BLACK, leading=12, alignment=TA_CENTER)

    def change_color(text, col_type):
        t = str(text).strip()
        if t in ('', '—', '-', '[not measured]', 'not measured'):
            return Paragraph(t, cell_style)
        if col_type == 'weight':
            if t.startswith('-'):
                return Paragraph(
                    f'<font color="#1B5E20"><b>{t}</b></font>', cell_style)
            elif t.startswith('+'):
                return Paragraph(
                    f'<font color="#9B0F12"><b>{t}</b></font>', cell_style)
        elif col_type == 'waist':
            if t.startswith('-'):
                return Paragraph(
                    f'<font color="#1B5E20"><b>{t}</b></font>', cell_style)
        return Paragraph(t, cell_style)

    styled_rows = []
    for i, row in enumerate(rows):
        while len(row) < 6:
            row.append('')

        if i == 0:
            styled_row = [
                Paragraph(f'<b>{apply_inline(str(c))}</b>', header_style)
                for c in row[:6]
            ]
        else:
            styled_row = [
                Paragraph(apply_inline(str(row[0])), cell_bold),
                Paragraph(apply_inline(str(row[1])), cell_style),
                Paragraph(apply_inline(str(row[2])), cell_style),
                change_color(row[3], 'weight'),
                Paragraph(apply_inline(str(row[4])), cell_style),
                change_color(row[5], 'waist'),
            ]
        styled_rows.append(styled_row)

    t = Table(styled_rows, colWidths=col_widths)
    style_cmds = [
        ('BACKGROUND',    (0, 0), (-1, 0),  BLACK),
        ('TEXTCOLOR',     (0, 0), (-1, 0),  WHITE),
        ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, -1), 8),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID',          (0, 0), (-1, -1), 0.5, GOLD),
        ('LEFTPADDING',   (0, 0), (-1, -1), 5),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 5),
        ('TOPPADDING',    (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('BACKGROUND',    (4, 1), (5, -1),  colors.HexColor('#F1F8E9')),
    ]
    for i in range(1, len(styled_rows)):
        bg = WHITE if i % 2 == 1 else LIGHT_GRAY
        style_cmds.append(('BACKGROUND', (0, i), (3, i), bg))
        style_cmds.append(('BACKGROUND', (4, i), (5, i),
                            colors.HexColor('#F1F8E9')))

    t.setStyle(TableStyle(style_cmds))
    return t


# ─── HELPER: styled table for fitness offer options ─────────────────────────
def styled_table_options(rows):
    """
    Styled table for fitness offer options comparison.
    Columns: Option | Duration | Weight Loss | Projected Weight | Investment
    Highlights recommended option (★) in green.
    """
    if not rows:
        return Spacer(1, 4)

    col_widths = [
        1.4 * inch,
        0.9 * inch,
        1.1 * inch,
        1.2 * inch,
        1.9 * inch,
    ]

    header_style = ParagraphStyle(
        'OptHeader', fontName='Helvetica-Bold',
        fontSize=9, textColor=WHITE, leading=13, alignment=TA_CENTER)

    cell_style = ParagraphStyle(
        'OptCell', fontName='Helvetica',
        fontSize=9, textColor=NEAR_BLACK, leading=13, alignment=TA_CENTER)

    cell_bold = ParagraphStyle(
        'OptCellBold', fontName='Helvetica-Bold',
        fontSize=9, textColor=NEAR_BLACK, leading=13, alignment=TA_CENTER)

    styled_rows = []
    for i, row in enumerate(rows):
        while len(row) < 5:
            row.append('')

        if i == 0:
            styled_row = [
                Paragraph(f'<b>{apply_inline(str(c))}</b>', header_style)
                for c in row[:5]
            ]
        else:
            option_name    = str(row[0])
            is_recommended = '★' in option_name
            style_first    = cell_bold if is_recommended else cell_style

            styled_row = [
                Paragraph(apply_inline(option_name), style_first),
                Paragraph(apply_inline(str(row[1])), cell_style),
                Paragraph(apply_inline(str(row[2])), cell_bold),
                Paragraph(apply_inline(str(row[3])), cell_style),
                Paragraph(apply_inline(str(row[4])), cell_style),
            ]
        styled_rows.append(styled_row)

    t = Table(styled_rows, colWidths=col_widths)
    style_cmds = [
        ('BACKGROUND',    (0, 0), (-1, 0),  BLACK),
        ('TEXTCOLOR',     (0, 0), (-1, 0),  WHITE),
        ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, -1), 9),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID',          (0, 0), (-1, -1), 1, GOLD),
        ('LEFTPADDING',   (0, 0), (-1, -1), 8),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
        ('TOPPADDING',    (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]
    for i in range(1, len(styled_rows)):
        row_text = str(rows[i][0])
        if '★' in row_text:
            style_cmds.append(('BACKGROUND', (0, i), (-1, i), GREEN_LIGHT))
        else:
            bg = WHITE if i % 2 == 1 else LIGHT_GRAY
            style_cmds.append(('BACKGROUND', (0, i), (-1, i), bg))

    t.setStyle(TableStyle(style_cmds))
    return t


# ─── HELPER: checklist ──────────────────────────────────────────────────────
def checklist_element(content, styles):
    items = []
    for line in content.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        line = apply_inline(line)
        if line.startswith('✓'):
            color_text = f'<font color="#1B5E20">✓</font> {line[1:].strip()}'
        elif line.startswith('~'):
            color_text = f'<font color="#F9A825">~</font> {line[1:].strip()}'
        elif line.startswith('✗'):
            color_text = f'<font color="#C62828">✗</font> {line[1:].strip()}'
        else:
            color_text = line
        items.append(Paragraph(color_text, styles['checklist']))

    if not items:
        return Spacer(1, 4)

    outer = Table([[item] for item in items], colWidths=[6.5 * inch])
    outer.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), GRAY_BG),
        ('BOX',           (0, 0), (-1, -1), 1, GRAY_BORDER),
        ('LEFTPADDING',   (0, 0), (-1, -1), 14),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 14),
        ('TOPPADDING',    (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('ROWPADDING',    (0, 0), (-1, -1), 3),
    ]))
    return outer


# ─── HELPER: photo notes ────────────────────────────────────────────────────
def photo_notes_element(content, styles):
    rows = []
    for line in content.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        if ':' in line:
            label, _, text = line.partition(':')
            label = label.strip()
            text  = apply_inline(text.strip())
            rows.append([
                Paragraph(f'<b>{label}</b>', styles['box_bold']),
                Paragraph(text, styles['box_body']),
            ])

    if not rows:
        return Spacer(1, 4)

    t = Table(rows, colWidths=[1.0*inch, 5.5*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), GRAY_BG),
        ('BOX',           (0, 0), (-1, -1), 1, GRAY_BORDER),
        ('LINEAFTER',     (0, 0), (0, -1),  1, GRAY_BORDER),
        ('LEFTPADDING',   (0, 0), (-1, -1), 10),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 10),
        ('TOPPADDING',    (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME',      (0, 0), (0, -1),  'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, -1), 9),
        ('LINEBELOW',     (0, 0), (-1, -2), 0.5, LIGHT_GRAY),
    ]))
    return t


# ─── HELPER: week arc / timeline ─────────────────────────────────────────────
def week_arc_element(content, styles):
    """
    Renders WEEK_ARC as a vertical timeline.
    Each line: "Week X (date): text"
    Last line uses italic red style.
    """
    lines = [l.strip() for l in content.strip().split('\n') if l.strip()]
    if not lines:
        return Spacer(1, 4)

    rows = []
    for idx, line in enumerate(lines):
        is_last = (idx == len(lines) - 1)

        match = re.match(
            r'^(Week\s+\S+(?:\s+\([^)]+\))?)\s*:\s*(.+)$',
            line, re.IGNORECASE)
        if match:
            week_label = match.group(1).strip()
            week_text  = apply_inline(match.group(2).strip())
        else:
            week_label = ''
            week_text  = apply_inline(line)

        text_style  = styles['timeline_next'] if is_last else styles['timeline_text']
        label_style = styles['timeline_week']
        dot_color   = RED if is_last else BLACK

        dot_table = Table(
            [[Paragraph('', ParagraphStyle('dot', fontSize=1))]],
            colWidths=[0.15*inch], rowHeights=[0.15*inch]
        )
        dot_table.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), dot_color),
            ('TOPPADDING',    (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING',   (0, 0), (-1, -1), 0),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
        ]))

        rows.append([
            dot_table,
            Paragraph(f'<b>{week_label}</b>', label_style),
            Paragraph(week_text, text_style),
        ])

    t = Table(rows, colWidths=[0.25*inch, 1.3*inch, 4.95*inch])
    style_cmds = [
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING',   (0, 0), (-1, -1), 4),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('BACKGROUND',    (0, 0), (-1, -1), GRAY_BG),
        ('BOX',           (0, 0), (-1, -1), 1, GRAY_BORDER),
        ('LINEBELOW',     (0, 0), (-1, -2), 0.5, LIGHT_GRAY),
        ('LEFTPADDING',   (1, 0), (1, -1),  8),
    ]
    t.setStyle(TableStyle(style_cmds))

    outer = Table([[t]], colWidths=[6.5*inch])
    outer.setStyle(TableStyle([
        ('LEFTPADDING',   (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
        ('TOPPADDING',    (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('LINEBEFORE',    (0, 0), (0, -1),  4, GOLD),
    ]))
    return outer


# ─── FOOTER CALLBACK ─────────────────────────────────────────────────────────
def draw_footer(canvas, doc):
    """Draw 'FLY STRAIGHT TRANSFORMATION' centred footer on every page."""
    canvas.saveState()
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(GRAY)
    page_width = letter[0]
    canvas.drawCentredString(
        page_width / 2.0,
        0.45 * inch,
        'FLY STRAIGHT TRANSFORMATION'
    )
    canvas.restoreState()


# ─── MAIN PARSER ────────────────────────────────────────────────────────────
def parse_markup_to_story(markup, styles):
    story = []

    # Normalise line endings
    markup = markup.replace('\r\n', '\n').replace('\r', '\n')

    # First pass: extract all tags
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

        if m.group(1):   # paired tag
            name      = m.group(1)
            attrs_raw = m.group(2) or ''
            inner     = m.group(3) or ''
        else:            # self-closing
            name      = m.group(4)
            attrs_raw = m.group(5) or ''
            inner     = ''

        attrs = dict(re.findall(r'(\w+)="([^"]*)"', attrs_raw))
        tokens.append(('tag', name, attrs, inner))
        last = m.end()

    if last < len(full):
        tokens.append(('text', full[last:]))

    # Second pass: render tokens
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

        # ── Layout ──────────────────────────────────────────────
        if name == 'PAGE_BREAK':
            story.append(PageBreak())

        elif name == 'GOLD_RULE':
            story.append(gold_rule())

        elif name == 'HEADER_BAR':
            story.append(Spacer(1, 6))
            story.append(header_bar(inner.strip(), styles))
            story.append(Spacer(1, 6))

        elif name == 'SECTION_BANNER_GREEN':
            story.append(Spacer(1, 8))
            story.append(section_banner(inner.strip(), GREEN, styles))
            story.append(Spacer(1, 8))

        elif name == 'SECTION_BANNER_BLACK':
            story.append(Spacer(1, 8))
            story.append(section_banner(inner.strip(), BLACK, styles))
            story.append(Spacer(1, 8))

        elif name == 'SECTION_BANNER_RED':
            story.append(Spacer(1, 8))
            story.append(section_banner(inner.strip(), RED, styles))
            story.append(Spacer(1, 8))

        elif name == 'COVER_CLIENT':
            # Cover page client name block — added v4
            story.append(Spacer(1, 16))
            story.append(cover_client_block(inner, styles))
            story.append(Spacer(1, 16))

        # ── Text ────────────────────────────────────────────────
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
            # Component name header — added v2
            story.append(Spacer(1, 4))
            story.append(Paragraph(apply_inline(inner.strip()), styles['h4']))

        elif name == 'BODY':
            story.append(Paragraph(apply_inline(inner.strip()), styles['body']))
            story.append(Spacer(1, 4))

        elif name == 'BOLD':
            story.append(Paragraph(
                f'<b>{apply_inline(inner.strip())}</b>', styles['body']))

        elif name == 'ITALIC':
            story.append(Paragraph(
                f'<i>{apply_inline(inner.strip())}</i>', styles['italic']))

        elif name == 'PULLQUOTE':
            story.append(Spacer(1, 8))
            story.append(Paragraph(apply_inline(inner.strip()),
                                   styles['pullquote']))
            story.append(Spacer(1, 8))

        # ── Callout boxes ────────────────────────────────────────
        elif name == 'BOX_GREEN':
            story.append(Spacer(1, 6))
            story.append(callout_box(inner, GREEN_LIGHT, GREEN_BORDER, styles))
            story.append(Spacer(1, 6))

        elif name == 'BOX_YELLOW':
            story.append(Spacer(1, 6))
            story.append(callout_box(inner, YELLOW_BG, YELLOW_BORDER, styles))
            story.append(Spacer(1, 6))

        elif name == 'BOX_RED':
            story.append(Spacer(1, 6))
            story.append(callout_box(inner, RED_BG, RED_BORDER, styles))
            story.append(Spacer(1, 6))

        elif name == 'BOX_BLACK':
            story.append(Spacer(1, 6))
            story.append(callout_box(inner, GRAY_BG, GRAY_BORDER, styles))
            story.append(Spacer(1, 6))

        elif name == 'BOX_QUOTE':
            story.append(Spacer(1, 6))
            story.append(callout_box(
                inner, QUOTE_BG, QUOTE_BORDER, styles, is_quote=True))
            story.append(Spacer(1, 6))

        elif name == 'BOX_INVESTMENT':
            # Dedicated value stacking renderer — added v3
            story.append(Spacer(1, 8))
            story.append(investment_box(inner, styles))
            story.append(Spacer(1, 8))

        elif name == 'COMPONENT':
            # Component/upgrade card — added v4
            story.append(Spacer(1, 8))
            story.append(component_card(inner, styles))
            story.append(Spacer(1, 6))

        # ── Tables ───────────────────────────────────────────────
        elif name == 'TABLE_WEIGHT_WAIST':
            rows = parse_pipe_table(inner)
            if rows:
                story.append(Spacer(1, 6))
                story.append(styled_table_weight_waist(rows))
                story.append(Spacer(1, 10))

        elif name in ('TABLE_MACRO', 'TABLE_SESSIONS', 'TABLE_ACTIONS',
                      'TABLE_QUESTIONS', 'TABLE_WEIGHT'):
            rows = parse_pipe_table(inner)
            if rows:
                story.append(Spacer(1, 6))
                story.append(styled_table(rows))
                story.append(Spacer(1, 10))

        elif name == 'TABLE_OPTIONS':
            rows = parse_pipe_table(inner)
            if rows:
                story.append(Spacer(1, 6))
                story.append(styled_table_options(rows))
                story.append(Spacer(1, 10))

        # ── Special ──────────────────────────────────────────────
        elif name == 'METRIC':
            label = attrs.get('label', '')
            value = attrs.get('value', '')
            unit  = attrs.get('unit', '')
            story.append(Spacer(1, 6))
            story.append(metric_element(label, value, unit, styles))
            story.append(Spacer(1, 6))

        elif name == 'CHECKLIST':
            story.append(Spacer(1, 6))
            story.append(checklist_element(inner, styles))
            story.append(Spacer(1, 6))

        elif name == 'PHOTO_NOTES':
            story.append(Spacer(1, 6))
            story.append(photo_notes_element(inner, styles))
            story.append(Spacer(1, 6))

        elif name == 'WEEK_ARC':
            story.append(Spacer(1, 8))
            story.append(week_arc_element(inner, styles))
            story.append(Spacer(1, 8))

    return story


# ─── MAIN ENTRY POINT ────────────────────────────────────────────────────────
def generate_offer_pdf(markup_content, client_name):
    """
    Generate Fly Straight branded fitness offer PDF from custom markup.
    Returns BytesIO buffer.
    """
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title=f'Fly Straight Fitness Offer — {client_name}',
        author='Fly Straight Transformation',
    )

    styles = create_styles()
    story  = parse_markup_to_story(markup_content, styles)

    # Build with footer callback on every page
    doc.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)
    buffer.seek(0)
    return buffer
