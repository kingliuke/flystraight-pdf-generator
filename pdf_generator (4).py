"""
Fly Straight Precision Fuel Protocol PDF Generator v2
Parses explicit markup tags and generates branded PDFs.

Tag vocabulary (M1–M7 output):
  Layout:        [PAGE_BREAK]  [GOLD_RULE]
  Cover:         [COVER_BLOCK]...[/COVER_BLOCK]
                   [PROGRAM_NAME]...[/PROGRAM_NAME]
                   [CLIENT_NAME]...[/CLIENT_NAME]
                   [PROGRAM_SUBTITLE]...[/PROGRAM_SUBTITLE]
  Banners:       [SECTION_HEADER_RED]...[/SECTION_HEADER_RED]
                 [SECTION_HEADER_BLACK]...[/SECTION_HEADER_BLACK]
  Headers:       [H2]...[/H2]   [H3]...[/H3]
  Body:          [BODY]...[/BODY]
  Tables:        [DATA_TABLE cols="2,3"]
                   [TABLE_HEADER]Col1|Col2|Col3[/TABLE_HEADER]
                   [TABLE_ROW]Val1|Val2|Val3[/TABLE_ROW]
                 [/DATA_TABLE]
  Calc blocks:   [CALC_BLOCK]...[/CALC_BLOCK]
  Callout boxes: [BOX_CALLOUT]...[/BOX_CALLOUT]   gold/yellow
                 [BOX_IMPORTANT]...[/BOX_IMPORTANT] red

Improvements over v4 (markdown-based):
  - Explicit tag parsing — no keyword heuristics, no silent fallbacks
  - Page header/footer callbacks on every content page
  - DATA_TABLE with proper alternating rows and proportional column widths
  - CALC_BLOCK with monospaced rendering for arithmetic display
  - Cover block with proper visual structure
  - Nested-table callout boxes (stable across ReportLab versions)
  - apply_inline handles **bold** and *italic* everywhere
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


# ─── BRAND COLORS ─────────────────────────────────────────────────────────────
BLACK        = colors.HexColor('#000000')
NEAR_BLACK   = colors.HexColor('#1A1A1A')
WHITE        = colors.HexColor('#FFFFFF')
GOLD         = colors.HexColor('#FFD000')
GOLD_LIGHT   = colors.HexColor('#FEF3C7')
GOLD_BORDER  = colors.HexColor('#FBBF24')
RED          = colors.HexColor('#9B0F12')
RED_LIGHT    = colors.HexColor('#FFEBEE')
RED_BORDER   = colors.HexColor('#C62828')
GRAY         = colors.HexColor('#666666')
GRAY_BG      = colors.HexColor('#F5F5F5')
GRAY_ALT     = colors.HexColor('#EBEBEB')   # alternating table rows
GRAY_BORDER  = colors.HexColor('#424242')
GRAY_LIGHT   = colors.HexColor('#E0E0E0')
MONO_BG      = colors.HexColor('#F0F0F0')   # CALC_BLOCK background

PAGE_W, PAGE_H = letter
MARGIN       = 0.75 * inch
CONTENT_W    = PAGE_W - 2 * MARGIN


# ─── STYLES ───────────────────────────────────────────────────────────────────
def create_styles():
    base = getSampleStyleSheet()
    return {
        # ── Cover ──────────────────────────────────────────────────────────────
        'program_name': ParagraphStyle('PFP_ProgramName',
            fontName='Helvetica-Bold', fontSize=28,
            textColor=NEAR_BLACK, leading=34,
            alignment=TA_CENTER, spaceAfter=8),

        'client_name': ParagraphStyle('PFP_ClientName',
            fontName='Helvetica-Bold', fontSize=20,
            textColor=RED, leading=26,
            alignment=TA_CENTER, spaceAfter=6),

        'program_subtitle': ParagraphStyle('PFP_Subtitle',
            fontName='Helvetica', fontSize=13,
            textColor=GRAY, leading=18,
            alignment=TA_CENTER, spaceAfter=4),

        'cover_label': ParagraphStyle('PFP_CoverLabel',
            fontName='Helvetica', fontSize=9,
            textColor=GRAY, leading=13,
            alignment=TA_CENTER, spaceAfter=6),

        # ── Headers ────────────────────────────────────────────────────────────
        'h2': ParagraphStyle('PFP_H2',
            fontName='Helvetica-Bold', fontSize=16,
            textColor=RED, leading=20,
            spaceBefore=16, spaceAfter=8),

        'h3': ParagraphStyle('PFP_H3',
            fontName='Helvetica-Bold', fontSize=12,
            textColor=NEAR_BLACK, leading=16,
            spaceBefore=12, spaceAfter=6),

        # ── Body ───────────────────────────────────────────────────────────────
        'body': ParagraphStyle('PFP_Body',
            fontName='Helvetica', fontSize=10,
            textColor=NEAR_BLACK, leading=15,
            alignment=TA_JUSTIFY, spaceAfter=8),

        # ── Banners ────────────────────────────────────────────────────────────
        'banner_text': ParagraphStyle('PFP_BannerText',
            fontName='Helvetica-Bold', fontSize=13,
            textColor=WHITE, leading=18,
            alignment=TA_LEFT),

        # ── Callout box interiors ───────────────────────────────────────────────
        'box_body': ParagraphStyle('PFP_BoxBody',
            fontName='Helvetica', fontSize=10,
            textColor=NEAR_BLACK, leading=15,
            alignment=TA_LEFT, spaceAfter=4),

        'box_bold': ParagraphStyle('PFP_BoxBold',
            fontName='Helvetica-Bold', fontSize=10,
            textColor=NEAR_BLACK, leading=15,
            alignment=TA_LEFT, spaceAfter=4),

        # ── CALC_BLOCK ─────────────────────────────────────────────────────────
        'calc': ParagraphStyle('PFP_Calc',
            fontName='Courier', fontSize=9,
            textColor=NEAR_BLACK, leading=14,
            alignment=TA_LEFT, spaceAfter=2),

        # ── Table interiors ────────────────────────────────────────────────────
        'table_header': ParagraphStyle('PFP_TableHeader',
            fontName='Helvetica-Bold', fontSize=9,
            textColor=WHITE, leading=13,
            alignment=TA_LEFT),

        'table_cell': ParagraphStyle('PFP_TableCell',
            fontName='Helvetica', fontSize=9,
            textColor=NEAR_BLACK, leading=13,
            alignment=TA_LEFT),

        # ── Page chrome ────────────────────────────────────────────────────────
        'footer': ParagraphStyle('PFP_Footer',
            fontName='Helvetica', fontSize=8,
            textColor=GRAY, leading=10,
            alignment=TA_CENTER),
    }


# ─── CHARACTER SANITIZATION ───────────────────────────────────────────────────
# Helvetica (WinAnsiEncoding) cannot render these Unicode characters.
# Map them to safe ASCII equivalents before any text hits ReportLab.
_CHAR_MAP = {
    '\u25a0': '-',    # ■ black square → dash
    '\u2014': '-',    # — em dash → dash
    '\u2013': '-',    # – en dash → dash
    '\u2019': "'",    # ' right single quote → apostrophe
    '\u2018': "'",    # ' left single quote → apostrophe
    '\u201c': '"',    # " left double quote → straight quote
    '\u201d': '"',    # " right double quote → straight quote
    '\u2022': '-',    # • bullet → dash
    '\u00b1': '+/-',  # ± → +/-
    '\u00d7': 'x',    # × → x
    '\u00f7': '/',    # ÷ → /
    '\u2264': '<=',   # ≤ → <=
    '\u2265': '>=',   # ≥ → >=
    '\u2248': '~',    # ≈ → ~
    '\u2192': '->',   # → → ->
    '\u00b0': ' deg', # ° → deg
    # Box-drawing characters (U+2500 block) — used in M2 handoff delimiters
    '\u2550': '=',    # ═ double horizontal → =
    '\u2551': '|',    # ║ double vertical → |
    '\u2554': '+',    # ╔ → +
    '\u2557': '+',    # ╗ → +
    '\u255a': '+',    # ╚ → +
    '\u255d': '+',    # ╝ → +
    '\u2500': '-',    # ─ single horizontal → -
    '\u2502': '|',    # │ single vertical → |
    '\u250c': '+',    # ┌ → +
    '\u2510': '+',    # ┐ → +
    '\u2514': '+',    # └ → +
    '\u2518': '+',    # ┘ → +
    # Other common problematic characters
    '\u00a0': ' ',    # non-breaking space → regular space
    '\u2026': '...',  # … ellipsis → ...
    '\u00ab': '"',    # « → "
    '\u00bb': '"',    # » → "
    '\u2039': "'",    # ‹ → '
    '\u203a': "'",    # › → '
}

def sanitize(text):
    """Replace characters Helvetica cannot render with safe ASCII equivalents.
    Also strips any remaining non-ASCII characters that aren't in the map,
    as a safety net against unknown Unicode crashing the paragraph renderer.
    """
    for char, replacement in _CHAR_MAP.items():
        text = text.replace(char, replacement)
    # Final safety net: encode to latin-1 (Helvetica's encoding), replacing
    # any remaining unmapped characters with '?' rather than crashing
    text = text.encode('latin-1', errors='replace').decode('latin-1')
    return text


def strip_handoff_blocks(markup):
    """
    Remove internal module handoff blocks from markup before rendering.
    These blocks (delimited by === lines) are inter-module data, not document content.
    If they reach the generator they cause rendering failures due to Unicode box chars.

    Removes content between lines that are purely = characters (3 or more).
    """
    # Match blocks: line of ===/═══ chars, content, closing line of ===/═══ chars
    markup = re.sub(
        r'\n[=\u2550]{3,}.*?[=\u2550]{3,}\n',
        '\n',
        markup,
        flags=re.DOTALL
    )
    return markup


# ─── INLINE MARKUP ────────────────────────────────────────────────────────────
def apply_inline(text):
    """Sanitize Unicode, then convert **bold** and *italic* to ReportLab XML."""
    text = sanitize(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text, flags=re.DOTALL)
    text = re.sub(r'\*(.+?)\*',     r'<i>\1</i>', text, flags=re.DOTALL)
    return text


# ─── GOLD RULE ────────────────────────────────────────────────────────────────
def gold_rule():
    return HRFlowable(
        width='100%', thickness=2, color=GOLD,
        spaceBefore=10, spaceAfter=10
    )


# ─── SECTION BANNER ───────────────────────────────────────────────────────────
def section_banner(text, bg_color, styles):
    data = [[Paragraph(f'<b>{apply_inline(text.strip())}</b>',
                       styles['banner_text'])]]
    t = Table(data, colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), bg_color),
        ('LEFTPADDING',   (0, 0), (-1, -1), 14),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 14),
        ('TOPPADDING',    (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    return t


# ─── COVER BLOCK ──────────────────────────────────────────────────────────────
def cover_block(inner_markup, styles):
    """
    Renders [COVER_BLOCK]...[/COVER_BLOCK].
    Extracts PROGRAM_NAME, CLIENT_NAME, PROGRAM_SUBTITLE nested tags.
    """
    def extract(tag, content):
        m = re.search(rf'\[{tag}\](.*?)\[/{tag}\]', content, re.DOTALL)
        return m.group(1).strip() if m else ''

    program_name    = extract('PROGRAM_NAME', inner_markup)
    client_name_txt = extract('CLIENT_NAME', inner_markup)
    subtitle        = extract('PROGRAM_SUBTITLE', inner_markup)

    rows = []
    if program_name:
        rows.append([Paragraph(f'<b>{apply_inline(program_name)}</b>',
                               styles['program_name'])])
    if client_name_txt:
        rows.append([Paragraph(f'<b>{apply_inline(client_name_txt)}</b>',
                               styles['client_name'])])
    if subtitle:
        rows.append([Paragraph(apply_inline(subtitle),
                               styles['program_subtitle'])])
    rows.append([Spacer(1, 8)])
    rows.append([Paragraph('Prepared Exclusively For Adam Lloyd Coaching Clients',
                           styles['cover_label'])])

    t = Table(rows, colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING',   (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
        ('TOPPADDING',    (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    return t


# ─── CALLOUT BOX ──────────────────────────────────────────────────────────────
def callout_box(text, bg, border, styles):
    """
    Renders BOX_CALLOUT and BOX_IMPORTANT.
    Multi-line content: each line becomes a paragraph.
    Lines starting with - / • / * have the marker stripped (safety net).
    """
    lines = text.strip().split('\n')
    paragraphs = []
    for line in lines:
        line = line.strip()
        if not line:
            paragraphs.append(Spacer(1, 4))
            continue
        if line.startswith(('- ', '• ', '* ')):
            line = line[2:]
        # Use bold style if line starts with **
        if line.startswith('**') and '**' in line[2:]:
            style = styles['box_bold']
        else:
            style = styles['box_body']
        paragraphs.append(Paragraph(apply_inline(line), style))

    inner = Table([[p] for p in paragraphs],
                  colWidths=[CONTENT_W - 0.4 * inch])
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


# ─── CALC BLOCK ───────────────────────────────────────────────────────────────
def calc_block(text, styles):
    """
    Renders [CALC_BLOCK]...[/CALC_BLOCK].
    Monospaced font, light gray background, left-aligned.
    Each line becomes a separate paragraph to preserve indentation via spaces.
    Tabs converted to 4 spaces.
    """
    text = text.replace('\t', '    ')
    lines = text.split('\n')
    rows = []
    for line in lines:
        # Preserve leading spaces using non-breaking space trick
        stripped = line.lstrip(' ')
        indent   = len(line) - len(stripped)
        nbsp     = '\u00a0' * indent   # non-breaking spaces for indent
        content  = apply_inline(nbsp + stripped) if stripped else '\u00a0'
        rows.append([Paragraph(content, styles['calc'])])

    inner = Table(rows, colWidths=[CONTENT_W - 0.4 * inch])
    inner.setStyle(TableStyle([
        ('LEFTPADDING',   (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
        ('TOPPADDING',    (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('BACKGROUND',    (0, 0), (-1, -1), MONO_BG),
    ]))
    outer = Table([[inner]], colWidths=[CONTENT_W])
    outer.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), MONO_BG),
        ('BOX',           (0, 0), (-1, -1), 1, GRAY_BORDER),
        ('LEFTPADDING',   (0, 0), (-1, -1), 12),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 12),
        ('TOPPADDING',    (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    return outer


# ─── DATA TABLE ───────────────────────────────────────────────────────────────
def data_table(inner_markup, attrs, styles):
    """
    Renders [DATA_TABLE cols="2,3,5"]...[/DATA_TABLE].

    Inner content:
      [TABLE_HEADER]Col1|Col2|Col3[/TABLE_HEADER]
      [TABLE_ROW]Val1|Val2|Val3[/TABLE_ROW]

    cols attribute (optional): comma-separated relative weights.
      "1,2,3" → columns get 1/6, 2/6, 3/6 of CONTENT_W.
      If absent, equal widths.

    First row (TABLE_HEADER) rendered with black background, white bold text.
    Subsequent rows alternate GRAY_BG and GRAY_ALT.
    apply_inline runs on every cell so **bold** and *italic* work inside tables.
    """
    # Parse rows
    header_texts = []
    row_texts    = []

    header_m = re.search(r'\[TABLE_HEADER\](.*?)\[/TABLE_HEADER\]',
                         inner_markup, re.DOTALL)
    if header_m:
        header_texts = [c.strip() for c in header_m.group(1).split('|')]

    for row_m in re.finditer(r'\[TABLE_ROW\](.*?)\[/TABLE_ROW\]',
                             inner_markup, re.DOTALL):
        row_texts.append([c.strip() for c in row_m.group(1).split('|')])

    if not header_texts and not row_texts:
        return Spacer(1, 4)

    num_cols = len(header_texts) if header_texts else (
        len(row_texts[0]) if row_texts else 1)

    # Column widths from cols attribute
    cols_attr = attrs.get('cols', '')
    if cols_attr:
        weights = [float(x.strip()) for x in cols_attr.split(',')]
        total   = sum(weights)
        col_widths = [CONTENT_W * w / total for w in weights]
    else:
        col_widths = [CONTENT_W / num_cols] * num_cols

    # Pad/trim all rows to num_cols
    def pad(row, n):
        return (row + [''] * n)[:n]

    table_data = []
    if header_texts:
        table_data.append([
            Paragraph(f'<b>{apply_inline(c)}</b>', styles['table_header'])
            for c in pad(header_texts, num_cols)
        ])
    for row in row_texts:
        table_data.append([
            Paragraph(apply_inline(c), styles['table_cell'])
            for c in pad(row, num_cols)
        ])

    t = Table(table_data, colWidths=col_widths)

    style_cmds = [
        # All cells
        ('FONTSIZE',      (0, 0), (-1, -1), 9),
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING',   (0, 0), (-1, -1), 8),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
        ('TOPPADDING',    (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('GRID',          (0, 0), (-1, -1), 0.5, GOLD),
    ]

    if header_texts:
        style_cmds += [
            ('BACKGROUND', (0, 0), (-1, 0), BLACK),
            ('TEXTCOLOR',  (0, 0), (-1, 0), WHITE),
        ]
        data_start = 1
    else:
        data_start = 0

    # Alternating row colors
    for i, _ in enumerate(row_texts):
        row_i = i + data_start
        bg = GRAY_BG if i % 2 == 0 else GRAY_ALT
        style_cmds.append(('BACKGROUND', (0, row_i), (-1, row_i), bg))

    t.setStyle(TableStyle(style_cmds))
    return t


# ─── PAGE CALLBACKS ───────────────────────────────────────────────────────────
def draw_cover_page(canvas, doc):
    """Cover page: footer only."""
    canvas.saveState()
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(GRAY)
    canvas.drawCentredString(PAGE_W / 2, 0.45 * inch,
                             'FLY STRAIGHT TRANSFORMATION')
    canvas.restoreState()


def draw_content_page(canvas, doc):
    """Content pages: gold rule + label at top, footer at bottom."""
    canvas.saveState()

    # Footer
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(GRAY)
    canvas.drawCentredString(PAGE_W / 2, 0.45 * inch,
                             'FLY STRAIGHT TRANSFORMATION')

    # Header — gold rule
    header_y = PAGE_H - 0.42 * inch
    canvas.setStrokeColor(GOLD)
    canvas.setLineWidth(1.5)
    canvas.line(MARGIN, header_y, PAGE_W - MARGIN, header_y)

    # Header label — right-aligned
    canvas.setFont('Helvetica-Bold', 7)
    canvas.setFillColor(GRAY)
    canvas.drawRightString(PAGE_W - MARGIN, header_y + 4,
                           'PRECISION FUEL PROTOCOL')

    canvas.restoreState()


# ─── MAIN PARSER ──────────────────────────────────────────────────────────────
def parse_markup(markup, styles):
    """
    Parse the complete markup string into a ReportLab story list.

    Uses a two-pass regex tokenizer:
      Pass 1 — find all paired tags [...][/...] and self-closing [TAG]
      Pass 2 — process each token in sequence
    """
    story = []
    markup = markup.replace('\r\n', '\n').replace('\r', '\n')

    # Regex: captures paired tags OR self-closing tags
    tag_re = re.compile(
        r'\[([A-Z_0-9]+)((?:\s+[a-z_]+=(?:"[^"]*"|\'[^\']*\'))*)\]'
        r'(.*?)\[/\1\]'
        r'|'
        r'\[([A-Z_0-9]+)((?:\s+[a-z_]+=(?:"[^"]*"|\'[^\']*\'))*)\]',
        re.DOTALL
    )

    tokens = []
    last = 0
    for m in tag_re.finditer(markup):
        if m.start() > last:
            tokens.append(('text', markup[last:m.start()], {}, ''))
        if m.group(1):  # paired tag
            attrs_str = m.group(2) or ''
            attrs     = dict(re.findall(r'(\w+)=["\']([^"\']*)["\']', attrs_str))
            tokens.append(('tag', m.group(1), attrs, m.group(3) or ''))
        else:           # self-closing tag
            attrs_str = m.group(5) or ''
            attrs     = dict(re.findall(r'(\w+)=["\']([^"\']*)["\']', attrs_str))
            tokens.append(('tag', m.group(4), attrs, ''))
        last = m.end()

    if last < len(markup):
        tokens.append(('text', markup[last:], {}, ''))

    # ── Process tokens ────────────────────────────────────────────────────────
    for kind, name, attrs, inner in tokens:

        if kind == 'text':
            for line in name.split('\n'):
                line = line.strip()
                if line:
                    story.append(Paragraph(apply_inline(line), styles['body']))
                else:
                    story.append(Spacer(1, 3))
            continue

        # ── Layout ────────────────────────────────────────────────────────────
        if name == 'PAGE_BREAK':
            story.append(PageBreak())

        elif name == 'GOLD_RULE':
            story.append(gold_rule())

        # ── Cover ─────────────────────────────────────────────────────────────
        elif name == 'COVER_BLOCK':
            story.append(Spacer(1, 0.5 * inch))
            story.append(cover_block(inner, styles))
            story.append(Spacer(1, 0.5 * inch))

        # ── Banners ───────────────────────────────────────────────────────────
        elif name == 'SECTION_HEADER_RED':
            story.append(Spacer(1, 8))
            story.append(section_banner(inner, RED, styles))
            story.append(Spacer(1, 8))

        elif name == 'SECTION_HEADER_BLACK':
            story.append(Spacer(1, 8))
            story.append(section_banner(inner, BLACK, styles))
            story.append(Spacer(1, 8))

        # ── Headers ───────────────────────────────────────────────────────────
        elif name == 'H2':
            story.append(Spacer(1, 6))
            story.append(Paragraph(
                f'<b>{apply_inline(inner.strip())}</b>', styles['h2']))

        elif name == 'H3':
            story.append(Spacer(1, 4))
            story.append(Paragraph(
                f'<b>{apply_inline(inner.strip())}</b>', styles['h3']))

        # ── Body ──────────────────────────────────────────────────────────────
        elif name == 'BODY':
            text = apply_inline(inner.strip())
            # Newlines inside BODY become <br/> for multi-line passages
            text = text.replace('\n', '<br/>')
            story.append(Paragraph(text, styles['body']))
            story.append(Spacer(1, 4))

        # ── Tables ────────────────────────────────────────────────────────────
        elif name == 'DATA_TABLE':
            story.append(Spacer(1, 6))
            story.append(data_table(inner, attrs, styles))
            story.append(Spacer(1, 12))

        # ── Calculation block ─────────────────────────────────────────────────
        elif name == 'CALC_BLOCK':
            story.append(Spacer(1, 6))
            story.append(calc_block(inner, styles))
            story.append(Spacer(1, 8))

        # ── Callout boxes ─────────────────────────────────────────────────────
        elif name == 'BOX_CALLOUT':
            story.append(Spacer(1, 6))
            story.append(callout_box(inner, GOLD_LIGHT, GOLD_BORDER, styles))
            story.append(Spacer(1, 6))

        elif name == 'BOX_IMPORTANT':
            story.append(Spacer(1, 6))
            story.append(callout_box(inner, RED_LIGHT, RED_BORDER, styles))
            story.append(Spacer(1, 6))

    return story


# ─── MAIN ENTRY POINT ─────────────────────────────────────────────────────────
def generate_fuel_protocol_pdf(markup_content: str, client_name: str) -> io.BytesIO:
    """
    Generate a Fly Straight Precision Fuel Protocol PDF from markup.

    Args:
        markup_content: Complete markup string from M1–M7 concatenated.
        client_name:    Client's full name for PDF metadata.

    Returns:
        BytesIO buffer containing the rendered PDF, seeked to position 0.

    Page callbacks:
        Page 1 (cover): footer only — draw_cover_page
        Pages 2+:       gold rule header + label + footer — draw_content_page
    """
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=MARGIN,
        leftMargin=MARGIN,
        topMargin=0.60 * inch,    # slightly tighter — header rule sits here
        bottomMargin=0.75 * inch,
        title=f'Precision Fuel Protocol — {client_name}',
        author='Fly Straight Transformation',
    )

    styles = create_styles()

    # Strip internal module handoff blocks before rendering —
    # these contain Unicode box chars and are not document content
    markup_content = strip_handoff_blocks(markup_content)

    # Cover page brand bar — always first element
    brand_bar_data = [[Paragraph('<b>FLY STRAIGHT</b>', styles['banner_text'])]]
    brand_bar_table = Table(brand_bar_data, colWidths=[CONTENT_W])
    brand_bar_table.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), BLACK),
        ('LEFTPADDING',   (0, 0), (-1, -1), 14),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 14),
        ('TOPPADDING',    (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
    ]))

    story = [
        brand_bar_table,
        Spacer(1, 0.4 * inch),
    ]
    story.extend(parse_markup(markup_content, styles))

    doc.build(
        story,
        onFirstPage=draw_cover_page,
        onLaterPages=draw_content_page,
    )

    buffer.seek(0)
    return buffer


# ─── CLI TEST HARNESS ─────────────────────────────────────────────────────────
if __name__ == '__main__':
    """
    Quick smoke test. Run:
        python3 fuel_protocol_generator.py
    Writes test_output.pdf to current directory.
    """
    SAMPLE = """
