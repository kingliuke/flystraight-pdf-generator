"""
Fly Straight Precision Training Protocol PDF Generator v1
Parses training markup tags and generates branded PDFs.

Tag vocabulary (TP1-TP6 output):

  Shared with nutrition generator:
    Layout:        [PAGE_BREAK]  [GOLD_RULE]
    Cover:         [COVER_BLOCK]...[/COVER_BLOCK]
                     [PROGRAM_NAME]  [CLIENT_NAME]  [PROGRAM_SUBTITLE]  [COACH_NAME]
    Banners:       [SECTION_HEADER_RED]  [SECTION_HEADER_BLACK]
    Headers:       [H2]  [H3]
    Body:          [BODY]
    Tables:        [DATA_TABLE]  [TABLE_HEADER]  [TABLE_ROW]
    Callouts:      [BOX_CALLOUT]  [BOX_IMPORTANT]
    Checklist:     [CHECKLIST]  [CHECKLIST_ITEM]

  Training-specific (new):
    Session:       [PRE_WORKOUT_FUEL]   — red border, high visual weight
                   [SESSION_CONTEXT]    — gold left border, cannot be skimmed
                   [SESSION_NOTES]      — gray bg, smaller leading, reference register

    Warm-up:       [WARMUP_BLOCK]       — container
                     [WARMUP_EXERCISE]name | sets | cue[/WARMUP_EXERCISE]
                     [WARMUP_SETS]text[/WARMUP_SETS]
                     [WARMUP_READY]text[/WARMUP_READY]

    Exercise:      [EXERCISE_BLOCK]     — container with left accent bar
                     [EXERCISE_HEADER]Name | sets | Tempo | RPE | Rest[/EXERCISE_HEADER]
                     [COACHING_NOTE]    — gray inset
                     [PROGRESSION_NOTE] — gold inset, visually distinct from coaching
                   [/EXERCISE_BLOCK]

    Cool-down:     [COOLDOWN]           — container
                     [STRETCH_ITEM]name | position | duration | cue[/STRETCH_ITEM]

    Recovery:      [RECOVERY_BLOCK]     — light blue-gray bg intro block
                   [RECOVERY_INTENSITY] — intensity guidelines block
                   [RECOVERY_VARIANT]label — day-specific variant container
                   [STRETCH_PROTOCOL]  — stretching section container

Architecture improvements over nutrition generator:
  - Sequential tokenizer (no greedy regex) — eliminates silent content loss
  - Depth-tracking block parser handles nested tags correctly
  - Section completeness validator logs warnings before PDF is built
  - Parameterised page header label
  - Exercise block renderer with left accent bar
  - Pipe-delimited single-line renderers (EXERCISE_HEADER, WARMUP_EXERCISE,
    STRETCH_ITEM) extract fields without regex over full document
  - All nutrition-generator fixes inherited: flat callout tables (splittable),
    GOLD_RULE paired-tag preprocessor, full Unicode sanitization map,
    handoff block stripper
"""

import io
import re
import logging
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY, TA_RIGHT

logger = logging.getLogger(__name__)


# ─── BRAND COLORS ─────────────────────────────────────────────────────────────
BLACK        = colors.HexColor('#000000')
NEAR_BLACK   = colors.HexColor('#1A1A1A')
WHITE        = colors.HexColor('#FFFFFF')
GOLD         = colors.HexColor('#FFD000')
GOLD_LIGHT   = colors.HexColor('#FEF3C7')
GOLD_BORDER  = colors.HexColor('#FBBF24')
GOLD_DARK    = colors.HexColor('#B8860B')   # left border accent on exercise blocks
RED          = colors.HexColor('#9B0F12')
RED_LIGHT    = colors.HexColor('#FFEBEE')
RED_BORDER   = colors.HexColor('#C62828')
GRAY         = colors.HexColor('#666666')
GRAY_BG      = colors.HexColor('#F5F5F5')
GRAY_ALT     = colors.HexColor('#EBEBEB')
GRAY_BORDER  = colors.HexColor('#424242')
GRAY_LIGHT   = colors.HexColor('#E0E0E0')
GRAY_MED     = colors.HexColor('#CCCCCC')
MONO_BG      = colors.HexColor('#F0F0F0')
COACHING_BG  = colors.HexColor('#F8F8F8')   # coaching note background
COACHING_BRD = colors.HexColor('#DDDDDD')   # coaching note border
PROG_BG      = colors.HexColor('#FFFBEA')   # progression note background (warm)
PROG_BRD     = colors.HexColor('#FBBF24')   # progression note border (gold)
SESSION_BG   = colors.HexColor('#FFFDF5')   # session context background
PRE_BG       = colors.HexColor('#FFF5F5')   # pre-workout fuel background
RECOVERY_BG  = colors.HexColor('#F0F4F8')   # recovery block background
RECOVERY_BRD = colors.HexColor('#BDD0E0')   # recovery block border
WARMUP_BG    = colors.HexColor('#F5F5F5')   # warmup block background
ACCENT_BAR   = colors.HexColor('#9B0F12')   # left accent bar on exercise blocks

PAGE_W, PAGE_H = letter
MARGIN       = 0.75 * inch
CONTENT_W    = PAGE_W - 2 * MARGIN

# Accent bar constants for exercise blocks
ACCENT_W     = 4          # points wide
ACCENT_GAP   = 8          # gap between bar and content
INNER_W      = CONTENT_W - ACCENT_W - ACCENT_GAP


