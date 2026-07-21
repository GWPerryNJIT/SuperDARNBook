import os
import urllib.request
import urllib.error
import json
import csv
import io
import urllib.parse
import re
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import time
from collections import defaultdict

# Helper function with exponential backoff for rate-limited requests
def fetch_with_retry(url, headers, max_retries=5):
    delay = 1.0
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as response:
                return response.read()
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f"Rate limited (429). Retrying in {delay:.1f} seconds...")
                time.sleep(delay)
                delay *= 2
            else:
                raise e
    raise Exception("Max retries exceeded for rate-limiting (429)")

# 1. Fetch official publications from SuperDARN Canada CSV database
print("Fetching official publications from SuperDARN Canada...")
url_csv = 'https://sdc-serv.usask.ca/website_updating_tools/publication_reports/articles_2SWA2C.csv'
req_csv = urllib.request.Request(url_csv, headers={'User-Agent': 'Mozilla/5.0'})

publications_by_year = defaultdict(int)
polar_radar_publications_by_year = defaultdict(int)
doi_to_year = {}
unresolved_papers = []
total_official_papers = 0

try:
    res_csv = urllib.request.urlopen(req_csv).read().decode('utf-8')
    reader = csv.DictReader(io.StringIO(res_csv))
    for row in reader:
        doi = row.get('DOI', '').strip()
        date_str = row.get('Publication Date')
        title = row.get('Title', '').strip()
        author = row.get('First Author', '').strip()
        if not date_str:
            continue
        try:
            year = int(date_str.split('-')[0])
            if 1980 <= year <= 2025:
                publications_by_year[year] += 1
                total_official_papers += 1
                if doi and doi.startswith('10.'):
                    doi_to_year[doi] = year
                else:
                    unresolved_papers.append({'title': title, 'author': author, 'year': year})
        except (ValueError, IndexError):
            continue
    print(f"Parsed {total_official_papers} papers. Has DOI: {len(doi_to_year)}, Needs Resolution: {len(unresolved_papers)}")
except Exception as e:
    print(f"Error fetching SuperDARN Canada CSV: {e}")
    exit(1)

# Define polar radars and their operational start years
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

citations_by_year = defaultdict(int)
polar_citations_by_year = defaultdict(int)

# 2. Query citations & metadata for valid DOIs from Crossref API in batches
print("Fetching metadata and citations for papers with DOIs from Crossref...")
dois = list(doi_to_year.keys())
batch_size = 50

for i in range(0, len(dois), batch_size):
    batch = dois[i:i+batch_size]
    clean_batch = [d for d in batch if all(ord(c) < 128 and not c.isspace() for c in d)]
    if not clean_batch:
        continue
    filter_str = ','.join([f'doi:{d}' for d in clean_batch])
    filter_str_esc = urllib.parse.quote(filter_str, safe=':,')
    url = f'https://api.crossref.org/works?filter={filter_str_esc}&rows=50&select=DOI,title,abstract,is-referenced-by-count'
    headers = {'User-Agent': 'Mozilla/5.0 (mailto:test@example.com)'}
    try:
        res = fetch_with_retry(url, headers)
        data = json.loads(res)
        for item in data.get('message', {}).get('items', []):
            d = item.get('DOI', '').lower()
            
            # Match metadata to verify polar radar use
            title_text = ' '.join(item.get('title', []))
            abstract_text = item.get('abstract', '')
            text_to_search = f"{title_text} {abstract_text}"
            
            for orig_doi, y in doi_to_year.items():
                if orig_doi.lower() == d:
                    c = item.get('is-referenced-by-count', 0)
                    citations_by_year[y] += c
                    is_polar_radar = check_polar_radar_use(text_to_search, y)
                    if is_polar_radar:
                        polar_radar_publications_by_year[y] += 1
                        polar_citations_by_year[y] += c
                    break
        time.sleep(0.1)
    except Exception as e:
        print(f"Error fetching batch {i}: {e}")

# 3. Resolve unresolved papers using Bibliographical Search on Crossref
print("Resolving papers missing DOIs using bibliographic search on Crossref...")
for paper in unresolved_papers:
    title = paper['title']
    author = paper['author']
    year = paper['year']
    if not title:
        continue
        
    query = f"{title} {author}"
    query_esc = urllib.parse.quote(query)
    url = f"https://api.crossref.org/works?query={query_esc}&rows=1&select=DOI,title,abstract,is-referenced-by-count"
    headers = {'User-Agent': 'Mozilla/5.0 (mailto:test@example.com)'}
    try:
        res = fetch_with_retry(url, headers)
        data = json.loads(res)
        items = data.get('message', {}).get('items', [])
        if items:
            match = items[0]
            title_text = ' '.join(match.get('title', []))
            abstract_text = match.get('abstract', '')
            text_to_search = f"{title_text} {abstract_text}"
            is_polar_radar = check_polar_radar_use(text_to_search, year)
            
            c = match.get('is-referenced-by-count', 0)
            citations_by_year[year] += c
            if is_polar_radar:
                polar_radar_publications_by_year[year] += 1
                polar_citations_by_year[year] += c
        time.sleep(0.1)
    except Exception as e:
        pass

# Fill in arrays from 1980 to 2025
years = np.arange(1980, 2026)
annual_pubs_total = np.array([publications_by_year.get(y, 0) for y in years])
annual_pubs_polar = np.array([polar_radar_publications_by_year.get(y, 0) for y in years])

citations_total = np.array([citations_by_year.get(y, 0) for y in years])
citations_polar = np.array([polar_citations_by_year.get(y, 0) for y in years])

