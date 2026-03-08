"""
Fly Straight PDF Generator - Professional Edition
Converts markdown Precision Fuel Protocol to fully branded PDF
with proper spacing, page flow, and visual hierarchy
"""

import io
import re
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
    PageBreak, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

# ============================================================================
# FLY STRAIGHT BRAND COLORS (EXACT)
# ============================================================================
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

# ============================================================================
# STYLE DEFINITIONS
# ============================================================================

def create_styles():
    """Create all Fly Straight paragraph styles"""
    styles = getSampleStyleSheet()
    
    custom_styles = {}
    
    # Brand bar (FLY STRAIGHT header/footer)
    custom_styles['brand_bar'] = ParagraphStyle(
        'BrandBar',
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
        rightIndent=0
    )
    
    # Main title (PRECISION FUEL PROTOCOL)
    custom_styles['main_title'] = ParagraphStyle(
        'MainTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=28,
        textColor=BLACK,
        spaceAfter=6,
        spaceBefore=0,
        alignment=TA_LEFT,
        leading=32
    )
    
    # Client name subtitle
    custom_styles['client_name'] = ParagraphStyle(
        'ClientName',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        textColor=GRAY,
        spaceAfter=20,
        alignment=TA_LEFT
    )
    
    # Section headers (RED, large)
    custom_styles['section'] = ParagraphStyle(
        'Section',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=16,
        textColor=RED,
        spaceAfter=8,
        spaceBefore=14,
        leading=20,
        alignment=TA_LEFT
    )
    
    # Subsection headers (smaller, black)
    custom_styles['subsection'] = ParagraphStyle(
        'Subsection',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=13,
        textColor=NEAR_BLACK,
        spaceAfter=6,
        spaceBefore=10,
        leading=16,
        alignment=TA_LEFT
    )
    
    # Body text (justified, proper spacing)
    custom_styles['body'] = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=NEAR_BLACK,
        leading=15,
        alignment=TA_JUSTIFY,
        spaceAfter=8,
        leftIndent=0,
        rightIndent=0
    )
    
    # Body text centered
    custom_styles['body_center'] = ParagraphStyle(
        'BodyCenter',
        parent=custom_styles['body'],
        alignment=TA_CENTER
    )
    
    # Bullet list item
    custom_styles['bullet'] = ParagraphStyle(
        'Bullet',
        parent=custom_styles['body'],
        leftIndent=12,
        bulletIndent=6,
        spaceAfter=4
    )
    
    # Yellow callout box
    custom_styles['callout_yellow'] = ParagraphStyle(
        'CalloutYellow',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        textColor=NEAR_BLACK,
        backColor=YELLOW_BG,
        borderColor=YELLOW_BORDER,
        borderWidth=1,
        borderPadding=10,
        leftIndent=12,
        rightIndent=12,
        alignment=TA_JUSTIFY,
        spaceAfter=12,
        spaceBefore=8,
        leading=16
    )
    
    # Red callout box (critical info)
    custom_styles['callout_red'] = ParagraphStyle(
        'CalloutRed',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=NEAR_BLACK,
        backColor=RED_BG,
        borderColor=RED,
        borderWidth=2,
        borderPadding=10,
        leftIndent=12,
        rightIndent=12,
        alignment=TA_CENTER,
        spaceAfter=12,
        spaceBefore=8,
        leading=14
    )
    
    return custom_styles

# ============================================================================
# TABLE STYLING
# ============================================================================

def create_profile_table(data):
    """Create member profile table with Fly Straight styling"""
    table = Table(data, colWidths=[2.0*inch, 4.5*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), LIGHT_GRAY),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 1, GOLD),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    return table