# ─── STYLES ───────────────────────────────────────────────────────────────────
def create_styles():
    base = getSampleStyleSheet()
    return {
        # ── Cover ──────────────────────────────────────────────────────────────
        'program_name': ParagraphStyle('PTP_ProgramName',
            fontName='Helvetica-Bold', fontSize=28,
            textColor=NEAR_BLACK, leading=34,
            alignment=TA_CENTER, spaceAfter=8),
        'client_name': ParagraphStyle('PTP_ClientName',
            fontName='Helvetica-Bold', fontSize=20,
            textColor=RED, leading=26,
            alignment=TA_CENTER, spaceAfter=6),
        'program_subtitle': ParagraphStyle('PTP_Subtitle',
            fontName='Helvetica', fontSize=13,
            textColor=GRAY, leading=18,
            alignment=TA_CENTER, spaceAfter=4),
        'cover_label': ParagraphStyle('PTP_CoverLabel',
            fontName='Helvetica', fontSize=9,
            textColor=GRAY, leading=13,
            alignment=TA_CENTER, spaceAfter=6),

        # ── Headers ────────────────────────────────────────────────────────────
        'h2': ParagraphStyle('PTP_H2',
            fontName='Helvetica-Bold', fontSize=16,
            textColor=RED, leading=20,
            spaceBefore=16, spaceAfter=8),
        'h3': ParagraphStyle('PTP_H3',
            fontName='Helvetica-Bold', fontSize=12,
            textColor=NEAR_BLACK, leading=16,
            spaceBefore=12, spaceAfter=6),

        # ── Body ───────────────────────────────────────────────────────────────
        'body': ParagraphStyle('PTP_Body',
            fontName='Helvetica', fontSize=10,
            textColor=NEAR_BLACK, leading=15,
            alignment=TA_JUSTIFY, spaceAfter=8),

        # ── Banners ────────────────────────────────────────────────────────────
        'banner_text': ParagraphStyle('PTP_BannerText',
            fontName='Helvetica-Bold', fontSize=13,
            textColor=WHITE, leading=18,
            alignment=TA_LEFT),

        # ── Callout boxes ──────────────────────────────────────────────────────
        'box_body': ParagraphStyle('PTP_BoxBody',
            fontName='Helvetica', fontSize=10,
            textColor=NEAR_BLACK, leading=15,
            alignment=TA_LEFT, spaceAfter=4),
        'box_bold': ParagraphStyle('PTP_BoxBold',
            fontName='Helvetica-Bold', fontSize=10,
            textColor=NEAR_BLACK, leading=15,
            alignment=TA_LEFT, spaceAfter=4),

        # ── Tables ─────────────────────────────────────────────────────────────
        'table_header': ParagraphStyle('PTP_TableHeader',
            fontName='Helvetica-Bold', fontSize=9,
            textColor=WHITE, leading=13,
            alignment=TA_LEFT),
        'table_cell': ParagraphStyle('PTP_TableCell',
            fontName='Helvetica', fontSize=9,
            textColor=NEAR_BLACK, leading=13,
            alignment=TA_LEFT),

        # ── Page chrome ────────────────────────────────────────────────────────
        'footer': ParagraphStyle('PTP_Footer',
            fontName='Helvetica', fontSize=8,
            textColor=GRAY, leading=10,
            alignment=TA_CENTER),

        # ── Session context — gold left border, larger leading ─────────────────
        'session_context': ParagraphStyle('PTP_SessionContext',
            fontName='Helvetica', fontSize=10,
            textColor=NEAR_BLACK, leading=17,
            alignment=TA_LEFT, spaceAfter=6,
            leftIndent=12),

        # ── Pre-workout fuel — red-tinted ──────────────────────────────────────
        'pre_fuel_label': ParagraphStyle('PTP_PreFuelLabel',
            fontName='Helvetica-Bold', fontSize=10,
            textColor=RED, leading=14,
            alignment=TA_LEFT, spaceAfter=2),
        'pre_fuel_body': ParagraphStyle('PTP_PreFuelBody',
            fontName='Helvetica', fontSize=10,
            textColor=NEAR_BLACK, leading=15,
            alignment=TA_LEFT, spaceAfter=4),

        # ── Exercise header — name + spec line ─────────────────────────────────
        'exercise_name': ParagraphStyle('PTP_ExerciseName',
            fontName='Helvetica-Bold', fontSize=12,
            textColor=NEAR_BLACK, leading=16,
            alignment=TA_LEFT, spaceAfter=2),
        'exercise_spec': ParagraphStyle('PTP_ExerciseSpec',
            fontName='Courier', fontSize=9,
            textColor=GRAY_BORDER, leading=13,
            alignment=TA_LEFT, spaceAfter=0),

        # ── Coaching note — gray inset ──────────────────────────────────────────
        'coaching': ParagraphStyle('PTP_Coaching',
            fontName='Helvetica', fontSize=9,
            textColor=NEAR_BLACK, leading=14,
            alignment=TA_LEFT, spaceAfter=3),
        'coaching_bold': ParagraphStyle('PTP_CoachingBold',
            fontName='Helvetica-Bold', fontSize=9,
            textColor=NEAR_BLACK, leading=14,
            alignment=TA_LEFT, spaceAfter=3),

        # ── Progression note — warm gold inset ─────────────────────────────────
        'progression': ParagraphStyle('PTP_Progression',
            fontName='Helvetica', fontSize=9,
            textColor=NEAR_BLACK, leading=14,
            alignment=TA_LEFT, spaceAfter=3),

        # ── Warm-up elements ───────────────────────────────────────────────────
        'warmup_exercise': ParagraphStyle('PTP_WarmupExercise',
            fontName='Helvetica-Bold', fontSize=9,
            textColor=NEAR_BLACK, leading=13,
            alignment=TA_LEFT, spaceAfter=1),
        'warmup_cue': ParagraphStyle('PTP_WarmupCue',
            fontName='Helvetica', fontSize=9,
            textColor=GRAY, leading=13,
            alignment=TA_LEFT, spaceAfter=4),
        'warmup_ready': ParagraphStyle('PTP_WarmupReady',
            fontName='Helvetica', fontSize=9,
            textColor=NEAR_BLACK, leading=13,
            alignment=TA_LEFT, spaceAfter=2,
            leftIndent=4),

        # ── Cool-down / stretch items ───────────────────────────────────────────
        'stretch_name': ParagraphStyle('PTP_StretchName',
            fontName='Helvetica-Bold', fontSize=9,
            textColor=NEAR_BLACK, leading=13,
            alignment=TA_LEFT, spaceAfter=1),
        'stretch_detail': ParagraphStyle('PTP_StretchDetail',
            fontName='Helvetica', fontSize=9,
            textColor=GRAY, leading=13,
            alignment=TA_LEFT, spaceAfter=4),

        # ── Session notes — reference register ─────────────────────────────────
        'session_notes': ParagraphStyle('PTP_SessionNotes',
            fontName='Helvetica', fontSize=9,
            textColor=NEAR_BLACK, leading=13,
            alignment=TA_LEFT, spaceAfter=4),
        'session_notes_bold': ParagraphStyle('PTP_SessionNotesBold',
            fontName='Helvetica-Bold', fontSize=9,
            textColor=NEAR_BLACK, leading=13,
            alignment=TA_LEFT, spaceAfter=4),

        # ── Recovery blocks ────────────────────────────────────────────────────
        'recovery_body': ParagraphStyle('PTP_RecoveryBody',
            fontName='Helvetica', fontSize=10,
            textColor=NEAR_BLACK, leading=15,
            alignment=TA_LEFT, spaceAfter=6),
        'recovery_variant_header': ParagraphStyle('PTP_RecoveryVariantHeader',
            fontName='Helvetica-Bold', fontSize=11,
            textColor=NEAR_BLACK, leading=16,
            spaceBefore=8, spaceAfter=6),

        # ── Checklist ──────────────────────────────────────────────────────────
        'checklist_item': ParagraphStyle('PTP_ChecklistItem',
            fontName='Helvetica', fontSize=10,
            textColor=NEAR_BLACK, leading=15,
            alignment=TA_LEFT, spaceAfter=4,
            leftIndent=18),
    }


# ─── CHARACTER SANITIZATION ───────────────────────────────────────────────────
# Inherited from nutrition generator — full map retained.
_CHAR_MAP = {
    '\u25a0': '-',    # ■ black square
    '\u2014': '-',    # — em dash
    '\u2013': '-',    # – en dash
    '\u2019': "'",    # ' right single quote
    '\u2018': "'",    # ' left single quote
    '\u201c': '"',    # " left double quote
    '\u201d': '"',    # " right double quote
    '\u2022': '-',    # • bullet
    '\u00b1': '+/-',  # ±
    '\u00d7': 'x',    # ×
    '\u00f7': '/',    # ÷
    '\u2264': '<=',   # ≤
    '\u2265': '>=',   # ≥
    '\u2248': '~',    # ≈
    '\u2192': '->',   # →
    '\u00b0': ' deg', # °
    '\u2550': '=',    # ═
    '\u2551': '|',    # ║
    '\u2554': '+',    # ╔
    '\u2557': '+',    # ╗
    '\u255a': '+',    # ╚
    '\u255d': '+',    # ╝
    '\u2500': '-',    # ─
    '\u2502': '|',    # │
    '\u250c': '+',    # ┌
    '\u2510': '+',    # ┐
    '\u2514': '+',    # └
    '\u2518': '+',    # ┘
    '\u00a0': ' ',    # non-breaking space
    '\u2026': '...',  # …
    '\u00ab': '"',    # «
    '\u00bb': '"',    # »
    '\u2039': "'",    # ‹
    '\u203a': "'",    # ›
    '\u25a1': '[ ]',  # □ empty square → checkbox
    '\u2611': '[x]',  # ☑ checked box
    '\u2610': '[ ]',  # ☐ ballot box
}


def sanitize(text):
    for char, replacement in _CHAR_MAP.items():
        text = text.replace(char, replacement)
    text = text.encode('latin-1', errors='replace').decode('latin-1')
    return text


def apply_inline(text):
    """Sanitize Unicode, convert **bold** and *italic* to ReportLab XML."""
    text = sanitize(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text, flags=re.DOTALL)
    text = re.sub(r'\*(.+?)\*',     r'<i>\1</i>', text, flags=re.DOTALL)
    return text


# ─── PRE-PROCESSING ───────────────────────────────────────────────────────────
def strip_training_noise(markup):
    """
    Strip internal module artifacts that should not appear in the rendered PDF.
    - Training handoff delimiters from T-modules (--- lines)
    - Lines of pure === or --- characters
    - Markdown headers (# ## ###) — TP modules should not produce these but
      defensive stripping prevents corrupted output if one does
    """
    markup = re.sub(r'---+[A-Z\s]+---+', '', markup, flags=re.DOTALL)
    markup = re.sub(r'(?m)^[=]{3,}\s*$', '', markup)
    markup = re.sub(r'(?m)^[-]{3,}\s*$', '', markup)
    markup = re.sub(r'(?m)^#{1,3}\s+', '', markup)
    return markup


def preprocess_markup(markup):
    """
    Inherited fix: convert paired [GOLD_RULE]text[/GOLD_RULE] to
    [GOLD_RULE] + [BOX_CALLOUT]text[/BOX_CALLOUT] before tokenisation.
    Without this, the tokeniser's greedy match swallows large content blocks.
    """
    markup = re.sub(
        r'\[GOLD_RULE\](.+?)\[/GOLD_RULE\]',
        lambda m: f'[GOLD_RULE]\n[BOX_CALLOUT]{m.group(1).strip()}[/BOX_CALLOUT]',
        markup,
        flags=re.DOTALL
    )
    return markup


