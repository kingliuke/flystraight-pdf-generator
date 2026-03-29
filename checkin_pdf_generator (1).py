"""
Fly Straight Check-In PDF Generator
Parses custom markup tags and generates branded weekly check-in PDFs
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

        'h3': ParagraphStyle('CI_H3',
            fontName='Helvetica-Bold', fontSize=13,
            textColor=NEAR_BLACK, spaceAfter=6, spaceBefore=10,
            leading=16, alignment=TA_LEFT),

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
        ('BACKGROUND',   (0, 0), (-1, -1), bg_color),
        ('LEFTPADDING',  (0, 0), (-1, -1), 14),
        ('RIGHTPADDING', (0, 0), (-1, -1), 14),
        ('TOPPADDING',   (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 10),
        ('ROWBACKGROUNDS',(0,0),(-1,-1),[bg_color]),
    ]))
    return t


# ─── HELPER: header bar (brand bar) ─────────────────────────────────────────
def header_bar(text, styles):
    data = [[Paragraph(f'<b>{text}</b>', styles['brand_bar'])]]
    t = Table(data, colWidths=[6.5 * inch])
    t.setStyle(TableStyle([
        ('BACKGROUND',   (0, 0), (-1, -1), BLACK),
        ('LEFTPADDING',  (0, 0), (-1, -1), 14),
        ('RIGHTPADDING', (0, 0), (-1, -1), 14),
        ('TOPPADDING',   (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 10),
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

    # Convert text to Paragraph objects
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
    # Alternating row backgrounds (skip header)
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
    Uses tighter column widths to fit 6 cols on the page.
    Weight change column uses red text for gains, green for losses.
    Waist change column uses green text for reductions.
    """
    if not rows:
        return Spacer(1, 4)

    # Column widths — tighter to fit 6 cols in 6.5 inches
    col_widths = [
        0.85 * inch,   # Week
        1.05 * inch,   # Date
        0.90 * inch,   # Weight
        0.85 * inch,   # Change (weight)
        0.90 * inch,   # Waist
        0.95 * inch,   # Change (waist)
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
        """Color weight changes red/green, waist changes green/gray."""
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
        # Pad row to 6 cols if shorter
        while len(row) < 6:
            row.append('')

        if i == 0:
            # Header row
            styled_row = [
                Paragraph(f'<b>{apply_inline(str(c))}</b>', header_style)
                for c in row[:6]
            ]
        else:
            # Data rows — col 0=week, 1=date, 2=weight, 3=wt change,
            #              4=waist, 5=waist change
            styled_row = [
                Paragraph(apply_inline(str(row[0])), cell_bold),   # Week
                Paragraph(apply_inline(str(row[1])), cell_style),  # Date
                Paragraph(apply_inline(str(row[2])), cell_style),  # Weight
                change_color(row[3], 'weight'),                     # Wt change
                Paragraph(apply_inline(str(row[4])), cell_style),  # Waist
                change_color(row[5], 'waist'),                      # Waist change
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
        # Light green tint on waist columns to visually group them
        ('BACKGROUND',    (4, 1), (5, -1),  colors.HexColor('#F1F8E9')),
    ]
    # Alternating row backgrounds on weight columns only
    for i in range(1, len(styled_rows)):
        bg = WHITE if i % 2 == 1 else LIGHT_GRAY
        style_cmds.append(('BACKGROUND', (0, i), (3, i), bg))
        # Keep waist columns with light green tint regardless of row
        style_cmds.append(('BACKGROUND', (4, i), (5, i),
                            colors.HexColor('#F1F8E9')))

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
            text = apply_inline(text.strip())
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
    Renders the WEEK_ARC block as a vertical timeline:
    Each line: "Week X (date): text"
    The last line (next week) uses italic red style.
    """
    lines = [l.strip() for l in content.strip().split('\n') if l.strip()]
    if not lines:
        return Spacer(1, 4)

    rows = []
    for idx, line in enumerate(lines):
        is_last = (idx == len(lines) - 1)

        # Parse "Week X (date): text" — flexible
        match = re.match(r'^(Week\s+\S+(?:\s+\([^)]+\))?)\s*:\s*(.+)$', line, re.IGNORECASE)
        if match:
            week_label = match.group(1).strip()
            week_text  = apply_inline(match.group(2).strip())
        else:
            week_label = ''
            week_text  = apply_inline(line)

        text_style = styles['timeline_next'] if is_last else styles['timeline_text']
        label_style = styles['timeline_week']

        dot_color = RED if is_last else BLACK

        # Dot column — draw as a small colored square via a single-cell table
        dot_table = Table(
            [[Paragraph('', ParagraphStyle('dot', fontSize=1))]],
            colWidths=[0.15*inch], rowHeights=[0.15*inch]
        )
        dot_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), dot_color),
            ('TOPPADDING',    (0,0),(-1,-1), 0),
            ('BOTTOMPADDING', (0,0),(-1,-1), 0),
            ('LEFTPADDING',   (0,0),(-1,-1), 0),
            ('RIGHTPADDING',  (0,0),(-1,-1), 0),
        ]))

        rows.append([
            dot_table,
            Paragraph(f'<b>{week_label}</b>', label_style),
            Paragraph(week_text, text_style),
        ])

    # Build the full timeline table
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
        ('LEFTPADDING',   (1, 0), (1, -1), 8),
    ]
    t.setStyle(TableStyle(style_cmds))

    # Wrap in outer container with gold left border effect
    outer = Table([[t]], colWidths=[6.5*inch])
    outer.setStyle(TableStyle([
        ('LEFTPADDING',   (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
        ('TOPPADDING',    (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('LINEBEFORE',    (0, 0), (0, -1),  4, GOLD),
    ]))
    return outer


# ─── MAIN PARSER ────────────────────────────────────────────────────────────
def parse_markup_to_story(markup, styles):
    story = []

    # Normalise line endings
    markup = markup.replace('\r\n', '\n').replace('\r', '\n')

    # Tag pattern: [TAG]...[/TAG] or self-closing [TAG ...]
    tag_pattern = re.compile(
        r'\[([A-Z_0-9]+)(?:\s[^\]]+)?\](?:(.*?)\[/\1\]|)',
        re.DOTALL
    )

    # We'll do a positional scan
    pos = 0
    text_buf = []

    def flush_text():
        nonlocal text_buf
        for line in text_buf:
            line = line.strip()
            if not line:
                story.append(Spacer(1, 4))
                continue
            story.append(Paragraph(apply_inline(line), styles['body']))
        text_buf = []

    # Tokenise into a flat list: ('text', content) or ('tag', name, attrs, inner)
    tokens = []
    i = 0
    full = markup

    # First pass: extract all tags with their positions
    tag_re = re.compile(
        r'\[([A-Z_0-9]+)((?:\s+[a-z_]+="[^"]*")*)\](.*?)\[/\1\]'
        r'|\[([A-Z_0-9]+)((?:\s+[a-z_]+="[^"]*")*)\]',
        re.DOTALL
    )

    last = 0
    for m in tag_re.finditer(full):
        # Text before this tag
        if m.start() > last:
            tokens.append(('text', full[last:m.start()]))

        if m.group(1):  # paired tag
            name  = m.group(1)
            attrs_raw = m.group(2) or ''
            inner = m.group(3) or ''
        else:           # self-closing
            name  = m.group(4)
            attrs_raw = m.group(5) or ''
            inner = ''

        # Parse attrs key="value"
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

        elif name == 'BODY':
            story.append(Paragraph(apply_inline(inner.strip()), styles['body']))
            story.append(Spacer(1, 4))

        elif name == 'BOLD':
            story.append(Paragraph(f'<b>{apply_inline(inner.strip())}</b>', styles['body']))

        elif name == 'ITALIC':
            story.append(Paragraph(f'<i>{apply_inline(inner.strip())}</i>', styles['italic']))

        elif name == 'PULLQUOTE':
            story.append(Spacer(1, 8))
            story.append(Paragraph(apply_inline(inner.strip()), styles['pullquote']))
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
            story.append(callout_box(inner, QUOTE_BG, QUOTE_BORDER, styles, is_quote=True))
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
def generate_checkin_pdf(markup_content, client_name):
    """
    Generate Fly Straight branded check-in PDF from custom markup.
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
        title=f'Fly Straight Check-In — {client_name}',
        author='Fly Straight Transformation',
    )

    styles = create_styles()
    story  = parse_markup_to_story(markup_content, styles)

    doc.build(story)
    buffer.seek(0)
    return buffer