def create_data_table(data, has_header=True):
    """Create data table with header row styling"""
    # Auto-calculate column widths
    num_cols = len(data[0]) if data else 0
    if num_cols == 0:
        return None
    
    available_width = 6.5 * inch
    col_widths = [available_width / num_cols] * num_cols
    
    table = Table(data, colWidths=col_widths)
    
    style_commands = [
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 1, GOLD),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]
    
    if has_header:
        # Header row styling
        style_commands.extend([
            ('BACKGROUND', (0, 0), (-1, 0), BLACK),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            # Data rows
            ('BACKGROUND', (0, 1), (-1, -1), LIGHT_GRAY),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ])
    else:
        # No header, alternate row colors
        style_commands.extend([
            ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GRAY),
        ])
    
    table.setStyle(TableStyle(style_commands))
    return table

# ============================================================================
# MARKDOWN PARSING
# ============================================================================

def clean_markdown(text):
    """Remove artifacts and clean markdown"""
    # Remove "PAGE X" headers
    text = re.sub(r'^PAGE \d+\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^# PAGE \d+\s*$', '', text, flags=re.MULTILINE)
    
    # Remove horizontal rules that are just separators
    text = re.sub(r'^---+\s*$', '', text, flags=re.MULTILINE)
    
    # Remove multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Clean up any stray JSON
    text = re.sub(r'\{"index".*?\}', '', text, flags=re.DOTALL)
    
    return text.strip()

def parse_markdown_table(table_text):
    """Parse markdown table into list of lists"""
    lines = [line.strip() for line in table_text.strip().split('\n') if line.strip()]
    
    # Remove separator lines (contains only pipes, spaces, and dashes)
    lines = [line for line in lines if not re.match(r'^\|[\s\-\|]+\|$', line)]
    
    if not lines:
        return None
    
    table_data = []
    for line in lines:
        # Remove leading/trailing pipes and split
        cells = [cell.strip() for cell in line.strip('|').split('|')]
        table_data.append(cells)
    
    return table_data if table_data else None

def is_callout_trigger(text):
    """Check if text should be rendered as callout box"""
    callout_keywords = [
        'THE FIX', 'WHY THIS MATTERS', 'CRITICAL', 'IMPORTANT',
        'DO NOT', 'NON NEGOTIABLE', 'REMEMBER', 'WARNING',
        'BOTTOM LINE', 'KEY POINT'
    ]
    text_upper = text.upper()
    return any(keyword in text_upper for keyword in callout_keywords)

