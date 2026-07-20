import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_pdf():
    # Document setup
    output_dir = '/Users/garethperry/.gemini/antigravity/brain/fb917de1-2433-4404-8b52-2d1d797295a5'
    os.makedirs(output_dir, exist_ok=True)
    
    path_artifact = os.path.join(output_dir, 'superdarn_sources_info.pdf')
    path_local = 'superdarn_sources_info.pdf'
    
    # We will build it once and copy to the other to keep it identical
    doc = SimpleDocTemplate(path_local, pagesize=letter,
                            rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
    
    styles = getSampleStyleSheet()
    
    # Custom Styles for Premium Aesthetics
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#1f77b4'),
        spaceAfter=15
    )
    
    h1_style = ParagraphStyle(
        'Heading1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=colors.HexColor('#333333'),
        spaceBefore=15,
        spaceAfter=10,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'BodyText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#444444'),
        spaceAfter=10
    )
    
    bullet_style = ParagraphStyle(
        'BulletText',
        parent=body_style,
        leftIndent=20,
        bulletIndent=10,
        spaceAfter=6
    )
    
    table_text_style = ParagraphStyle(
        'TableText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#333333')
    )
    
    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.white
    )

    story = []
    
    # Document Title
    story.append(Paragraph("SuperDARN Data & Publication Sources", title_style))
    story.append(Paragraph("Documentation of metadata resources, search indices, coordinate models, and filtering criteria.", body_style))
    story.append(Spacer(1, 15))
    
    # Section 1: Radar Hardware Registry
    story.append(Paragraph("1. Radar Location & Hardware Coordinates", h1_style))
    story.append(Paragraph("The coordinates (geographic coordinates and operating altitudes) of the SuperDARN radar stations are retrieved from the official pyDARN library database, which references the authoritative community hardware registry:", body_style))
    story.append(Paragraph("• <b>Source Registry:</b> SuperDARN Hardware Database (<a href='https://github.com/SuperDARN/hdw'>SuperDARN/hdw</a>)", bullet_style))
    story.append(Paragraph("• <b>Retrieval Method:</b> Programmatically parsed using python's <code>pydarn.utils</code> hardware modules, extracting the earliest coordinates for each station.", bullet_style))
    story.append(Paragraph("• <b>Hemisphere Classification:</b> Categorized based on geographic latitude (Northern hemisphere for positive values, Southern hemisphere for negative values).", bullet_style))
    story.append(Spacer(1, 10))

    # Section 2: Geomagnetic Coordinates Model
    story.append(Paragraph("2. Altitude-Adjusted Corrected Geomagnetic (AACGM) Model", h1_style))
    story.append(Paragraph("Because the Earth's magnetic field changes over time and has non-dipolar components, geographic coordinates do not line up with magnetic coordinates. We converted the geographic coordinates using the following models:", body_style))
    story.append(Paragraph("• <b>Coordinate Engine:</b> AACGM-v2 (Altitude-Adjusted Corrected Geomagnetic coordinates, Version 2) C-library implementation.", bullet_style))
    story.append(Paragraph("• <b>Python Library:</b> <code>aacgmv2</code> (Version 2.7.1), wrapping the standard geomagnetic coordinate transforms.", bullet_style))
    story.append(Paragraph("• <b>Epoch Settings:</b> The AACGM coordinates are computed dynamically for the specific year each radar went operational to capture the secular variation of the magnetic field.", bullet_style))
    story.append(Spacer(1, 10))

    # Section 3: Publications Data & Search Parameters
    story.append(Paragraph("3. Scientific Publication & Citation Metrics", h1_style))
    story.append(Paragraph("Publication counts were programmatically parsed from the official SuperDARN Canada registry. Corresponding citation metrics were retrieved directly from the Crossref scholarly metadata index using the DOIs registered by the network:", body_style))
    story.append(Paragraph("• <b>Publication Database:</b> SuperDARN Canada Official Publications Registry (<code>https://superdarn.ca/publications</code>)", bullet_style))
    story.append(Paragraph("• <b>Citation Database:</b> Crossref Metadata Search API (<code>https://api.crossref.org/works</code>)", bullet_style))
    story.append(Paragraph("• <b>Retrieval Method:</b> Programmatically parsed the registry's CSV, extracted DOIs, and batch queried Crossref in groups of 50 using filter queries to fetch <code>is-referenced-by-count</code> metadata.", bullet_style))
    story.append(Paragraph("• <b>Citation Cohorts:</b> Citations are associated with the publication year of the papers. The cumulative curve shows the total citations of papers published up to each year.", bullet_style))
    story.append(Spacer(1, 15))

    # Section 4: Data Sources Summary Table
    story.append(Paragraph("4. Summary of Data Sources", h1_style))
    
    table_data = [
        [
            Paragraph("Dataset / Feature", table_header_style), 
            Paragraph("Primary Source", table_header_style), 
            Paragraph("Provider / Institution", table_header_style), 
            Paragraph("Access Link / API", table_header_style)
        ],
        [
            Paragraph("Radar Station Metadata", table_text_style),
            Paragraph("SuperDARN hdw Registry", table_text_style),
            Paragraph("SuperDARN Data Simulator Working Group", table_text_style),
            Paragraph("<a href='https://github.com/SuperDARN/hdw'>github.com/SuperDARN/hdw</a>", table_text_style)
        ],
        [
            Paragraph("Geomagnetic Coordinates", table_text_style),
            Paragraph("AACGM-v2 Model", table_text_style),
            Paragraph("SuperDARN Collaboration / NASA", table_text_style),
            Paragraph("via python <code>aacgmv2</code> wrapper", table_text_style)
        ],
        [
            Paragraph("Publications Registry", table_text_style),
            Paragraph("SuperDARN Canada Portal", table_text_style),
            Paragraph("University of Saskatchewan", table_text_style),
            Paragraph("<a href='https://superdarn.ca/publications'>superdarn.ca/publications</a>", table_text_style)
        ],
        [
            Paragraph("Citation Metadata", table_text_style),
            Paragraph("Crossref Index", table_text_style),
            Paragraph("Publishers International Linking Association", table_text_style),
            Paragraph("<a href='https://api.crossref.org/works'>api.crossref.org/works</a>", table_text_style)
        ]
    ]
    
    t = Table(table_data, colWidths=[110, 110, 140, 144])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1f77b4')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
        ('TOPPADDING', (0,0), (-1,0), 8),
        ('BOTTOMPADDING', (0,1), (-1,-1), 8),
        ('TOPPADDING', (0,1), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#f9f9f9')),
        ('BACKGROUND', (0,3), (-1,3), colors.HexColor('#f9f9f9')),
    ]))
    story.append(t)
    story.append(Spacer(1, 15))
    
    # Section 5: Plotting Methodologies
    story.append(Paragraph("5. Visualization Variants", h1_style))
    story.append(Paragraph("Two separate publication and citation plots have been compiled:", body_style))
    story.append(Paragraph("• <b>Hybrid Registry & Crossref Plot:</b> Uses the official 1,303 peer-reviewed paper registry from SuperDARN Canada as the source of publications (bars), and queries the Crossref API using their registered DOIs to compile the cumulative citation totals.", bullet_style))
    story.append(Paragraph("• <b>Crossref-Only Plot:</b> Restricts both publication counts and citation metrics solely to the Crossref database. The query searches for works matching the term 'SuperDARN' (yielding 414 total publications and 6,926 cumulative citations by 2025).", bullet_style))
    
    # Build Document
    doc.build(story)
    
    # Copy to artifact directory
    import shutil
    shutil.copy2(path_local, path_artifact)
    print(f"Successfully generated sources PDF at:\n- {path_local}\n- {path_artifact}")

if __name__ == '__main__':
    generate_pdf()