# ─── SEQUENTIAL TOKENISER ─────────────────────────────────────────────────────
def tokenise(markup):
    """
    Sequential O(n) tokeniser. Replaces the greedy regex approach in the
    nutrition generator that silently dropped content between mismatched tags.

    Returns a flat list of tokens:
      ('open',  tag_name, attrs_dict)   — opening or self-closing tag
      ('close', tag_name, {})
      ('text',  content,  {})

    Attributes are parsed from key="value" pairs inside opening tags.
    RECOVERY_VARIANT carries a label in the tag itself: [RECOVERY_VARIANT]label
    — this is extracted as attrs['label'].
    """
    tokens = []
    i = 0
    n = len(markup)

    while i < n:
        if markup[i] != '[':
            # Scan for next '[' or end
            j = markup.find('[', i)
            if j == -1:
                j = n
            chunk = markup[i:j]
            if chunk:
                tokens.append(('text', chunk, {}))
            i = j
            continue

        # We are at '['
        j = markup.find(']', i)
        if j == -1:
            # No closing bracket — treat rest as text
            tokens.append(('text', markup[i:], {}))
            break

        raw = markup[i+1:j]  # content between [ and ]

        # Closing tag?
        if raw.startswith('/'):
            tag_name = raw[1:].strip().split()[0]
            tokens.append(('close', tag_name, {}))
            i = j + 1
            continue

        # Opening tag — may have attributes
        parts = raw.split(None, 1)   # split on first whitespace
        tag_name = parts[0].strip()

        attrs = {}
        if len(parts) > 1:
            # Parse key="value" pairs
            for m in re.finditer(r'(\w+)=["\']([^"\']*)["\']', parts[1]):
                attrs[m.group(1)] = m.group(2)
            # For RECOVERY_VARIANT: label is any trailing non-key=value text
            remainder = re.sub(r'\w+=["\'][^"\']*["\']', '', parts[1]).strip()
            if remainder:
                attrs['label'] = remainder

        tokens.append(('open', tag_name, attrs))
        i = j + 1

    return tokens


# ─── BLOCK EXTRACTOR ──────────────────────────────────────────────────────────
def extract_block_content(tokens, start_idx, block_tag):
    """
    Given tokens and an index pointing just past an opening tag,
    collect all tokens until the matching close tag (depth-aware).
    Returns (inner_tokens, next_idx).
    """
    depth = 1
    inner = []
    i = start_idx
    while i < len(tokens) and depth > 0:
        kind, name, attrs = tokens[i]
        if kind == 'open' and name == block_tag:
            depth += 1
            inner.append(tokens[i])
        elif kind == 'close' and name == block_tag:
            depth -= 1
            if depth > 0:
                inner.append(tokens[i])
        else:
            inner.append(tokens[i])
        i += 1
    return inner, i


def tokens_to_text(tokens):
    """Reconstruct raw text from a token list (for sub-parsers that use regex)."""
    parts = []
    for kind, name, attrs in tokens:
        if kind == 'text':
            parts.append(name)
        elif kind == 'open':
            parts.append(f'[{name}]')
        elif kind == 'close':
            parts.append(f'[/{name}]')
    return ''.join(parts)


# ─── SECTION COMPLETENESS VALIDATOR ───────────────────────────────────────────
EXPECTED_SECTIONS = [
    'COVER_BLOCK',
    'SECTION_HEADER_RED',
    'SECTION_HEADER_BLACK',
    'EXERCISE_BLOCK',
    'SESSION_NOTES',
    'RECOVERY_VARIANT',
]

def validate_sections(tokens, client_name):
    """Log warnings for any expected section type that is entirely absent."""
    found = {kind for (_, kind, __) in tokens if _ == 'open'}
    for section in EXPECTED_SECTIONS:
        if section not in found:
            logger.warning(
                'Training PDF for %s: expected section [%s] not found in markup. '
                'Document may be incomplete.',
                client_name, section
            )


# ─── LAYOUT HELPERS ───────────────────────────────────────────────────────────
def gold_rule():
    return HRFlowable(width='100%', thickness=2, color=GOLD,
                      spaceBefore=10, spaceAfter=10)


def thin_rule(color=GRAY_LIGHT):
    return HRFlowable(width='100%', thickness=0.5, color=color,
                      spaceBefore=4, spaceAfter=4)


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


def body_paragraphs(text, styles, style_key='body'):
    """
    Split text at blank lines and return a list of Paragraph flowables.
    Within each chunk, newlines become <br/>.
    Inherited from nutrition generator — fixes the "giant Paragraph cannot
    be split across pages" crash for tall BODY content.
    """
    items = []
    chunks = re.split(r'\n{2,}', text.strip())
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            items.append(Spacer(1, 6))
            continue
        rendered = apply_inline(chunk.replace('\n', '<br/>'))
        items.append(Paragraph(rendered, styles[style_key]))
        items.append(Spacer(1, 2))
    return items


