"""
PDF Generator for Fly Straight Precision Fuel Protocol
Converts markdown content to branded PDF
"""

import io
import re
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
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

def create_styles():
    """Create Fly Straight branded paragraph styles"""
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
        spaceAfter=6)
    
    # Main header (PRECISION FUEL PROTOCOL)
    header = ParagraphStyle('FlyHeader',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=28,
        textColor=BLACK,
        spaceAfter=6,
        alignment=TA_LEFT,
        leading=32)
    
    # Section headers (red)
    section = ParagraphStyle('FlySection',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=16,
        textColor=RED,
        spaceAfter=8,
        spaceBefore=14,
        leading=20)
    
    # Subsection headers
    subsection = ParagraphStyle('SubSection',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=13,
        textColor=NEAR_BLACK,
        spaceAfter=6,
        spaceBefore=10)
    
    # Body text
    body = ParagraphStyle('FlyBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=NEAR_BLACK,
        leading=15,
        alignment=TA_JUSTIFY,
        spaceAfter=8)
    
    # Client name subtitle
    client_info = ParagraphStyle('ClientInfo',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        textColor=GRAY,
        spaceAfter=20)
    
    return {
        'brand_bar': brand_bar,
        'header': header,
        'section': section,
        'subsection': subsection,
        'body': body,
        'client_info': client_info
    }

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
        
        # Data rows
        ('BACKGROUND', (0, 1), (-1, -1), LIGHT_GRAY),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        
        # All cells
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 1, GOLD),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    return table

def parse_markdown_to_story(markdown_content, client_name, custom_styles):
    """
    Parse markdown content and convert to ReportLab story elements
    """
    story = []
    
    # Split into lines
    lines = markdown_content.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines
        if not line:
            i += 1
            continue
        
        # Main header (# TITLE)
        if line.startswith('# ') and not line.startswith('## '):
            text = line[2:].strip()
            if 'PRECISION FUEL PROTOCOL' in text.upper():
                story.append(Paragraph(f'<b>{text}</b>', custom_styles['header']))
            else:
                story.append(Paragraph(text, custom_styles['section']))
            i += 1
            continue
        
        # Section header (## SECTION)
        if line.startswith('## '):
            text = line[3:].strip()
            story.append(Paragraph(f'<b>{text}</b>', custom_styles['section']))
            i += 1
            continue
        
        # Subsection header (### SUBSECTION)
        if line.startswith('### '):
            text = line[4:].strip()
            story.append(Paragraph(f'<b>{text}</b>', custom_styles['subsection']))
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
                story.append(Spacer(1, 12))
            
            continue
        
        # Horizontal rule (page break or section separator)
        if line == '---':
            story.append(Spacer(1, 12))
            i += 1
            continue
        
        # Bold text (**text**)
        if line.startswith('**') and line.endswith('**'):
            text = line.strip('*')
            # Check if it's a callout box trigger
            if any(keyword in text.upper() for keyword in ['THE FIX', 'WHY THIS MATTERS', 'CRITICAL', 'CALLOUT']):
                # Create callout box
                callout_style = ParagraphStyle('Callout',
                    parent=custom_styles['body'],
                    fontName='Helvetica-Bold',
                    backColor=YELLOW_BG,
                    borderColor=YELLOW_BORDER,
                    borderWidth=1,
                    borderPadding=10,
                    leftIndent=12,
                    rightIndent=12,
                    alignment=TA_CENTER if 'FIX' in text.upper() else TA_JUSTIFY)
                story.append(Paragraph(text, callout_style))
                story.append(Spacer(1, 12))
            else:
                story.append(Paragraph(f'<b>{text}</b>', custom_styles['subsection']))
            i += 1
            continue
        
        # Regular paragraph
        # Convert markdown bold (**text**) to ReportLab bold
        line = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', line)
        # Convert markdown bullets
        if line.startswith('- ') or line.startswith('• '):
            line = '• ' + line[2:]
        
        story.append(Paragraph(line, custom_styles['body']))
        i += 1
    
    return story

def generate_fuel_protocol_pdf(markdown_content, client_name):
    """
    Main function: Generate Fly Straight branded PDF from markdown
    
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
    story.append(Spacer(1, 0.2*inch))
    
    # Parse markdown and add to story
    content_story = parse_markdown_to_story(markdown_content, client_name, custom_styles)
    story.extend(content_story)
    
    # CLOSING BRAND BAR
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph('<b>FLY STRAIGHT TRANSFORMATION</b>', custom_styles['brand_bar']))
    
    # Build PDF
    doc.build(story)
    
    # Reset buffer position
    buffer.seek(0)
    
    return buffer
