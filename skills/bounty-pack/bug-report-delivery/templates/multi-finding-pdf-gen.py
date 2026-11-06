#!/usr/bin/env python3
"""Reusable multi-finding bug bounty PDF generator.

Generates per-finding PDFs with embedded POC screenshots, meta tables,
severity coloring, and code blocks. Each finding gets its own directory.

Usage:
    Edit the FINDINGS list below with your actual data, then run:
    python multi-finding-pdf-gen.py

Output:
    <BASE>/<finding_id>/  — each contains screenshots + PDF
    Filename pattern: Fireblocks-F1-Cloudinary-Unauth-Upload.pdf

Dependencies: Pillow, reportlab
Python: Use correct path on Windows:
    /c/Users/WINDOWS10/AppData/Local/Python/bin/python.exe
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    KeepTogether, Image as RLImage
)
from PIL import Image as PILImage
import os, textwrap

BASE = r"C:\Users\WINDOWS10\fireblocks-bounty"
W, H = A4  # unpack for width reference only — pagesize=A4 (tuple) in doc

SEV_COLORS = {
    'CRITICAL': HexColor('#dc3545'),
    'HIGH': HexColor('#fd7e14'),
    'MEDIUM': HexColor('#ffc107'),
    'LOW': HexColor('#28a745'),
    'INFO': HexColor('#17a2b8'),
}

# ============================================================
# DEFINE YOUR FINDINGS HERE
# Each finding dict drives: meta table, screenshots, code blocks
# ============================================================
FINDINGS = [
    {
        'id': 'F1',
        'title': 'Cloudinary Unauthenticated Upload',
        'severity': 'HIGH',
        'program': 'Fireblocks',
        'platform': 'HackerOne',
        'cvss': '7.5 (High)',
        'endpoint': 'https://api.cloudinary.com/v1_1/fireblocks/image/upload',
        'reporter': 'BC_USERNAME',
        'summary': [
            'The Fireblocks Cloudinary upload presets are accessible without '
            'authentication. An attacker can upload arbitrary files (images, '
            'HTML, JavaScript, SVGs with embedded scripts) to Fireblocks\' '
            'Cloudinary account using the public upload preset.'
        ],
        'screenshots': [
            ('01-us-upload-request.png', 'US Cloudinary upload request (no auth)'),
            ('02-us-upload-response.png', 'Upload succeeded — file hosted publicly'),
            ('03-eu-upload-response.png', 'EU Cloudinary also accepts unauth upload'),
            ('04-html-upload.png', 'Malicious HTML uploaded and served'),
            ('05-raw-content-accessible.png', 'Raw HTML served with text/html content-type'),
            ('06-svg-upload.png', 'SVG with embedded JS accepted'),
        ],
        'code_blocks': [
            ('US Upload (no auth)', 'curl -X POST '
             '"https://api.cloudinary.com/v1_1/fireblocks/image/upload" '
             '-F "upload_preset=kgdyxtmr" '
             '-F "file=@malicious.html"'),
            ('EU Upload (no auth)', 'curl -X POST '
             '"https://api.cloudinary.com/v1_1/dvkywpcq6/image/upload" '
             '-F "upload_preset=gz7mvatc" '
             '-F "file=@malicious.html"'),
        ],
        'impact': 'Attacker can host phishing pages on *.cloudinary.com domain, '
                  'bypassing CSP. Uploaded SVGs with JS execute in victims\' browsers. '
                  'Degrades trust in Fireblocks domain.',
    },
    # Add more findings here following the same structure...
]

# ============================================================
# BELOW THIS LINE — GENERATOR CODE (usually no edits needed)
# ============================================================

def screenshot_flowable(filepath, caption_text, max_width=460, max_height=340):
    """Embed screenshot image with caption, auto-scaled to fit."""
    styles = getSampleStyleSheet()
    caption_style = ParagraphStyle('Caption2', parent=styles['Normal'],
                                    fontSize=8, leading=10, alignment=1,
                                    textColor=HexColor('#666666'))
    if not os.path.exists(filepath):
        return Paragraph(f"[Screenshot not found: {os.path.basename(filepath)}]",
                         caption_style)
    img = RLImage(filepath)
    aspect = img.imageWidth / img.imageHeight
    w = max_width
    h = w / aspect
    if h > max_height:
        h = max_height
        w = h * aspect
    img.drawWidth = w
    img.drawHeight = h
    img.hAlign = 'CENTER'
    caption = Paragraph(f"<i>{caption_text}</i>", caption_style)
    return KeepTogether([img, caption])


def meta_table(data_rows):
    """Create a styled meta information table."""
    styles = getSampleStyleSheet()
    table_data = [[Paragraph(f'<b>{k}</b>', styles['Normal']),
                    Paragraph(str(v), styles['Normal'])] for k, v in data_rows]
    t = Table(table_data, colWidths=[120, 340])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), HexColor('#f0f0f0')),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    return t


def build_pdf(finding, output_dir):
    """Generate a single finding PDF."""
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir,
        f"{finding['program']}-{finding['id']}-{finding['title'].replace(' ', '-')}.pdf")

    doc = SimpleDocTemplate(output_path, pagesize=A4,
                            topMargin=40, bottomMargin=40,
                            leftMargin=50, rightMargin=50)
    styles = getSampleStyleSheet()

    # Register custom styles (avoid name collisions with built-ins)
    styles.add(ParagraphStyle('CodeBlock2', parent=styles['Normal'],
                              fontName='Courier', fontSize=8, leading=10,
                              backColor=HexColor('#f4f4f4')))
    styles.add(ParagraphStyle('FindingTitle', parent=styles['Title'],
                              fontSize=16, spaceAfter=6))

    story = []

    # Title + severity
    sev_color = SEV_COLORS.get(finding['severity'].upper(), HexColor('#6c757d'))
    story.append(Paragraph(
        f"PRIVATE SECURITY DISCLOSURE — {finding['program']}",
        styles['FindingTitle']))
    story.append(Paragraph(
        f"<font color='{sev_color}'><b>[{finding['severity']}]</b></font> "
        f"{finding['title']}",
        styles['Normal']))
    story.append(Spacer(1, 12))

    # Meta table
    story.append(meta_table([
        ('Program', finding['program']),
        ('Platform', finding['platform']),
        ('Severity', f"{finding['severity']} ({finding['cvss']})"),
        ('Endpoint', finding['endpoint']),
        ('Researcher', finding['reporter']),
    ]))
    story.append(Spacer(1, 16))

    # Summary
    story.append(Paragraph('<b>Summary</b>', styles['Heading2']))
    for para in finding.get('summary', []):
        story.append(Paragraph(para, styles['Normal']))
        story.append(Spacer(1, 6))

    # Code blocks (request/response)
    if finding.get('code_blocks'):
        story.append(Paragraph('<b>Proof of Concept — Steps</b>', styles['Heading2']))
        for label, code in finding['code_blocks']:
            story.append(Paragraph(f"<b>{label}</b>", styles['Normal']))
            story.append(Paragraph(
                f"<font face='Courier' size='8'>{code}</font>",
                styles['CodeBlock2']))
            story.append(Spacer(1, 8))

    # Screenshots
    if finding.get('screenshots'):
        story.append(Paragraph('<b>Evidence Screenshots</b>', styles['Heading2']))
        for fname, caption in finding['screenshots']:
            fpath = os.path.join(output_dir, fname)
            story.append(screenshot_flowable(fpath, caption))
            story.append(Spacer(1, 10))

    # Impact
    if finding.get('impact'):
        story.append(Paragraph('<b>Impact</b>', styles['Heading2']))
        story.append(Paragraph(finding['impact'], styles['Normal']))

    doc.build(story)
    print(f"  PDF: {output_path}")
    return output_path


def main():
    print("Generating per-finding PDF reports...")
    for finding in FINDINGS:
        fdir = os.path.join(BASE, f"{finding['id'].lower()}-{finding['title'].split()[0].lower()}")
        build_pdf(finding, fdir)
    print("Done.")


if __name__ == '__main__':
    main()