def callout_box(text, bg, border, styles):
    """
    Flat single-column table callout box — splittable across pages.
    Inherited directly from nutrition generator.
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
        if line.startswith('**') and '**' in line[2:]:
            style = styles['box_bold']
        else:
            style = styles['box_body']
        paragraphs.append(Paragraph(apply_inline(line), style))

    t = Table([[p] for p in paragraphs], colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), bg),
        ('BOX',           (0, 0), (-1, -1), 2, border),
        ('LEFTPADDING',   (0, 0), (-1, -1), 14),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 14),
        ('TOPPADDING',    (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    return t


def data_table(inner_text, attrs, styles):
    """
    Renders [DATA_TABLE]...[/DATA_TABLE].
    Inherited from nutrition generator — identical logic, same column weighting.
    """
    header_texts = []
    row_texts    = []

    header_m = re.search(r'\[TABLE_HEADER\](.*?)\[/TABLE_HEADER\]',
                         inner_text, re.DOTALL)
    if header_m:
        header_texts = [c.strip() for c in header_m.group(1).split('|')]

    for row_m in re.finditer(r'\[TABLE_ROW\](.*?)\[/TABLE_ROW\]',
                             inner_text, re.DOTALL):
        row_texts.append([c.strip() for c in row_m.group(1).split('|')])

    if not header_texts and not row_texts:
        return Spacer(1, 4)

    num_cols = len(header_texts) if header_texts else (
        len(row_texts[0]) if row_texts else 1)

    cols_attr = attrs.get('cols', '')
    if cols_attr:
        weights = [float(x.strip()) for x in cols_attr.split(',')]
        total   = sum(weights)
        col_widths = [CONTENT_W * w / total for w in weights]
    else:
        col_widths = [CONTENT_W / num_cols] * num_cols

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
    for i, _ in enumerate(row_texts):
        row_i = i + data_start
        bg = GRAY_BG if i % 2 == 0 else GRAY_ALT
        style_cmds.append(('BACKGROUND', (0, row_i), (-1, row_i), bg))
    t.setStyle(TableStyle(style_cmds))
    return t


# ─── COVER BLOCK ──────────────────────────────────────────────────────────────
def cover_block(inner_text, styles):
    def extract(tag, content):
        m = re.search(rf'\[{tag}\](.*?)\[/{tag}\]', content, re.DOTALL)
        return m.group(1).strip() if m else ''

    program_name    = extract('PROGRAM_NAME',    inner_text)
    client_name_txt = extract('CLIENT_NAME',     inner_text)
    subtitle        = extract('PROGRAM_SUBTITLE', inner_text)
    coach_name      = extract('COACH_NAME',      inner_text)

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
    label_text = (f'Prepared by {apply_inline(coach_name)} | Fly Straight Transformation'
                  if coach_name else 'Fly Straight Transformation')
    rows.append([Paragraph(label_text, styles['cover_label'])])

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


# ─── SESSION CONTEXT ──────────────────────────────────────────────────────────
def session_context_block(text, styles):
    """
    Gold left border, slightly larger leading.
    Rendered as a 2-column table: narrow gold bar | content.
    """
    paras = body_paragraphs(text, styles, 'session_context')
    content_rows = [[p] for p in paras]

    inner_t = Table(content_rows, colWidths=[INNER_W + ACCENT_GAP])
    inner_t.setStyle(TableStyle([
        ('LEFTPADDING',   (0, 0), (-1, -1), ACCENT_GAP),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
        ('TOPPADDING',    (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('BACKGROUND',    (0, 0), (-1, -1), SESSION_BG),
    ]))

    bar_t = Table([['']], colWidths=[ACCENT_W], rowHeights=[None])
    bar_t.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), GOLD_BORDER),
        ('TOPPADDING',    (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING',   (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
    ]))

    outer = Table([[bar_t, inner_t]],
                  colWidths=[ACCENT_W, INNER_W + ACCENT_GAP])
    outer.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING',   (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
        ('TOPPADDING',    (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    return outer


# ─── PRE-WORKOUT FUEL ─────────────────────────────────────────────────────────
def pre_workout_fuel_block(text, styles):
    """
    Red-bordered block. Cannot be skimmed past.
    """
    return callout_box(text, PRE_BG, RED_BORDER, styles)


# ─── EXERCISE BLOCK ───────────────────────────────────────────────────────────
def exercise_header(spec_line, styles):
    """
    Parse pipe-delimited spec: "Name | X sets x reps | Tempo: X | RPE: X | Rest: X"
    Returns list of flowables: bold name paragraph + monospaced spec paragraph.
    """
    parts = [p.strip() for p in spec_line.split('|')]
    name = parts[0] if parts else spec_line
    spec = '  |  '.join(parts[1:]) if len(parts) > 1 else ''

    items = []
    items.append(Paragraph(apply_inline(name), styles['exercise_name']))
    if spec:
        items.append(Paragraph(sanitize(spec), styles['exercise_spec']))
    items.append(Spacer(1, 4))
    return items


def coaching_note_block(text, styles):
    """
    Gray inset box. Technique guidance.
    Each paragraph separated, all at 9pt.
    """
    lines = text.strip().split('\n')
    paragraphs = []
    for line in lines:
        line = line.strip()
        if not line:
            paragraphs.append(Spacer(1, 3))
            continue
        if line.startswith(('- ', '• ')):
            line = line[2:]
        if line.startswith('**') and '**' in line[2:]:
            s = styles['coaching_bold']
        else:
            s = styles['coaching']
        paragraphs.append(Paragraph(apply_inline(line), s))

    t = Table([[p] for p in paragraphs], colWidths=[INNER_W + ACCENT_GAP])
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), COACHING_BG),
        ('BOX',           (0, 0), (-1, -1), 0.5, COACHING_BRD),
        ('LEFTPADDING',   (0, 0), (-1, -1), 10),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 10),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    return t


def progression_note_block(text, styles):
    """
    Warm gold inset box. Overload logic. Visually distinct from coaching notes.
    """
    lines = text.strip().split('\n')
    paragraphs = []
    for line in lines:
        line = line.strip()
        if not line:
            paragraphs.append(Spacer(1, 3))
            continue
        paragraphs.append(Paragraph(apply_inline(line), styles['progression']))

    t = Table([[p] for p in paragraphs], colWidths=[INNER_W + ACCENT_GAP])
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), PROG_BG),
        ('BOX',           (0, 0), (-1, -1), 1, PROG_BRD),
        ('LEFTPADDING',   (0, 0), (-1, -1), 10),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 10),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    return t


def exercise_block(inner_tokens, styles):
    """
    Render a complete EXERCISE_BLOCK as a left-accent-bar container.
    Inner tokens are processed in order:
      EXERCISE_HEADER → name + spec line (full width, above the accent bar)
      COACHING_NOTE   → gray inset (inside accent bar column)
      BOX_CALLOUT     → gold callout (inside accent bar column)
      BOX_IMPORTANT   → red callout (inside accent bar column — for contraindications)
      PROGRESSION_NOTE→ gold warm inset (inside accent bar column)
    """
    # First pass: collect the header and all content items
    header_items = []
    content_items = []

    i = 0
    while i < len(inner_tokens):
        kind, name, attrs = inner_tokens[i]

        if kind == 'open' and name == 'EXERCISE_HEADER':
            # Collect until close
            j = i + 1
            text_parts = []
            while j < len(inner_tokens):
                k2, n2, _ = inner_tokens[j]
                if k2 == 'close' and n2 == 'EXERCISE_HEADER':
                    break
                if k2 == 'text':
                    text_parts.append(n2)
                j += 1
            spec_text = ''.join(text_parts).strip()
            header_items.extend(exercise_header(spec_text, styles))
            i = j + 1

        elif kind == 'open' and name == 'COACHING_NOTE':
            j = i + 1
            text_parts = []
            while j < len(inner_tokens):
                k2, n2, _ = inner_tokens[j]
                if k2 == 'close' and n2 == 'COACHING_NOTE':
                    break
                if k2 == 'text':
                    text_parts.append(n2)
                j += 1
            note_text = ''.join(text_parts).strip()
            if note_text:
                content_items.append(coaching_note_block(note_text, styles))
                content_items.append(Spacer(1, 4))
            i = j + 1

        elif kind == 'open' and name == 'PROGRESSION_NOTE':
            j = i + 1
            text_parts = []
            while j < len(inner_tokens):
                k2, n2, _ = inner_tokens[j]
                if k2 == 'close' and n2 == 'PROGRESSION_NOTE':
                    break
                if k2 == 'text':
                    text_parts.append(n2)
                j += 1
            prog_text = ''.join(text_parts).strip()
            if prog_text:
                content_items.append(progression_note_block(prog_text, styles))
                content_items.append(Spacer(1, 4))
            i = j + 1

        elif kind == 'open' and name == 'BOX_CALLOUT':
            j = i + 1
            text_parts = []
            while j < len(inner_tokens):
                k2, n2, _ = inner_tokens[j]
                if k2 == 'close' and n2 == 'BOX_CALLOUT':
                    break
                if k2 == 'text':
                    text_parts.append(n2)
                j += 1
            box_text = ''.join(text_parts).strip()
            if box_text:
                content_items.append(callout_box(box_text, GOLD_LIGHT, GOLD_BORDER, styles))
                content_items.append(Spacer(1, 4))
            i = j + 1

        elif kind == 'open' and name == 'BOX_IMPORTANT':
            j = i + 1
            text_parts = []
            while j < len(inner_tokens):
                k2, n2, _ = inner_tokens[j]
                if k2 == 'close' and n2 == 'BOX_IMPORTANT':
                    break
                if k2 == 'text':
                    text_parts.append(n2)
                j += 1
            box_text = ''.join(text_parts).strip()
            if box_text:
                content_items.append(callout_box(box_text, RED_LIGHT, RED_BORDER, styles))
                content_items.append(Spacer(1, 4))
            i = j + 1

        elif kind == 'text' and name.strip():
            # Loose text inside exercise block — render as body
            for p in body_paragraphs(name, styles):
                content_items.append(p)
            i += 1
        else:
            i += 1

    # Build accent-bar layout
    # Header spans full width (no accent bar for the name/spec)
    # Content goes inside right column next to the red accent bar

    result = []
    result.extend(header_items)

    if content_items:
        # Pack content into a single-column table for the right side
        content_rows = [[item] for item in content_items]
        content_t = Table(content_rows, colWidths=[INNER_W])
        content_t.setStyle(TableStyle([
            ('LEFTPADDING',   (0, 0), (-1, -1), 0),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
            ('TOPPADDING',    (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))

        bar_t = Table([['']], colWidths=[ACCENT_W])
        bar_t.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), ACCENT_BAR),
            ('TOPPADDING',    (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING',   (0, 0), (-1, -1), 0),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
        ]))

        gap_col = Table([['']], colWidths=[ACCENT_GAP])
        gap_col.setStyle(TableStyle([
            ('TOPPADDING',    (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING',   (0, 0), (-1, -1), 0),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
        ]))

        outer = Table([[bar_t, gap_col, content_t]],
                      colWidths=[ACCENT_W, ACCENT_GAP, INNER_W])
        outer.setStyle(TableStyle([
            ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING',   (0, 0), (-1, -1), 0),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
            ('TOPPADDING',    (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        result.append(outer)

    return result


# ─── WARMUP BLOCK ─────────────────────────────────────────────────────────────
def warmup_block(inner_tokens, styles):
    """
    Light gray container. WARMUP_EXERCISE, WARMUP_SETS, WARMUP_READY, BODY all supported.
    """
    items = []

    i = 0
    while i < len(inner_tokens):
        kind, name, attrs = inner_tokens[i]

        if kind == 'open' and name == 'WARMUP_EXERCISE':
            j = i + 1
            text_parts = []
            while j < len(inner_tokens):
                k2, n2, _ = inner_tokens[j]
                if k2 == 'close' and n2 == 'WARMUP_EXERCISE':
                    break
                if k2 == 'text':
                    text_parts.append(n2)
                j += 1
            raw = ''.join(text_parts).strip()
            # Pipe-delimited: name | sets | cue
            parts = [p.strip() for p in raw.split('|', 2)]
            ex_name = parts[0] if parts else raw
            ex_sets = parts[1] if len(parts) > 1 else ''
            ex_cue  = parts[2] if len(parts) > 2 else ''
            spec_str = f'{ex_sets}' if ex_sets else ''
            items.append(Paragraph(
                f'<b>{apply_inline(ex_name)}</b>' +
                (f'  —  {sanitize(spec_str)}' if spec_str else ''),
                styles['warmup_exercise']))
            if ex_cue:
                items.append(Paragraph(apply_inline(ex_cue), styles['warmup_cue']))
            i = j + 1

        elif kind == 'open' and name == 'WARMUP_SETS':
            j = i + 1
            text_parts = []
            while j < len(inner_tokens):
                k2, n2, _ = inner_tokens[j]
                if k2 == 'close' and n2 == 'WARMUP_SETS':
                    break
                if k2 == 'text':
                    text_parts.append(n2)
                j += 1
            raw = ''.join(text_parts).strip()
            items.append(Paragraph(
                f'<b>Warm-up sets:</b>  {apply_inline(raw)}',
                styles['warmup_exercise']))
            items.append(Spacer(1, 3))
            i = j + 1

        elif kind == 'open' and name == 'WARMUP_READY':
            j = i + 1
            text_parts = []
            while j < len(inner_tokens):
                k2, n2, _ = inner_tokens[j]
                if k2 == 'close' and n2 == 'WARMUP_READY':
                    break
                if k2 == 'text':
                    text_parts.append(n2)
                j += 1
            raw = ''.join(text_parts).strip()
            items.append(thin_rule())
            items.append(Paragraph(
                f'<b>You are ready when:</b>  {apply_inline(raw)}',
                styles['warmup_ready']))
            i = j + 1

        elif kind == 'open' and name == 'BODY':
            j = i + 1
            text_parts = []
            while j < len(inner_tokens):
                k2, n2, _ = inner_tokens[j]
                if k2 == 'close' and n2 == 'BODY':
                    break
                if k2 == 'text':
                    text_parts.append(n2)
                j += 1
            for p in body_paragraphs(''.join(text_parts), styles, 'coaching'):
                items.append(p)
            i = j + 1

        elif kind == 'text' and name.strip():
            for p in body_paragraphs(name, styles, 'coaching'):
                items.append(p)
            i += 1
        else:
            i += 1

    if not items:
        return []

    rows = [[item] for item in items]
    t = Table(rows, colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), WARMUP_BG),
        ('BOX',           (0, 0), (-1, -1), 0.5, GRAY_LIGHT),
        ('LEFTPADDING',   (0, 0), (-1, -1), 12),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 12),
        ('TOPPADDING',    (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    return [t]


# ─── COOLDOWN BLOCK ───────────────────────────────────────────────────────────
def cooldown_block(inner_tokens, styles):
    """
    Light container. STRETCH_ITEM, BODY, H3 all supported.
    """
    items = []

    i = 0
    while i < len(inner_tokens):
        kind, name, attrs = inner_tokens[i]

        if kind == 'open' and name == 'STRETCH_ITEM':
            j = i + 1
            text_parts = []
            while j < len(inner_tokens):
                k2, n2, _ = inner_tokens[j]
                if k2 == 'close' and n2 == 'STRETCH_ITEM':
                    break
                if k2 == 'text':
                    text_parts.append(n2)
                j += 1
            raw = ''.join(text_parts).strip()
            # Pipe-delimited: name | position | duration | cue
            parts = [p.strip() for p in raw.split('|', 3)]
            s_name     = parts[0] if parts else raw
            s_position = parts[1] if len(parts) > 1 else ''
            s_duration = parts[2] if len(parts) > 2 else ''
            s_cue      = parts[3] if len(parts) > 3 else ''
            label = s_name
            if s_duration:
                label += f'  ({sanitize(s_duration)})'
            items.append(Paragraph(f'<b>{apply_inline(label)}</b>',
                                   styles['stretch_name']))
            detail_parts = []
            if s_position:
                detail_parts.append(sanitize(s_position))
            if s_cue:
                detail_parts.append(sanitize(s_cue))
            if detail_parts:
                items.append(Paragraph(
                    apply_inline('  '.join(detail_parts)),
                    styles['stretch_detail']))
            i = j + 1

        elif kind == 'open' and name == 'H3':
            j = i + 1
            text_parts = []
            while j < len(inner_tokens):
                k2, n2, _ = inner_tokens[j]
                if k2 == 'close' and n2 == 'H3':
                    break
                if k2 == 'text':
                    text_parts.append(n2)
                j += 1
            items.append(Paragraph(
                f'<b>{apply_inline("".join(text_parts).strip())}</b>',
                styles['h3']))
            i = j + 1

        elif kind == 'open' and name == 'BODY':
            j = i + 1
            text_parts = []
            while j < len(inner_tokens):
                k2, n2, _ = inner_tokens[j]
                if k2 == 'close' and n2 == 'BODY':
                    break
                if k2 == 'text':
                    text_parts.append(n2)
                j += 1
            for p in body_paragraphs(''.join(text_parts), styles):
                items.append(p)
            i = j + 1

        elif kind == 'text' and name.strip():
            for p in body_paragraphs(name, styles):
                items.append(p)
            i += 1
        else:
            i += 1

    return items


# ─── SESSION NOTES ────────────────────────────────────────────────────────────
def session_notes_block(text, styles):
    """
    Gray background, smaller leading, reference register.
    Flat table so it can split across pages.
    """
    lines = text.strip().split('\n')
    paragraphs = []
    for line in lines:
        line_s = line.strip()
        if not line_s:
            paragraphs.append(Spacer(1, 3))
            continue
        if line_s.startswith('**') and '**' in line_s[2:]:
            s = styles['session_notes_bold']
        else:
            s = styles['session_notes']
        paragraphs.append(Paragraph(apply_inline(line_s), s))

    t = Table([[p] for p in paragraphs], colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), GRAY_BG),
        ('BOX',           (0, 0), (-1, -1), 0.5, GRAY_LIGHT),
        ('LEFTPADDING',   (0, 0), (-1, -1), 12),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 12),
        ('TOPPADDING',    (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    return t


# ─── RECOVERY BLOCKS ──────────────────────────────────────────────────────────
def recovery_container(inner_tokens, styles, bg=RECOVERY_BG, border=RECOVERY_BRD):
    """Generic light-blue-gray container for RECOVERY_BLOCK and RECOVERY_INTENSITY."""
    items = render_token_list(inner_tokens, styles)
    if not items:
        return []
    rows = [[item] for item in items]
    t = Table(rows, colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), bg),
        ('BOX',           (0, 0), (-1, -1), 0.5, border),
        ('LEFTPADDING',   (0, 0), (-1, -1), 12),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 12),
        ('TOPPADDING',    (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    return [t, Spacer(1, 6)]


def recovery_variant_block(inner_tokens, attrs, styles):
    """RECOVERY_VARIANT — renders with a variant-label header and content below."""
    label = attrs.get('label', '')
    items = []
    if label:
        items.append(Paragraph(
            f'<b>{apply_inline(label)}</b>',
            styles['recovery_variant_header']))
    items.extend(render_token_list(inner_tokens, styles))
    return items


def stretch_protocol_block(inner_tokens, styles):
    """STRETCH_PROTOCOL — renders all priority areas with STRETCH_ITEMs."""
    return cooldown_block(inner_tokens, styles)


# ─── CHECKLIST ────────────────────────────────────────────────────────────────
def checklist_block(inner_tokens, styles):
    """
    Renders [CHECKLIST]...[CHECKLIST_ITEM]text[/CHECKLIST_ITEM]...[/CHECKLIST].
    Each item gets a square checkbox prefix.
    """
    items = []
    i = 0
    while i < len(inner_tokens):
        kind, name, attrs = inner_tokens[i]
        if kind == 'open' and name == 'CHECKLIST_ITEM':
            j = i + 1
            text_parts = []
            while j < len(inner_tokens):
                k2, n2, _ = inner_tokens[j]
                if k2 == 'close' and n2 == 'CHECKLIST_ITEM':
                    break
                if k2 == 'text':
                    text_parts.append(n2)
                j += 1
            item_text = ''.join(text_parts).strip()
            items.append(Paragraph(
                f'[ ]  {apply_inline(item_text)}',
                styles['checklist_item']))
            i = j + 1
        elif kind == 'text' and name.strip():
            i += 1
        else:
            i += 1

    return items


# ─── GENERIC TOKEN RENDERER ───────────────────────────────────────────────────
def render_token_list(tokens, styles):
    """
    Process a flat or nested token list and return ReportLab flowables.
    This is the core dispatch function — called recursively by block renderers.
    """
    story = []
    i = 0

    while i < len(tokens):
        kind, name, attrs = tokens[i]

        # ── Text ───────────────────────────────────────────────────────────────
        if kind == 'text':
            stripped = name.strip()
            if stripped:
                for p in body_paragraphs(name, styles):
                    story.append(p)
            i += 1
            continue

        if kind == 'close':
            i += 1
            continue

        # ── kind == 'open' from here ───────────────────────────────────────────

        # ── Layout ─────────────────────────────────────────────────────────────
        if name == 'PAGE_BREAK':
            story.append(PageBreak())
            i += 1

        elif name == 'GOLD_RULE':
            story.append(gold_rule())
            i += 1

        # ── Cover ──────────────────────────────────────────────────────────────
        elif name == 'COVER_BLOCK':
            inner, i = extract_block_content(tokens, i + 1, 'COVER_BLOCK')
            story.append(Spacer(1, 0.5 * inch))
            story.append(cover_block(tokens_to_text(inner), styles))
            story.append(Spacer(1, 0.5 * inch))

        # ── Banners ────────────────────────────────────────────────────────────
        elif name == 'SECTION_HEADER_RED':
            inner, i = extract_block_content(tokens, i + 1, 'SECTION_HEADER_RED')
            story.append(Spacer(1, 8))
            story.append(section_banner(tokens_to_text(inner), RED, styles))
            story.append(Spacer(1, 8))

        elif name == 'SECTION_HEADER_BLACK':
            inner, i = extract_block_content(tokens, i + 1, 'SECTION_HEADER_BLACK')
            story.append(Spacer(1, 8))
            story.append(section_banner(tokens_to_text(inner), BLACK, styles))
            story.append(Spacer(1, 8))

        # ── Headers ────────────────────────────────────────────────────────────
        elif name == 'H2':
            inner, i = extract_block_content(tokens, i + 1, 'H2')
            story.append(Spacer(1, 6))
            story.append(Paragraph(
                f'<b>{apply_inline(tokens_to_text(inner).strip())}</b>',
                styles['h2']))

        elif name == 'H3':
            inner, i = extract_block_content(tokens, i + 1, 'H3')
            story.append(Spacer(1, 4))
            story.append(Paragraph(
                f'<b>{apply_inline(tokens_to_text(inner).strip())}</b>',
                styles['h3']))

        # ── Body ───────────────────────────────────────────────────────────────
        elif name == 'BODY':
            inner, i = extract_block_content(tokens, i + 1, 'BODY')
            for p in body_paragraphs(tokens_to_text(inner), styles):
                story.append(p)

        # ── Tables ─────────────────────────────────────────────────────────────
        elif name == 'DATA_TABLE':
            inner, i = extract_block_content(tokens, i + 1, 'DATA_TABLE')
            story.append(Spacer(1, 6))
            story.append(data_table(tokens_to_text(inner), attrs, styles))
            story.append(Spacer(1, 12))

        # ── Callout boxes ──────────────────────────────────────────────────────
        elif name == 'BOX_CALLOUT':
            inner, i = extract_block_content(tokens, i + 1, 'BOX_CALLOUT')
            story.append(Spacer(1, 6))
            story.append(callout_box(tokens_to_text(inner),
                                     GOLD_LIGHT, GOLD_BORDER, styles))
            story.append(Spacer(1, 6))

        elif name == 'BOX_IMPORTANT':
            inner, i = extract_block_content(tokens, i + 1, 'BOX_IMPORTANT')
            story.append(Spacer(1, 6))
            story.append(callout_box(tokens_to_text(inner),
                                     RED_LIGHT, RED_BORDER, styles))
            story.append(Spacer(1, 6))

        # ── Checklist ──────────────────────────────────────────────────────────
        elif name == 'CHECKLIST':
            inner, i = extract_block_content(tokens, i + 1, 'CHECKLIST')
            story.append(Spacer(1, 6))
            story.extend(checklist_block(inner, styles))
            story.append(Spacer(1, 6))

        # ── SESSION_CONTEXT ────────────────────────────────────────────────────
        elif name == 'SESSION_CONTEXT':
            inner, i = extract_block_content(tokens, i + 1, 'SESSION_CONTEXT')
            story.append(Spacer(1, 6))
            story.append(session_context_block(tokens_to_text(inner), styles))
            story.append(Spacer(1, 8))

        # ── PRE_WORKOUT_FUEL ───────────────────────────────────────────────────
        elif name == 'PRE_WORKOUT_FUEL':
            inner, i = extract_block_content(tokens, i + 1, 'PRE_WORKOUT_FUEL')
            story.append(Spacer(1, 6))
            story.append(pre_workout_fuel_block(tokens_to_text(inner), styles))
            story.append(Spacer(1, 8))

        # ── WARMUP_BLOCK ───────────────────────────────────────────────────────
        elif name == 'WARMUP_BLOCK':
            inner, i = extract_block_content(tokens, i + 1, 'WARMUP_BLOCK')
            story.append(Spacer(1, 6))
            story.extend(warmup_block(inner, styles))
            story.append(Spacer(1, 10))

        # ── EXERCISE_BLOCK ─────────────────────────────────────────────────────
        elif name == 'EXERCISE_BLOCK':
            inner, i = extract_block_content(tokens, i + 1, 'EXERCISE_BLOCK')
            story.append(Spacer(1, 4))
            story.extend(exercise_block(inner, styles))
            story.append(Spacer(1, 8))

        # ── COOLDOWN ───────────────────────────────────────────────────────────
        elif name == 'COOLDOWN':
            inner, i = extract_block_content(tokens, i + 1, 'COOLDOWN')
            story.append(Spacer(1, 6))
            story.extend(cooldown_block(inner, styles))
            story.append(Spacer(1, 8))

        # ── SESSION_NOTES ──────────────────────────────────────────────────────
        elif name == 'SESSION_NOTES':
            inner, i = extract_block_content(tokens, i + 1, 'SESSION_NOTES')
            story.append(Spacer(1, 6))
            story.append(session_notes_block(tokens_to_text(inner), styles))
            story.append(Spacer(1, 10))

        # ── RECOVERY_BLOCK ─────────────────────────────────────────────────────
        elif name == 'RECOVERY_BLOCK':
            inner, i = extract_block_content(tokens, i + 1, 'RECOVERY_BLOCK')
            story.extend(recovery_container(inner, styles))

        # ── RECOVERY_INTENSITY ─────────────────────────────────────────────────
        elif name == 'RECOVERY_INTENSITY':
            inner, i = extract_block_content(tokens, i + 1, 'RECOVERY_INTENSITY')
            story.extend(recovery_container(inner, styles,
                                            bg=WARMUP_BG, border=GRAY_LIGHT))

        # ── RECOVERY_VARIANT ───────────────────────────────────────────────────
        elif name == 'RECOVERY_VARIANT':
            inner, i = extract_block_content(tokens, i + 1, 'RECOVERY_VARIANT')
            story.append(Spacer(1, 6))
            story.extend(recovery_variant_block(inner, attrs, styles))
            story.append(Spacer(1, 8))

        # ── STRETCH_PROTOCOL ───────────────────────────────────────────────────
        elif name == 'STRETCH_PROTOCOL':
            inner, i = extract_block_content(tokens, i + 1, 'STRETCH_PROTOCOL')
            story.append(Spacer(1, 6))
            story.extend(stretch_protocol_block(inner, styles))
            story.append(Spacer(1, 8))

        # ── Unknown tag — skip silently, log warning ───────────────────────────
        else:
            logger.warning('training_pdf_generator: unknown tag [%s] — skipped', name)
            inner, i = extract_block_content(tokens, i + 1, name)

    return story


# ─── PAGE CALLBACKS ───────────────────────────────────────────────────────────
def make_cover_callback():
    def draw_cover_page(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(GRAY)
        canvas.drawCentredString(PAGE_W / 2, 0.45 * inch,
                                 'FLY STRAIGHT TRANSFORMATION')
        canvas.restoreState()
    return draw_cover_page


def make_content_callback(header_label='PRECISION TRAINING PROTOCOL'):
    def draw_content_page(canvas, doc):
        canvas.saveState()
        # Footer
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(GRAY)
        canvas.drawCentredString(PAGE_W / 2, 0.45 * inch,
                                 'FLY STRAIGHT TRANSFORMATION')
        # Header gold rule
        header_y = PAGE_H - 0.42 * inch
        canvas.setStrokeColor(GOLD)
        canvas.setLineWidth(1.5)
        canvas.line(MARGIN, header_y, PAGE_W - MARGIN, header_y)
        # Header label
        canvas.setFont('Helvetica-Bold', 7)
        canvas.setFillColor(GRAY)
        canvas.drawRightString(PAGE_W - MARGIN, header_y + 4, header_label)
        canvas.restoreState()
    return draw_content_page


# ─── MAIN ENTRY POINT ─────────────────────────────────────────────────────────
def generate_training_pdf(markup_content: str,
                          client_name: str,
                          header_label: str = 'PRECISION TRAINING PROTOCOL') -> io.BytesIO:
    """
    Generate a Fly Straight Precision Training Protocol PDF from markup.

    Args:
        markup_content: Complete markup string from TP1-TP6 concatenated.
        client_name:    Client's full name for PDF metadata.
        header_label:   Text that appears in the top-right page header.
                        Defaults to 'PRECISION TRAINING PROTOCOL'.

    Returns:
        BytesIO buffer containing the rendered PDF, seeked to position 0.
    """
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=MARGIN,
        leftMargin=MARGIN,
        topMargin=0.60 * inch,
        bottomMargin=0.75 * inch,
        title=f'Precision Training Protocol — {client_name}',
        author='Fly Straight Transformation',
    )

    styles = create_styles()

    # Pre-processing pipeline
    markup_content = strip_training_noise(markup_content)
    markup_content = preprocess_markup(markup_content)

    # Tokenise
    tokens = tokenise(markup_content)

    # Validate sections and log warnings — does not block PDF generation
    validate_sections(tokens, client_name)

    print(f'=== TRAINING PDF DEBUG ===')
    print(f'Client: {client_name}')
    print(f'Markup length: {len(markup_content)} chars')
    print(f'Token count: {len(tokens)}')
    tag_names = [n for (k, n, _) in tokens if k == 'open']
    print(f'Top-level tags found: {list(dict.fromkeys(tag_names))}')
    print(f'=== END DEBUG ===')

    # Brand bar — always first element
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
    story.extend(render_token_list(tokens, styles))

    print(f'Story elements: {len(story)}')

    doc.build(
        story,
        onFirstPage=make_cover_callback(),
        onLaterPages=make_content_callback(header_label),
    )

    buffer.seek(0)
    return buffer


# ─── CLI SMOKE TEST ───────────────────────────────────────────────────────────
if __name__ == '__main__':
    SAMPLE = """