def parse_markdown_to_story(markdown_content, client_name, styles):
    """
    Parse markdown and convert to ReportLab story elements
    with intelligent page flow and spacing
    """
    story = []
    
    # Clean the markdown first
    markdown_content = clean_markdown(markdown_content)
    
    lines = markdown_content.split('\n')
    i = 0
    
    # Track if we've added cover page
    cover_added = False
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines
        if not line:
            i += 1
            continue
        
        # ===== COVER PAGE DETECTION =====
        if not cover_added and ('PRECISION FUEL PROTOCOL' in line.upper() or 
                                'FLY STRAIGHT' in line.upper()):
            # Add cover page elements
            story.append(Spacer(1, 0.1*inch))
            story.append(Paragraph('<b>FLY STRAIGHT</b>', styles['brand_bar']))
            story.append(Spacer(1, 0.2*inch))
            cover_added = True
            i += 1
            continue
        
        # ===== MAIN HEADERS (# Header) =====
        if line.startswith('# ') and not line.startswith('## '):
            text = line[2:].strip()
            # Skip if it's just "PAGE X"
            if re.match(r'^PAGE \d+$', text, re.IGNORECASE):
                i += 1
                continue
            
            if 'PRECISION FUEL PROTOCOL' in text.upper():
                story.append(Paragraph(f'<b>{text}</b>', styles['main_title']))
            else:
                # Regular section
                story.append(Paragraph(f'<b>{text}</b>', styles['section']))
            i += 1
            continue
        
        # ===== SECTION HEADERS (## Header) =====
        if line.startswith('## '):
            text = line[3:].strip()
            story.append(Paragraph(f'<b>{text}</b>', styles['section']))
            i += 1
            continue
        
        # ===== SUBSECTION HEADERS (### Header) =====
        if line.startswith('### '):
            text = line[4:].strip()
            # Check if it's a callout trigger
            if is_callout_trigger(text):
                # Make it a callout box
                clean_text = text.replace('■', '').strip()
                story.append(Paragraph(clean_text, styles['callout_yellow']))
            else:
                story.append(Paragraph(f'<b>{text}</b>', styles['subsection']))
            i += 1
            continue
        
        # ===== TABLES (starts with |) =====
        if line.startswith('|'):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                table_lines.append(lines[i])
                i += 1
            
            table_text = '\n'.join(table_lines)
            table_data = parse_markdown_table(table_text)
            
            if table_data:
                # Detect table type
                if len(table_data) > 1 and any('Field' in str(cell) or 'FIELD' in str(cell) 
                                                for cell in table_data[0]):
                    # Profile table
                    table = create_profile_table(table_data)
                else:
                    # Data table
                    table = create_data_table(table_data, has_header=True)
                
                if table:
                    story.append(table)
                    story.append(Spacer(1, 12))
            continue
        
        # ===== BOLD TEXT (**text**) =====
        if line.startswith('**') and line.endswith('**'):
            text = line.strip('*').strip()
            
            # Check if it's a callout
            if is_callout_trigger(text):
                clean_text = text.replace('■', '').strip()
                story.append(Paragraph(clean_text, styles['callout_yellow']))
            else:
                # Check if it's a subsection or just bold text
                if len(text) < 80 and not text.endswith('.'):
                    story.append(Paragraph(f'<b>{text}</b>', styles['subsection']))
                else:
                    story.append(Paragraph(f'<b>{text}</b>', styles['body']))
            i += 1
            continue
        
        # ===== BULLET LISTS =====
        if line.startswith('• ') or line.startswith('- ') or line.startswith('■ '):
            bullet_char = line[0]
            text = line[2:].strip()
            
            # Convert markdown bold within bullets
            text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
            
            bullet_text = f'{bullet_char} {text}'
            story.append(Paragraph(bullet_text, styles['bullet']))
            i += 1
            continue
        
        # ===== REGULAR PARAGRAPHS =====
        # Convert markdown bold (**text**)
        line = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', line)
        
        # Detect if it's a special intro paragraph (for cover)
        if not cover_added and i < 10 and len(line) > 100:
            story.append(Paragraph(line, styles['callout_yellow']))
            cover_added = True
        else:
            story.append(Paragraph(line, styles['body']))
        
        i += 1
    
    return story

# ============================================================================
# MAIN PDF GENERATION
# ============================================================================

def generate_fuel_protocol_pdf(markdown_content, client_name):
    """
    Generate professional Fly Straight branded PDF from markdown
    
    Returns: BytesIO buffer containing PDF
    """
    
    # Create in-memory buffer
    buffer = io.BytesIO()
    
    # Create PDF document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch,
        title=f'{client_name} Precision Fuel Protocol',
        author='Fly Straight Transformation'
    )
    
    # Get styles
    styles = create_styles()
    
    # Build story
    story = []
    
    # Parse markdown and add content
    content_story = parse_markdown_to_story(markdown_content, client_name, styles)
    story.extend(content_story)
    
    # Add closing brand bar
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph('<b>FLY STRAIGHT TRANSFORMATION</b>', styles['brand_bar']))
    
    # Build PDF
    try:
        doc.build(story)
    except Exception as e:
        print(f"Error building PDF: {e}")
        # Return error PDF
        error_story = [
            Paragraph('<b>FLY STRAIGHT</b>', styles['brand_bar']),
            Spacer(1, 0.5*inch),
            Paragraph('<b>PDF Generation Error</b>', styles['section']),
            Paragraph(f'Error: {str(e)}', styles['body']),
        ]
        doc.build(error_story)
    
    # Reset buffer position
    buffer.seek(0)
    
    return buffer