[COVER_BLOCK]
[PROGRAM_NAME]PRECISION FUEL PROTOCOL[/PROGRAM_NAME]
[CLIENT_NAME]Steven Almeida[/CLIENT_NAME]
[PROGRAM_SUBTITLE]Your Structure to Rebuild[/PROGRAM_SUBTITLE]
[/COVER_BLOCK]

[GOLD_RULE]

[PAGE_BREAK]

[SECTION_HEADER_RED]YOUR NUMBERS: THE MATH BEHIND THE TRANSFORMATION[/SECTION_HEADER_RED]

[BOX_IMPORTANT]TDEE estimates carry ±10–15% individual variance. These targets are your calibrated starting point. Adjustments happen at your Week 2–3 check-in.[/BOX_IMPORTANT]

[H2]Current Metabolic State[/H2]

[DATA_TABLE cols="3,2"]
[TABLE_HEADER]Metric|Value[/TABLE_HEADER]
[TABLE_ROW]Basal Metabolic Rate (BMR)|~1,923 calories[/TABLE_ROW]
[TABLE_ROW]Activity Multiplier|1.55 (weighted — physical + office split)[/TABLE_ROW]
[TABLE_ROW]**Total Daily Expenditure (TDEE)**|**~2,981 calories/day**[/TABLE_ROW]
[/DATA_TABLE]