[COVER_BLOCK]
[PROGRAM_NAME]PRECISION TRAINING PROTOCOL[/PROGRAM_NAME]
[CLIENT_NAME]Agostino DiRienzo[/CLIENT_NAME]
[PROGRAM_SUBTITLE]Phase 1: Strength Foundation | Weeks 1 to 12[/PROGRAM_SUBTITLE]
[COACH_NAME]Adam Lloyd[/COACH_NAME]
[/COVER_BLOCK]

[GOLD_RULE]

[PAGE_BREAK]

[SECTION_HEADER_BLACK]TINO, THIS IS WHERE IT STARTS.[/SECTION_HEADER_BLACK]

[BODY]You spent years building a construction business that runs without you being in the room. You also spent those years maintaining a daily cardio habit that most people never build in their entire lives. The missing piece is here: resistance training built around your specific biology, your boxer's muscle memory, and the cortisol reality of running a business while eating in a 900-calorie deficit.[/BODY]

[GOLD_RULE]

[H2]Fly Straight Member Profile[/H2]

[DATA_TABLE]
[TABLE_HEADER]Field|Details[/TABLE_HEADER]
[TABLE_ROW]Age|36 years old[/TABLE_ROW]
[TABLE_ROW]Current Weight|253 lbs[/TABLE_ROW]
[TABLE_ROW]Height|5'10"[/TABLE_ROW]
[TABLE_ROW]Goal Weight|200 to 205 lbs[/TABLE_ROW]
[TABLE_ROW]Training Classification|Intermediate Returner (former boxer, meaningful training history)[/TABLE_ROW]
[TABLE_ROW]Training Time|5:30 AM daily[/TABLE_ROW]
[TABLE_ROW]Deload Week|Week 4[/TABLE_ROW]
[/DATA_TABLE]

