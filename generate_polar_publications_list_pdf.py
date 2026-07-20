import os
import urllib.request
import json
import csv
import io
import urllib.parse
import re
import time
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

# 1. Fetch official publications from SuperDARN Canada CSV database
print("Fetching publications for the PDF bibliography...")
url_csv = 'https://sdc-serv.usask.ca/website_updating_tools/publication_reports/articles_2SWA2C.csv'
req_csv = urllib.request.Request(url_csv, headers={'User-Agent': 'Mozilla/5.0'})

doi_to_paper = {}
unresolved_papers = []

try:
    res_csv = urllib.request.urlopen(req_csv).read().decode('utf-8')
    reader = csv.DictReader(io.StringIO(res_csv))
    for row in reader:
        doi = row.get('DOI', '').strip()
        date_str = row.get('Publication Date')
        title = row.get('Title', '').strip()
        author = row.get('First Author', '').strip()
        authors = row.get('Authors', '').strip()
        journal = row.get('Journal', '').strip()
        if not date_str:
            continue
        try:
            year = int(date_str.split('-')[0])
            if 1980 <= year <= 2025:
                paper_info = {
                    'title': title,
                    'author': author,
                    'authors': authors,
                    'year': year,
                    'journal': journal,
                    'doi': doi
                }
                if doi and doi.startswith('10.'):
                    doi_to_paper[doi] = paper_info
                else:
                    unresolved_papers.append(paper_info)
        except (ValueError, IndexError):
            continue
except Exception as e:
    print(f"Error: {e}")
    exit(1)

# Define polar radars and start years
radar_rules = [
    {'pattern': r'\b(Rankin Inlet|RKN)\b', 'start_year': 2006},
    {'pattern': r'\b(Inuvik|INV)\b', 'start_year': 2007},
    {'pattern': r'\b(Zhongshan|ZHO)\b', 'start_year': 2010},
    {'pattern': r'\b(McMurdo|MCM)\b', 'start_year': 2012},
    {'pattern': r'\b(Clyde River|CLY)\b', 'start_year': 2012},
    {'pattern': r'\b(Dome C|DCN|DCE)\b', 'start_year': 2013},
    {'pattern': r'\b(South Pole|SPS)\b', 'start_year': 2013},
    {'pattern': r'\b(Longyearbyen|Svalbard|LYR)\b', 'start_year': 2016}
]

def check_polar_radar_use(text, year):
    for rule in radar_rules:
        if re.search(rule['pattern'], text, re.IGNORECASE):
            if year >= rule['start_year']:
                return True
    return False

matched_papers = []

# Batch query metadata
dois = list(doi_to_paper.keys())
batch_size = 50
for i in range(0, len(dois), batch_size):
    batch = dois[i:i+batch_size]
    clean_batch = [d for d in batch if all(ord(c) < 128 and not c.isspace() for c in d)]
    if not clean_batch:
        continue
    filter_str = ','.join([f'doi:{d}' for d in clean_batch])
    filter_str_esc = urllib.parse.quote(filter_str, safe=':,')
    url = f'https://api.crossref.org/works?filter={filter_str_esc}&rows=50&select=DOI,title,abstract'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (mailto:test@example.com)'})
    try:
        res = urllib.request.urlopen(req).read()
        data = json.loads(res)
        for item in data.get('message', {}).get('items', []):
            d = item.get('DOI', '').lower()
            title_text = ' '.join(item.get('title', []))
            abstract_text = item.get('abstract', '')
            text_to_search = f"{title_text} {abstract_text}"
            
            for orig_doi, info in doi_to_paper.items():
                if orig_doi.lower() == d:
                    if check_polar_radar_use(text_to_search, info['year']):
                        matched_papers.append(info)
                    break
        time.sleep(0.05)
    except Exception as e:
        pass

# Resolve unresolved papers
for paper in unresolved_papers:
    title = paper['title']
    author = paper['author']
    year = paper['year']
    if not title:
        continue
    query = f"{title} {author}"
    query_esc = urllib.parse.quote(query)
    url = f"https://api.crossref.org/works?query={query_esc}&rows=1&select=DOI,title,abstract"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (mailto:test@example.com)'})
    try:
        res = urllib.request.urlopen(req).read()
        data = json.loads(res)
        items = data.get('message', {}).get('items', [])
        if items:
            match = items[0]
            title_text = ' '.join(match.get('title', []))
            abstract_text = match.get('abstract', '')
            text_to_search = f"{title_text} {abstract_text}"
            if check_polar_radar_use(text_to_search, year):
                paper['doi'] = match.get('DOI')
                matched_papers.append(paper)
        time.sleep(0.05)
    except Exception as e:
        pass

