"""
PDF Generator for Fly Straight Precision Fuel Protocol v4
Converts markdown content to branded PDF with enhanced visual design
"""

import io
import re
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
    PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

# FLY STRAIGHT BRAND COLORS
BLACK = colors.HexColor('#000000')
RED = colors.HexColor('#9B0F12')
GOLD = colors.HexColor('#FFD000')
NEAR_BLACK = colors.HexColor('#1A1A1A')
GRAY = colors.HexColor('#666666')
LIGHT_GRAY = colors.HexColor('#F5F5F5')
WHITE = colors.HexColor('#FFFFFF')
YELLOW_BG = colors.HexColor('#FEF3C7')
YELLOW_BORDER = colors.HexColor('#FBBF24')
RED_BG = colors.HexColor('#FEF2F2')
LIGHT_RED = colors.HexColor('#FCA5A5')

def create_styles():
    """Create Fly Straight branded paragraph styles with enhanced hierarchy"""
    styles = getSampleStyleSheet()
    
    # Brand bar style
    brand_bar = ParagraphStyle('BrandBar',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=16,
        textColor=WHITE,
        backColor=BLACK,
        alignment=TA_CENTER,
        leading=22,
        spaceBefore=6,
        spaceAfter=6,
        leftIndent=0,
        rightIndent=0)
    
    # Page title (huge, for major page headers)
    page_title = ParagraphStyle('PageTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        textColor=RED,
        spaceAfter=12,
        spaceBefore=20,
        leading=28,
        alignment=TA_LEFT)
    
    # Main header (PRECISION FUEL PROTOCOL)
    header = ParagraphStyle('FlyHeader',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=28,
        textColor=BLACK,
        spaceAfter=6,
        alignment=TA_LEFT,
        leading=32)
    
    # Section headers (red, large)
    section = ParagraphStyle('FlySection',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=16,
        textColor=RED,
        spaceAfter=10,
        spaceBefore=18,
        leading=20)
    
    # Subsection headers (bold black, medium)
    subsection = ParagraphStyle('SubSection',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=13,
        textColor=NEAR_BLACK,
        spaceAfter=8,
        spaceBefore=12,
        leading=16)
    
    # Small headers (bold, smaller)
    small_header = ParagraphStyle('SmallHeader',
        parent=styles['Heading4'],
        fontName='Helvetica-Bold',
        fontSize=11,
        textColor=NEAR_BLACK,
        spaceAfter=6,
        spaceBefore=8)
    
    # Body text
    body = ParagraphStyle('FlyBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=NEAR_BLACK,
        leading=15,
        alignment=TA_JUSTIFY,
        spaceAfter=10)
    
    # Pull quote / emphasis text (larger, bold)
    pullquote = ParagraphStyle('PullQuote',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        textColor=RED,
        leading=18,
        alignment=TA_CENTER,
        spaceBefore=12,
        spaceAfter=12,
        leftIndent=30,
        rightIndent=30)
    
    # Callout box (yellow background)
    callout = ParagraphStyle('Callout',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        textColor=NEAR_BLACK,
        backColor=YELLOW_BG,
        borderColor=YELLOW_BORDER,
        borderWidth=2,
        borderPadding=12,
        leading=16,
        alignment=TA_LEFT,
        spaceBefore=12,
        spaceAfter=12,
        leftIndent=15,
        rightIndent=15)
    
    # Important box (red background)
    important = ParagraphStyle('Important',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        textColor=NEAR_BLACK,
        backColor=RED_BG,
        borderColor=LIGHT_RED,
        borderWidth=2,
        borderPadding=12,
        leading=16,
        alignment=TA_LEFT,
        spaceBefore=12,
        spaceAfter=12,
        leftIndent=15,
        rightIndent=15)
    
    # Note text (smaller, gray)
    note = ParagraphStyle('Note',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        textColor=GRAY,
        leading=12,
        alignment=TA_JUSTIFY,
        spaceAfter=6,
        leftIndent=20)
    
    # Client name subtitle
    client_info = ParagraphStyle('ClientInfo',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=14,
        textColor=GRAY,
        spaceAfter=20,
        alignment=TA_LEFT)
    
    # Bold body (for emphasis within paragraphs)
    bold_body = ParagraphStyle('BoldBody',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=NEAR_BLACK,
        leading=15,
        alignment=TA_JUSTIFY,
        spaceAfter=10)
    
    return {
        'brand_bar': brand_bar,
        'page_title': page_title,
        'header': header,
        'section': section,
        'subsection': subsection,
        'small_header': small_header,
        'body': body,
        'pullquote': pullquote,
        'callout': callout,
        'important': important,
        'note': note,
        'client_info': client_info,
        'bold_body': bold_body
    }