[H3]BMR Calculation — Mifflin-St Jeor[/H3]

[CALC_BLOCK]
Unit conversions:
  Weight: 305 lbs ÷ 2.2046 = 138.35 kg
  Height: 6'0" = (6 × 12 + 0) × 2.54 = 182.88 cm
  Age: 51 years

BMR formula (men): (10 × kg) + (6.25 × cm) − (5 × age) + 5
  = (10 × 138.35) + (6.25 × 182.88) − (5 × 51) + 5
  = 1,383.50 + 1,143.00 − 255 + 5
  = 2,276.50 → rounded to 2,277 calories

NOTE: Body weight class = Obese Class I (280–329 lbs)
Mifflin-St Jeor may overstate BMR by 5–8% at this body composition.
Target adjusted conservatively. Calibrate at Week 2–3 check-in.
[/CALC_BLOCK]

[H2]Your Daily Macro Targets[/H2]

[DATA_TABLE cols="2,1,2,1"]
[TABLE_HEADER]Macro|Grams|Calories|% of Total[/TABLE_HEADER]
[TABLE_ROW]Protein|190g|760 cal|36%[/TABLE_ROW]
[TABLE_ROW]Carbohydrates|205g|820 cal|39%[/TABLE_ROW]
[TABLE_ROW]Fat|58g|522 cal|25%[/TABLE_ROW]
[TABLE_ROW]**TOTAL**|**—**|**2,102 cal**|**100%**[/TABLE_ROW]
[/DATA_TABLE]