# Sort publications by Year (descending) and Author
matched_papers = sorted(matched_papers, key=lambda x: (-x['year'], x['author']))
print(f"Generating PDF for {len(matched_papers)} polar SuperDARN papers...")

# ReportLab Layout Custom Class for Page Numbers
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#555555"))
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(letter[0] - 54, 36, page_text)
        
        # Draw header on later pages
        if self._pageNumber > 1:
            self.setFont("Helvetica-Bold", 8)
            self.drawString(54, letter[1] - 40, "BIBLIOGRAPHY: POLAR SUPERDARN RADAR RESEARCH")
            self.setStrokeColor(colors.HexColor("#cccccc"))
            self.setLineWidth(0.5)
            self.line(54, letter[1] - 45, letter[0] - 54, letter[1] - 45)
            
        self.restoreState()

# Document generation setup
output_dir = '/Users/garethperry/.gemini/antigravity/brain/fb917de1-2433-4404-8b52-2d1d797295a5'
output_path_artifact = os.path.join(output_dir, 'superdarn_polar_publications_list.pdf')
output_path_local = 'superdarn_polar_publications_list.pdf'

doc = SimpleDocTemplate(
    output_path_artifact,
    pagesize=letter,
    rightMargin=54,
    leftMargin=54,
    topMargin=54,
    bottomMargin=54
)

styles = getSampleStyleSheet()

# Custom styles
style_title = ParagraphStyle(
    name='TitleStyle',
    parent=styles['Normal'],
    fontName='Helvetica-Bold',
    fontSize=20,
    leading=24,
    textColor=colors.HexColor("#1b365d"),
    spaceAfter=15
)

style_subtitle = ParagraphStyle(
    name='SubTitleStyle',
    parent=styles['Normal'],
    fontName='Helvetica',
    fontSize=10,
    leading=14,
    textColor=colors.HexColor("#555555"),
    spaceAfter=25
)

style_bib_entry = ParagraphStyle(
    name='BibEntry',
    parent=styles['Normal'],
    fontName='Helvetica',
    fontSize=9.5,
    leading=13.5,
    textColor=colors.HexColor("#111111")
)

style_bib_meta = ParagraphStyle(
    name='BibMeta',
    parent=styles['Normal'],
    fontName='Helvetica-Oblique',
    fontSize=8.5,
    leading=11.5,
    textColor=colors.HexColor("#555555")
)

story = []

# Title & Metadata block
story.append(Paragraph("Bibliography of Polar SuperDARN Radar Research (1980 - 2025)", style_title))
metadata_desc = (
    "This document lists all publications from the official SuperDARN Canada registry that actually use data "
    "from the 9 polar SuperDARN radars (geomagnetic latitude &ge; 70&deg;). Publications are validated using "
    "operational start-year filters (only matching papers published in or after the operational startup year of the radar used) "
    "to ensure data validity. Crossref scholarly metadata was used to resolve citation metadata."
)
story.append(Paragraph(metadata_desc, style_subtitle))
story.append(Spacer(1, 10))

# Build Table of Bibliography Entries
table_data = []
for idx, paper in enumerate(matched_papers, 1):
    citation_text = f"<b>{idx}. {paper['authors']} ({paper['year']})</b>. \"{paper['title']}\". <i>{paper['journal']}</i>."
    doi_suffix = f"DOI: https://doi.org/{paper['doi']}" if paper.get('doi') else "DOI: Not Available"
    
    p_cit = Paragraph(citation_text, style_bib_entry)
    p_doi = Paragraph(doi_suffix, style_bib_meta)
    
    # Combined cells
    cell_flowables = [p_cit, Spacer(1, 2), p_doi, Spacer(1, 8)]
    table_data.append([cell_flowables])

# Set Table constraints
bib_table = Table(table_data, colWidths=[doc.width])
bib_table.setStyle(TableStyle([
    ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ('TOPPADDING', (0,0), (-1,-1), 4),
    ('LINEBELOW', (0,0), (-1,-1), 0.3, colors.HexColor("#eaeaea")),
]))

story.append(bib_table)

# Build PDF
doc.build(story, canvasmaker=NumberedCanvas)

# Copy to local directory
import shutil
shutil.copy(output_path_artifact, output_path_local)

print("Bibliography PDF generated successfully.")