[PAGE_BREAK]

[SECTION_HEADER_RED]PUSH DAY -- TINO[/SECTION_HEADER_RED]
[H2]Chest | Shoulders | Triceps[/H2]
[BODY]Phase 1 -- Technique | Week 1 | Monday | Est. 55 minutes[/BODY]

[GOLD_RULE]

[PRE_WORKOUT_FUEL]
**Time:** 5:00 AM -- 30 minutes before training.

1 scoop whey protein (25g protein) + 5g creatine + 1 medium banana (27g carbs). Mix in water.

**Why this matters on Push Day:** At 5:30 AM in a 900-calorie deficit, cortisol is at its daily peak. Pressing movements without fuel amplify the cortisol response and accelerate muscle breakdown. Your boxer base means your body knows what hard upper body work feels like -- it needs the fuel to do it properly.
[/PRE_WORKOUT_FUEL]

[GOLD_RULE]

[SESSION_CONTEXT]
Tino, your boxing background means your pushing mechanics are not being learned today -- they are being relearned. Your chest, shoulders, and triceps have structural memory. The goal this week is to find that memory and confirm it is still there before we load it. The weight on the bar in week 1 is deliberately conservative. That is not timidity. That is the connective tissue timeline being respected so that week 6 can be aggressive.
[/SESSION_CONTEXT]

