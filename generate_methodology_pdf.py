import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_pdf():
    output_dir = '/Users/garethperry/.gemini/antigravity/brain/fb917de1-2433-4404-8b52-2d1d797295a5'
    os.makedirs(output_dir, exist_ok=True)
    
    path_artifact = os.path.join(output_dir, 'crossref_citation_tally_methodology.pdf')
    path_local = 'crossref_citation_tally_methodology.pdf'
    
    doc = SimpleDocTemplate(path_local, pagesize=letter,
                            rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
    
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=colors.HexColor('#1f77b4'),
        spaceAfter=15
    )
    
    h1_style = ParagraphStyle(
        'Heading1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#333333'),
        spaceBefore=14,
        spaceAfter=8,
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
    
    code_style = ParagraphStyle(
        'CodeStyle',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#555555'),
        backColor=colors.HexColor('#f5f5f5'),
        borderPadding=6,
        spaceAfter=10
    )

    story = []
    
    # Document Title
    story.append(Paragraph("Methodology Report: Crossref Citation Tallying & DOI Resolution", title_style))
    story.append(Paragraph("This document explains the programmatic methodology used in the SuperDARN plotting scripts to fetch, resolve, and aggregate citation counts using the open Crossref Metadata Index.", body_style))
    story.append(Spacer(1, 10))
    
    # Section 1: Registry Ingestion
    story.append(Paragraph("1. Registry Ingestion & Pre-Processing", h1_style))
    story.append(Paragraph("The script first downloads the official SuperDARN Canada Publications Registry as a CSV database from their server:", body_style))
    story.append(Paragraph("• <b>Source URL:</b> <code>https://sdc-serv.usask.ca/website_updating_tools/publication_reports/articles_2SWA2C.csv</code>", bullet_style))
    story.append(Paragraph("• <b>Parsing Fields:</b> Reads the columns: <code>DOI</code>, <code>Title</code>, <code>First Author</code>, and <code>Publication Date</code>.", bullet_style))
    story.append(Paragraph("• <b>DOI Classification:</b> Records with a valid DOI (starting with <code>10.</code>) are mapped directly to their publication year. Records with missing, empty, or placeholder DOIs (such as <i>'Incomplete Data'</i>) are sent to the fallback bibliographical resolution queue. This is crucial for the 179 papers published between 1995 and 2001, which lack DOIs in the database.", bullet_style))
    story.append(Spacer(1, 8))

    # Section 2: DOI-Based Batch Querying
    story.append(Paragraph("2. DOI-Based Batch Querying (For Papers with DOIs)", h1_style))
    story.append(Paragraph("For the papers containing pre-existing DOIs (primarily 2002–2025), querying them individually would be slow and trigger rate limits. To solve this, the script performs batch querying:", body_style))
    story.append(Paragraph("• <b>Batching:</b> DOIs are split into groups of 50.", bullet_style))
    story.append(Paragraph("• <b>Filtering:</b> Joined into a comma-separated filter string: <code>doi:10.1029/abc,doi:10.1016/xyz,...</code>", bullet_style))
    story.append(Paragraph("• <b>Query Endpoint:</b> The script calls the Crossref <code>/works</code> API requesting selected fields to minimize payload size:", bullet_style))
    story.append(Paragraph("GET https://api.crossref.org/works?filter={filter_string_url_encoded}&amp;rows=50&amp;select=DOI,is-referenced-by-count", code_style))
    story.append(Paragraph("• <b>Data Extraction:</b> Reads the <code>is-referenced-by-count</code> field (the lifetime citations received across indexed publishers) and adds it to the tally for that paper's publication year.", bullet_style))
    story.append(Spacer(1, 8))

    # Section 3: Bibliographic Fallback Resolution
    story.append(Paragraph("3. Bibliographic Fallback Resolution (For Papers without DOIs)", h1_style))
    story.append(Paragraph("For the 386 registry papers lacking DOIs (including all early papers from 1995–2001), the script falls back to a bibliographical search on the Crossref index:", body_style))
    story.append(Paragraph("• <b>Search Query:</b> Combines the paper title and the first author's name: <code>'{title} {author}'</code>.", bullet_style))
    story.append(Paragraph("• <b>API Call:</b> Queries Crossref for the single most relevant search match:", bullet_style))
    story.append(Paragraph("GET https://api.crossref.org/works?query={query_string_url_encoded}&amp;rows=1&amp;select=DOI,is-referenced-by-count", code_style))
    story.append(Paragraph("• <b>Tallying:</b> Selects the top search result, extracts its <code>is-referenced-by-count</code> citation metric, and attributes it to the publication year of the original registry record.", bullet_style))
    story.append(Spacer(1, 8))

    # Section 4: Year-by-Year Aggregation
    story.append(Paragraph("4. Year-by-Year Aggregation", h1_style))
    story.append(Paragraph("Once both batches and resolved searches are processed, citations are grouped by publication year:", body_style))
    story.append(Paragraph("• <b>Annual Citations:</b> Computes the sum of citations of all papers published in year <i>y</i>.", bullet_style))
    story.append(Paragraph("• <b>Cumulative Citations:</b> The cumulative total of citations representing the impact of all papers published up to year <i>y</i> is computed using the running sum of these citation totals over time. This is implemented using NumPy's cumulative sum: <code>np.cumsum(annual_citations)</code>.", bullet_style))
    
    # Build Document
    doc.build(story)
    
    # Copy to artifact directory
    import shutil
    shutil.copy2(path_local, path_artifact)
    print(f"Successfully generated methodology PDF at:\n- {path_local}\n- {path_artifact}")

if __name__ == '__main__':
    generate_pdf()