[BOX_CALLOUT]**Vegetables are unlimited.** Broccoli, green beans, spinach, bok choy, bean sprouts, cauliflower, zucchini — these do not count toward your carb or calorie totals. Starchy vegetables — potatoes, sweet potatoes, corn, peas — do count and must be tracked.[/BOX_CALLOUT]

[GOLD_RULE]

[PAGE_BREAK]

[SECTION_HEADER_BLACK]RED FLAGS THAT WILL DERAIL YOU[/SECTION_HEADER_BLACK]

[H2]1. Dropping Back to One Meal Per Day[/H2]

[BODY]Right now you are eating boiled eggs during the day and dinner at home — effectively one real meal. You said yourself you know it is bad. That pattern is what brought you to 305 lbs. The body running on one meal interprets the gap between meals as a famine signal and slows metabolic rate to compensate.[/BODY]

[BODY]**The fix:** Four meals, every day. Set phone alarms for each one. The first week will feel like too much food. That is the point — your body needs to stop operating in conservation mode.[/BODY]

[GOLD_RULE]

[PAGE_BREAK]

[SECTION_HEADER_BLACK]A WORD FROM ADAM[/SECTION_HEADER_BLACK]

[BODY]Steven, let's get you to 200 lbs — and let's be honest about what that means. Six years younger than your dad was when he died, at 305 pounds, drinking on weekends, eating once a day. You said it yourself: you are playing with fire.[/BODY]

[BODY]You built a roofing company. You run men. You show up for clients every day at 7am in the sun and carry 80-pound rolls up a ladder. You have been doing the hard thing alone for a long time.[/BODY]

[BODY]What was missing was not discipline. It was structure — a protocol built around your actual life, and someone who already knows your history before the first session starts. That is what this is.[/BODY]

[BODY]Six months to stop telling yourself tomorrow, and prove to yourself you already did it on the day that counted most — the day you were 51, six years from where your father stopped.[/BODY]

[GOLD_RULE]

[BODY]Fly Straight,[/BODY]

[BODY]**ADAM LLOYD**
Fly Straight Transformation[/BODY]
"""

    buf = generate_fuel_protocol_pdf(SAMPLE, 'Steven Almeida')
    with open('test_output.pdf', 'wb') as f:
        f.write(buf.read())
    print('Written: test_output.pdf')