[GOLD_RULE]

[WARMUP_BLOCK]
[BODY]After a 5:00 AM wake and fuel, your core temperature is low and your thoracic spine is stiff. This warm-up addresses both before you press anything.[/BODY]
[WARMUP_EXERCISE]Incline treadmill walk | 5 minutes at 8% incline, 2.5 mph | Elevates temperature, begins decompressing the thoracic spine after overnight compression.[/WARMUP_EXERCISE]
[WARMUP_EXERCISE]Band pull-apart | 2 sets x 15 reps | Pull band to chest at shoulder height. 2-second squeeze at full extension. This is rear delt activation -- the counterbalance to everything you are about to press.[/WARMUP_EXERCISE]
[WARMUP_EXERCISE]Scapular wall slide | 2 sets x 10 reps | Back flat to wall, elbows at 90 degrees, slide arms overhead while maintaining wall contact. If the lower back peels off the wall, you have found a thoracic restriction -- work within that range for now.[/WARMUP_EXERCISE]
[WARMUP_SETS]Set 1: Empty motion x 12 reps -- position check only | Set 2: 25% working weight x 8 reps -- feel for lat engagement[/WARMUP_SETS]
[WARMUP_READY]Shoulders feel loose and connected. The pressing motion in the warm-up sets felt controlled rather than stiff. Chest feels ready to spread rather than grip.[/WARMUP_READY]
[/WARMUP_BLOCK]

[GOLD_RULE]

[EXERCISE_BLOCK]
[EXERCISE_HEADER]Dumbbell Floor Press | 3 sets x 8-10 reps | Tempo: 3-1-1-0 | RPE: 5-6 | Rest: 2 min[/EXERCISE_HEADER]
[COACHING_NOTE]**Equipment:** 2 x 30 lb dumbbells. Floor space.