def create_horizontal_rule():
    """Create a styled horizontal line separator"""
    return HRFlowable(
        width="100%",
        thickness=1,
        color=GOLD,
        spaceBefore=12,
        spaceAfter=12
    )

def parse_markdown_table(table_text):
    """
    Parse markdown table into list of lists
    
    Example input:
    | Header 1 | Header 2 |
    |----------|----------|
    | Data 1   | Data 2   |
    """
    lines = [line.strip() for line in table_text.strip().split('\n') if line.strip()]
    
    # Remove separator line (contains dashes)
    lines = [line for line in lines if not re.match(r'^\|[\s\-\|]+\|$', line)]
    
    table_data = []
    for line in lines:
        # Remove leading/trailing pipes and split
        cells = [cell.strip() for cell in line.strip('|').split('|')]
        table_data.append(cells)
    
    return table_data

def create_styled_table(table_data, col_widths=None):
    """Create ReportLab table with Fly Straight styling"""
    
    if not col_widths:
        # Auto-calculate column widths
        num_cols = len(table_data[0])
        available_width = 6.5 * inch  # Page width minus margins
        col_widths = [available_width / num_cols] * num_cols
    
    table = Table(table_data, colWidths=col_widths)
    
    # Style first row as header
    table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), BLACK),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        
        # Data rows - alternating colors for readability
        ('BACKGROUND', (0, 1), (-1, -1), LIGHT_GRAY),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        
        # All cells
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 1, GOLD),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    return table

def detect_callout_type(text):
    """Detect if text should be a callout box and which type"""
    text_upper = text.upper()
    
    # Important/Critical boxes (red)
    if any(keyword in text_upper for keyword in [
        'CRITICAL', 'DO NOT TRAIN FASTED', 'NON-NEGOTIABLE', 
        'IMPORTANT', 'WARNING', 'NEVER'
    ]):
        return 'important'
    
    # Callout boxes (yellow)
    if any(keyword in text_upper for keyword in [
        'THE FIX', 'WHY THIS MATTERS', 'WHY THIS WORKS',
        'HOW THIS WORKS', 'THE SCIENCE', 'THE REALITY',
        'THE TRUTH', 'THE MATH', 'WHAT HAPPENED',
        'VEGETABLES ARE UNLIMITED'
    ]):
        return 'callout'
    
    # Pull quotes (centered, bold, red)
    if any(keyword in text_upper for keyword in [
        'YOU ARE NOT BROKEN', 'YOU ARE NOT STARTING FROM ZERO',
        'LET\'S', 'THIS IS NOT TEMPORARY', 'PROTEIN IS KING',
        'STRUCTURE IS HERE', 'NO GUESSWORK'
    ]) and len(text) < 100:  # Short impactful phrases
        return 'pullquote'
    
    return None