cum_citations_total = np.cumsum(citations_total)
cum_citations_polar = np.cumsum(citations_polar)

# 4. Design the Plot (Dual Axis, White Theme, Large Fonts)
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
fig, ax1 = plt.subplots(figsize=(20, 14), dpi=300)

fig.patch.set_facecolor('#ffffff')
ax1.set_facecolor('#ffffff')

# Left Y-axis (Annual Publications - Overlayed Bars)
color_total_bar = '#cccccc'
color_polar_bar = '#1f77b4'

# Plot total publications first (light gray)
bars_total = ax1.bar(years, annual_pubs_total, color=color_total_bar, alpha=0.5, edgecolor='#aaaaaa', 
                     linewidth=0.8, label='Total Annual Publications', zorder=3)
# Overlay polar-radar publications (blue)
bars_polar = ax1.bar(years, annual_pubs_polar, color=color_polar_bar, alpha=0.8, edgecolor='#333333', 
                     linewidth=0.8, label="Publications Using Polar Radars (\u226570\u00b0 MLAT)", zorder=4)

# Right Y-axis (Cumulative Citations)
ax2 = ax1.twinx()
color_total_line = '#e377c2'
color_polar_line = '#9467bd'

# Mask to eliminate citation curves when value is 0
mask_total = cum_citations_total > 0
years_tot = years[mask_total]
cum_citations_total_plot = cum_citations_total[mask_total]

mask_polar = cum_citations_polar > 0
years_pol = years[mask_polar]
cum_citations_polar_plot = cum_citations_polar[mask_polar]

if len(cum_citations_total_plot) > 0:
    line_total = ax2.plot(years_tot, cum_citations_total_plot, color=color_total_line, linewidth=2.5, linestyle='--',
                          marker='o', markersize=6, label='Total Cumulative Citations', zorder=5)

if len(cum_citations_polar_plot) > 0:
    line_polar = ax2.plot(years_pol, cum_citations_polar_plot, color=color_polar_line, linewidth=3.5,
                          marker='s', markersize=7, label="Cumulative Citations (Polar-radar papers)", zorder=6)

# Gridlines
ax1.grid(True, which='major', linestyle='--', color='#dcdcdc', alpha=0.7, zorder=1)
ax1.grid(True, which='minor', linestyle=':', color='#f0f0f0', alpha=0.5, zorder=1)
ax2.grid(False)

# Title and Labels (Massive Font Sizes)
ax1.set_title("SuperDARN publications: Impact of polar radar research (\u226570\u00b0 MLAT) (1980 - 2025)", 
             fontsize=30, pad=35, color='#111111', fontweight='bold')
ax1.set_xlabel('Year', fontsize=24, labelpad=25, color='#333333')
ax1.set_ylabel('Annual Publications (Bars)', fontsize=24, labelpad=25, color='#333333')
ax2.set_ylabel('Cumulative Citations (Lines)', fontsize=24, labelpad=25, color='#111111')

# Formatting Spines
for ax in [ax1, ax2]:
    for spine in ax.spines.values():
        spine.set_color('#cccccc')
        spine.set_visible(True)

# Ticks
ax1.set_xlim(1978, 2027)
ax1.xaxis.set_major_locator(ticker.MultipleLocator(5))
ax1.xaxis.set_minor_locator(ticker.MultipleLocator(1))

ax1.tick_params(axis='x', which='major', length=10, width=1.5, color='#888888', labelcolor='#333333', labelsize=20)
ax1.tick_params(axis='x', which='minor', length=5, width=1.0, color='#bbbbbb')
ax1.tick_params(axis='y', which='major', length=8, width=1.2, color='#333333', labelcolor='#333333', labelsize=20)
ax2.tick_params(axis='y', which='major', length=8, width=1.2, color='#333333', labelcolor='#333333', labelsize=20)

ax1.yaxis.set_major_locator(ticker.MultipleLocator(10))
ax2.yaxis.set_major_locator(ticker.MultipleLocator(2000))

# Add Legend
lines = [bars_total, bars_polar]
if len(cum_citations_total_plot) > 0:
    lines += line_total
if len(cum_citations_polar_plot) > 0:
    lines += line_polar
    
labels_legend = [l.get_label() for l in lines]
legend = ax1.legend(lines, labels_legend, loc='upper left', 
                    frameon=True, fontsize=22, facecolor='#ffffff', edgecolor='#cccccc')

# Save paths
output_dir = '/Users/garethperry/.gemini/antigravity/brain/fb917de1-2433-4404-8b52-2d1d797295a5'
os.makedirs(output_dir, exist_ok=True)

output_path_artifact_pdf = os.path.join(output_dir, 'superdarn_publications_polar_radars.pdf')
output_path_artifact_png = os.path.join(output_dir, 'superdarn_publications_polar_radars.png')
output_path_local_pdf = 'superdarn_publications_polar_radars.pdf'
output_path_local_png = 'superdarn_publications_polar_radars.png'

plt.tight_layout()
plt.savefig(output_path_artifact_pdf, facecolor='#ffffff', edgecolor='none')
plt.savefig(output_path_artifact_png, facecolor='#ffffff', edgecolor='none', dpi=300)
plt.savefig(output_path_local_pdf, facecolor='#ffffff', edgecolor='none')
plt.savefig(output_path_local_png, facecolor='#ffffff', edgecolor='none', dpi=300)

print("Successfully generated and saved publication & citation plots.")
print(f"Total cumulative citations for Polar Radar papers by 2025: {cum_citations_polar[-1]} of {cum_citations_total[-1]}")