**Setup:** Lie flat, knees bent, feet flat -- this stabilises the base without loading the foot. Dumbbells start at chest height, elbows at approximately 45 degrees from torso. At 253 lbs, your upper back makes excellent contact with the floor -- use it as a stable platform.[/COACHING_NOTE]
[COACHING_NOTE]**3-second lower is the session this week.** The eccentric builds motor control that the concentric phase reveals later. Press with intent, not urgency. If you were pressing overhead on a construction site today, your anterior deltoid is already worked -- feel this from the chest, not the shoulder.[/COACHING_NOTE]
[PROGRESSION_NOTE]**Trigger:** When you complete 10 reps for all 3 sets at RPE 5-6, add 5 lbs next session and return to 8 reps.
**Next available weight:** 35 lbs.
**Regression:** If you cannot complete 8 reps, reduce by 5 lbs and rebuild.
**Technique phase note:** Weight progression is not the goal this week. The movement pattern is.[/PROGRESSION_NOTE]
[/EXERCISE_BLOCK]

[GOLD_RULE]

[EXERCISE_BLOCK]
[EXERCISE_HEADER]Dumbbell Lateral Raise | 3 sets x 12-15 reps | Tempo: 2-0-2-1 | RPE: 6 | Rest: 60 sec[/EXERCISE_HEADER]
[COACHING_NOTE]**Equipment:** 2 x 15 lb dumbbells.

**Why this exercise:** Lateral delts are the width. Your boxing background developed your anterior shoulder extensively -- the lateral head is where the visual transformation happens fastest.[/COACHING_NOTE]
[COACHING_NOTE]At the top, your shoulder should be level with your ear. No higher. Drop the shrug -- if you feel upper trap, you have shrugged. Reset, drop the shoulders, raise the arm.[/COACHING_NOTE]
[BOX_CALLOUT]**Bad-day modification:** On high-fatigue construction days where standing is difficult, perform seated on the edge of a bench or chair. Same stimulus, zero bilateral stance demand.[/BOX_CALLOUT]
[PROGRESSION_NOTE]Add reps within range before adding weight. When 15 reps across all sets at RPE 6, add 2.5 lbs.[/PROGRESSION_NOTE]
[/EXERCISE_BLOCK]

[PAGE_BREAK]

[SECTION_HEADER_BLACK]ACTIVE RECOVERY -- TINO[/SECTION_HEADER_BLACK]
[H2]Movement | Mobility | Recovery[/H2]
[BODY]Phase 1 -- Technique | Week 1 | Template -- 4 Variants[/BODY]
[BODY]Est. duration: 30 to 60 minutes (varies by day)[/BODY]

[GOLD_RULE]

[RECOVERY_BLOCK]
[BODY]Active recovery is not cardio and it is not rest. It is strategic low-intensity movement designed to enhance recovery, reduce cortisol, and maintain your daily training habit without adding training stress.[/BODY]
[BODY]Metabolic waste products that cause soreness clear through blood flow. Blood flow requires movement. 30 to 45 minutes of easy movement the day after a session produces measurably less soreness than sitting still -- and burns additional calories without taxing your nervous system.[/BODY]
[/RECOVERY_BLOCK]

[RECOVERY_INTENSITY]
[BODY]**Target:** RPE 3 to 4. Nose breathing entire time. If you cannot nose breathe, you are going too hard. Heart rate approximately 110 to 130 bpm.[/BODY]
[BOX_CALLOUT]**Physical job interaction:** On heavy construction days, reduce duration by 15 to 20 minutes. Your body is already managing recovery debt from the labor. This is not a shorter session because you earned it -- it is shorter because the system needs it.[/BOX_CALLOUT]
[/RECOVERY_INTENSITY]

[RECOVERY_VARIANT]Variant 3 -- After Leg Day
[BODY]Yesterday was Leg Day. The most metabolically demanding session of the week. Your quads, hamstrings, and glutes are sore. Stairs will be uncomfortable. Sitting down feels stiff.[/BODY]
[BOX_IMPORTANT]**The temptation today is to sit on the couch because you earned it after Leg Day.**

Here is the specific reason that is the wrong call: the metabolic waste driving your soreness clears through blood flow. Blood flow requires movement. 35 minutes of easy cycling or walking today moves significantly more blood through your quads and hamstrings than sitting does. Research on DOMS clearance consistently shows low-intensity movement reduces soreness duration by 20 to 30% compared to rest. Sitting compounds it. The difference shows up on Monday.[/BOX_IMPORTANT]
[BODY]**Prescription:** 35 to 40 minutes | RPE 3 only -- not RPE 4 | Stationary bike preferred when legs are heavily sore.[/BODY]
[/RECOVERY_VARIANT]

[STRETCH_PROTOCOL]
[H3]Priority 1 -- Hip Flexors[/H3]
[BODY]Construction work and the forward lean of morning training accumulates hip flexor tension. This is the highest-leverage stretch in the program for a client in your occupational context.[/BODY]
[STRETCH_ITEM]Half-kneeling hip flexor | Rear knee down, front foot forward, hips square. Gently push hips forward until stretch felt in front of rear-side hip | 60 seconds per side | Breathe into the stretch. With each exhale, allow slight additional release. Do not force.[/STRETCH_ITEM]
[H3]Priority 2 -- Thoracic Spine[/H3]
[STRETCH_ITEM]Chair-back thoracic extension | Sit in firm chair. Hands clasped behind head. Gently extend backward over the chair back at shoulder blade level | 20 seconds at 3 different heights | Mid-back only -- NOT lower back. If you feel it in the lower back, move higher on the chair back.[/STRETCH_ITEM]
[/STRETCH_PROTOCOL]

[SESSION_NOTES]
**Readiness on recovery days:** The Autoregulation Protocol is for training sessions. Active recovery is below the threshold where it normally applies -- RPE 3 is appropriate at almost any readiness level.

The exception: if you rate 2 or more Red factors, apply the minimum effective dose.
[BOX_CALLOUT]**Minimum effective dose:** 15 to 20 minutes easy walking plus 2 to 3 priority stretches. Done. This counts. It is infinitely better than zero and does not add meaningful stress to an already-depleted system.[/BOX_CALLOUT]
**What to track:** Date, duration, equipment used, energy level today (1 to 10).
[/SESSION_NOTES]

[PAGE_BREAK]

[SECTION_HEADER_RED]FINAL REMINDERS FOR TINO[/SECTION_HEADER_RED]

[DATA_TABLE]
[TABLE_HEADER]#|Reminder|Why It Matters[/TABLE_HEADER]
[TABLE_ROW]1|YOU ARE NOT A BEGINNER|You have a boxer's base and a construction worker's daily physical output. Your body knows what hard work feels like. The conservative week 1 loading is for your connective tissue -- not your capacity. By week 3, the program accelerates.[/TABLE_ROW]
[TABLE_ROW]2|THE 900-CALORIE DEFICIT IS THE BIGGEST CORTISOL SOURCE|Pre-workout fuel at 5:00 AM is not optional. Cortisol peaks 30 to 45 minutes after waking. Fasted training at that hour in a 900-calorie deficit burns muscle, not fat.[/TABLE_ROW]
[TABLE_ROW]3|DELOAD WEEK 4 IS NON-NEGOTIABLE|With your triple cortisol load -- deficit, training, and business ownership -- deload at week 4 is earlier than the standard 6-week protocol. It is not optional. The week 5 performance gain is the proof it worked.[/TABLE_ROW]
[/DATA_TABLE]

[PAGE_BREAK]

[SECTION_HEADER_BLACK]A WORD FROM ADAM[/SECTION_HEADER_BLACK]

[BODY]Tino, let's get you to 200 lbs -- and let's be honest about what that number means. At 200 lbs lean, you are in better physical condition than you were at any point in your adult working life. That is the goal. Not lighter -- better.[/BODY]

[BODY]You built a construction business from scratch. You wake up at 5:00 AM before other people's alarms have gone off. You have been carrying the physical and business load simultaneously for years, and you maintained a daily cardio habit through all of it. What you were doing alone was already impressive. What was missing was the structure to direct that capacity toward a specific physical outcome.[/BODY]

[BODY]That structure is here now. A protocol built around the specific reality of your cortisol load, your boxer's muscle memory, and your 5:30 AM training window. Not a generic plan. This one.[/BODY]

[BODY]Twelve weeks to prove that the body that trained in a boxing gym and built a business can be rebuilt leaner and stronger than it has ever been. Your cardio base is already elite. Now we add the lean mass that transforms the physique.[/BODY]

[BODY]Fly Straight,[/BODY]

[BODY]**ADAM LLOYD**
Fly Straight Transformation[/BODY]
"""

    buf = generate_training_pdf(SAMPLE, 'Agostino DiRienzo')
    with open('test_training_output.pdf', 'wb') as f:
        f.write(buf.read())
    print('Written: test_training_output.pdf')