def parse_markdown_to_story(markdown_content, client_name, custom_styles):
    """
    Parse markdown content and convert to ReportLab story elements
    Enhanced with callout detection and better visual hierarchy
    """
    story = []
    
    # Split into lines
    lines = markdown_content.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines (but add small spacer for breathing room)
        if not line:
            story.append(Spacer(1, 4))
            i += 1
            continue
        
        # Main header (# TITLE)
        if line.startswith('# ') and not line.startswith('## '):
            text = line[2:].strip()
            if 'PRECISION FUEL PROTOCOL' in text.upper():
                story.append(Paragraph(f'<b>{text}</b>', custom_styles['header']))
            else:
                # Use page_title for major section headers
                story.append(Paragraph(f'<b>{text}</b>', custom_styles['page_title']))
            story.append(Spacer(1, 6))
            i += 1
            continue
        
        # Section header (## SECTION)
        if line.startswith('## '):
            text = line[3:].strip()
            story.append(Paragraph(f'<b>{text}</b>', custom_styles['section']))
            story.append(Spacer(1, 4))
            i += 1
            continue
        
        # Subsection header (### SUBSECTION)
        if line.startswith('### '):
            text = line[4:].strip()
            story.append(Paragraph(f'<b>{text}</b>', custom_styles['subsection']))
            i += 1
            continue
        
        # Small header (#### SMALL)
        if line.startswith('#### '):
            text = line[5:].strip()
            story.append(Paragraph(f'<b>{text}</b>', custom_styles['small_header']))
            i += 1
            continue
        
        # Table detection (starts with |)
        if line.startswith('|'):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                table_lines.append(lines[i])
                i += 1
            
            table_text = '\n'.join(table_lines)
            table_data = parse_markdown_table(table_text)
            
            if table_data:
                table = create_styled_table(table_data)
                story.append(table)
                story.append(Spacer(1, 16))
            
            continue
        
        # Horizontal rule (visual separator)
        if line == '---':
            story.append(create_horizontal_rule())
            i += 1
            continue
        
        # Page break (use ===)
        if line == '===':
            story.append(PageBreak())
            i += 1
            continue
        
        # Detect callout boxes and pull quotes
        callout_type = detect_callout_type(line)
        
        if callout_type:
            # Remove markdown formatting
            text = re.sub(r'\*\*(.+?)\*\*', r'\1', line)
            
            if callout_type == 'pullquote':
                story.append(Paragraph(f'<i>{text}</i>', custom_styles['pullquote']))
            elif callout_type == 'important':
                story.append(Paragraph(text, custom_styles['important']))
            elif callout_type == 'callout':
                story.append(Paragraph(text, custom_styles['callout']))
            
            story.append(Spacer(1, 8))
            i += 1
            continue
        
        # Bold standalone text (**text**)
        if line.startswith('**') and line.endswith('**') and line.count('**') == 2:
            text = line.strip('*')
            story.append(Paragraph(f'<b>{text}</b>', custom_styles['bold_body']))
            i += 1
            continue
        
        # Blockquote (starts with >)
        if line.startswith('> '):
            text = line[2:].strip()
            story.append(Paragraph(f'<i>{text}</i>', custom_styles['note']))
            i += 1
            continue
        
        # Regular paragraph
        # Convert markdown bold (**text**) to ReportLab bold
        line = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', line)
        
        # Convert markdown italic (*text* or _text_)
        line = re.sub(r'\*(.+?)\*', r'<i>\1</i>', line)
        line = re.sub(r'_(.+?)_', r'<i>\1</i>', line)
        
        # Convert bullets
        if line.startswith('- ') or line.startswith('• '):
            line = '• ' + line[2:]
        
        # Check if line starts with ■ (for elimination lists, etc.)
        if line.startswith('■'):
            line = f'<b>{line}</b>'
        
        story.append(Paragraph(line, custom_styles['body']))
        i += 1
    
    return story

def generate_fuel_protocol_pdf(markdown_content, client_name):
    """
    Main function: Generate Fly Straight branded PDF from markdown
    Enhanced with better visual design
    
    Returns: BytesIO buffer containing PDF
    """
    
    # Create in-memory buffer
    buffer = io.BytesIO()
    
    # Create PDF document
    doc = SimpleDocTemplate(buffer,
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch)
    
    # Get styles
    custom_styles = create_styles()
    
    # Build story
    story = []
    
    # COVER PAGE
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph('<b>FLY STRAIGHT</b>', custom_styles['brand_bar']))
    story.append(Spacer(1, 0.3*inch))
    
    # Parse markdown and add to story
    content_story = parse_markdown_to_story(markdown_content, client_name, custom_styles)
    story.extend(content_story)
    
    # CLOSING BRAND BAR
    story.append(Spacer(1, 0.4*inch))
    story.append(Paragraph('<b>FLY STRAIGHT TRANSFORMATION</b>', custom_styles['brand_bar']))
    
    # Build PDF
    doc.build(story)
    
    # Reset buffer position
    buffer.seek(0)
    
    return buffer
