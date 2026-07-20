import os
import urllib.request
import json
import csv
import io
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import time
from collections import defaultdict

# 1. Fetch official publications from SuperDARN Canada CSV database
print("Fetching official publications from SuperDARN Canada...")
url_csv = 'https://sdc-serv.usask.ca/website_updating_tools/publication_reports/articles_2SWA2C.csv'
req_csv = urllib.request.Request(url_csv, headers={'User-Agent': 'Mozilla/5.0'})

publications_by_year = defaultdict(int)
doi_to_year = {}
total_official_papers = 0

try:
    res_csv = urllib.request.urlopen(req_csv).read().decode('utf-8')
    reader = csv.DictReader(io.StringIO(res_csv))
    for row in reader:
        doi = row.get('DOI', '').strip()
        date_str = row.get('Publication Date')
        if not date_str:
            continue
        try:
            year = int(date_str.split('-')[0])
            if 1980 <= year <= 2025:
                publications_by_year[year] += 1
                total_official_papers += 1
                if doi and doi.startswith('10.'):
                    doi_to_year[doi] = year
        except (ValueError, IndexError):
            continue
    print(f"Parsed {total_official_papers} papers. Valid DOIs: {len(doi_to_year)}")
except Exception as e:
    print(f"Error fetching SuperDARN Canada CSV: {e}")
    # Pre-populated fallback if CSV fetch fails
    publications_by_year = {
        1995: 8, 1996: 5, 1997: 17, 1998: 34, 1999: 30, 2000: 41, 2001: 44, 2002: 55, 2003: 41,
        2004: 42, 2005: 43, 2006: 36, 2007: 34, 2008: 53, 2009: 49, 2010: 44, 2011: 40, 2012: 44,
        2013: 44, 2014: 46, 2015: 60, 2016: 48, 2017: 39, 2018: 52, 2019: 35, 2020: 50, 2021: 65,
        2022: 64, 2023: 37, 2024: 54, 2025: 49
    }
    total_official_papers = sum(publications_by_year.values())

dois = list(doi_to_year.keys())

# 2. Query Crossref API
print("Fetching citation counts from Crossref API...")
crossref_citations = defaultdict(int)
batch_size = 50
for i in range(0, len(dois), batch_size):
    batch = dois[i:i+batch_size]
    clean_batch = [d for d in batch if all(ord(c) < 128 and not c.isspace() for c in d)]
    if not clean_batch:
        continue
    filter_str = ','.join([f'doi:{d}' for d in clean_batch])
    filter_str_esc = urllib.parse.quote(filter_str, safe=':,')
    url = f'https://api.crossref.org/works?filter={filter_str_esc}&rows=50&select=DOI,is-referenced-by-count'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (mailto:test@example.com)'})
    try:
        res = urllib.request.urlopen(req).read()
        data = json.loads(res)
        for item in data.get('message', {}).get('items', []):
            d = item.get('DOI', '').lower()
            for orig_doi, y in doi_to_year.items():
                if orig_doi.lower() == d:
                    crossref_citations[y] += item.get('is-referenced-by-count', 0)
                    break
        time.sleep(0.1)
    except Exception as e:
        print(f"Error fetching Crossref batch {i}: {e}")

# 3. Query OpenAlex API
print("Fetching citation counts from OpenAlex API...")
openalex_citations = defaultdict(int)
for i in range(0, len(dois), batch_size):
    batch = dois[i:i+batch_size]
    clean_batch = [d for d in batch if all(ord(c) < 128 and not c.isspace() for c in d)]
    if not clean_batch:
        continue
    filter_str = '|'.join([f'https://doi.org/{d}' for d in clean_batch])
    filter_str_esc = urllib.parse.quote(filter_str, safe=':|')
    url = f'https://api.openalex.org/works?filter=doi:{filter_str_esc}&select=doi,cited_by_count&per_page=50'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (mailto:test@example.com)'})
    try:
        res = urllib.request.urlopen(req).read()
        data = json.loads(res)
        for r in data.get('results', []):
            d = r.get('doi', '').replace('https://doi.org/', '').lower()
            for orig_doi, y in doi_to_year.items():
                if orig_doi.lower() == d:
                    openalex_citations[y] += r.get('cited_by_count', 0)
                    break
        time.sleep(0.1)
    except Exception as e:
        print(f"Error fetching OpenAlex batch {i}: {e}")

# 4. Query Semantic Scholar API (supports POST batch query up to 1000 items)
print("Fetching citation counts from Semantic Scholar API...")
semschol_citations = defaultdict(int)
try:
    url_ss = 'https://api.semanticscholar.org/graph/v1/paper/batch?fields=citationCount,externalIds'
    # Query in batches of 500
    batch_size_ss = 500
    for i in range(0, len(dois), batch_size_ss):
        batch = dois[i:i+batch_size_ss]
        data_post = {'ids': batch}
        req_ss = urllib.request.Request(
            url_ss,
            data=json.dumps(data_post).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
        )
        res_ss = urllib.request.urlopen(req_ss).read()
        results = json.loads(res_ss)
        for r in results:
            if not r:
                continue
            d = r.get('externalIds', {}).get('DOI', '').lower()
            if d:
                for orig_doi, y in doi_to_year.items():
                    if orig_doi.lower() == d:
                        semschol_citations[y] += r.get('citationCount', 0)
                        break
        time.sleep(0.2)
except Exception as e:
    print(f"Error fetching Semantic Scholar: {e}")

# Process datasets for plotting
years = np.arange(1980, 2026)
annual_pubs = np.array([publications_by_year.get(y, 0) for y in years])

cr_cum = np.cumsum([crossref_citations.get(y, 0) for y in years])
oa_cum = np.cumsum([openalex_citations.get(y, 0) for y in years])
ss_cum = np.cumsum([semschol_citations.get(y, 0) for y in years])

# 5. Design the Plot
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
fig, ax1 = plt.subplots(figsize=(18, 12), dpi=300)

fig.patch.set_facecolor('#ffffff')
ax1.set_facecolor('#ffffff')

# Left Axis: Annual Publications
color_pubs = '#7f7f7f' # Muted grey for bars to let citations shine
bars = ax1.bar(years, annual_pubs, color=color_pubs, alpha=0.5, edgecolor='#333333', 
               linewidth=0.8, label='Annual Publications (Registry)', zorder=3)

# Right Axis: Citations
ax2 = ax1.twinx()
line_cr = ax2.plot(years, cr_cum, color='#e377c2', linewidth=3.0, marker='o', markersize=6, label='Crossref Citations', zorder=4)
line_oa = ax2.plot(years, oa_cum, color='#1f77b4', linewidth=3.0, marker='s', markersize=6, label='OpenAlex Citations', zorder=5)
line_ss = ax2.plot(years, ss_cum, color='#bcbd22', linewidth=3.0, marker='^', markersize=6, label='Semantic Scholar Citations', zorder=6)

ax1.grid(True, which='major', linestyle='--', color='#dcdcdc', alpha=0.7, zorder=1)
ax1.grid(True, which='minor', linestyle=':', color='#f0f0f0', alpha=0.5, zorder=1)
ax2.grid(False)

# Labels
ax1.set_title('SuperDARN Publications (Registry) and Citation Indexes Comparison (1980 - 2025)', 
             fontsize=24, pad=35, color='#111111', fontweight='bold')
ax1.set_xlabel('Year', fontsize=20, labelpad=20, color='#333333')
ax1.set_ylabel('Annual Publications (Bars)', fontsize=20, labelpad=20, color=color_pubs, fontweight='bold')
ax2.set_ylabel('Cumulative Citations (Lines)', fontsize=20, labelpad=20, color='#111111', fontweight='bold')

# Formatting spines
for ax in [ax1, ax2]:
    for spine in ax.spines.values():
        spine.set_color('#cccccc')
        spine.set_visible(True)

ax1.set_xlim(1978, 2027)
ax1.xaxis.set_major_locator(ticker.MultipleLocator(5))
ax1.xaxis.set_minor_locator(ticker.MultipleLocator(1))

ax1.tick_params(axis='x', which='major', length=10, width=1.5, color='#888888', labelcolor='#333333', labelsize=16)
ax1.tick_params(axis='x', which='minor', length=5, width=1.0, color='#bbbbbb')
ax1.tick_params(axis='y', which='major', length=8, width=1.2, color=color_pubs, labelcolor=color_pubs, labelsize=16)
ax2.tick_params(axis='y', which='major', length=8, width=1.2, color='#333333', labelcolor='#333333', labelsize=16)

ax1.yaxis.set_major_locator(ticker.MultipleLocator(10))
ax2.yaxis.set_major_locator(ticker.MultipleLocator(2000))

# Combined Legend
lines = [bars] + line_cr + line_oa + line_ss
labels_legend = [l.get_label() for l in lines]
legend = ax1.legend(lines, labels_legend, loc='upper left', frameon=True, fontsize=18, facecolor='#ffffff', edgecolor='#cccccc')

# Save paths
output_dir = '/Users/garethperry/.gemini/antigravity/brain/fb917de1-2433-4404-8b52-2d1d797295a5'
os.makedirs(output_dir, exist_ok=True)

output_path_artifact_pdf = os.path.join(output_dir, 'superdarn_publications_indexes_comparison.pdf')
output_path_artifact_png = os.path.join(output_dir, 'superdarn_publications_indexes_comparison.png')
output_path_local_pdf = 'superdarn_publications_indexes_comparison.pdf'
output_path_local_png = 'superdarn_publications_indexes_comparison.png'

plt.tight_layout()
plt.savefig(output_path_artifact_pdf, facecolor='#ffffff', edgecolor='none')
plt.savefig(output_path_artifact_png, facecolor='#ffffff', edgecolor='none', dpi=300)
plt.savefig(output_path_local_pdf, facecolor='#ffffff', edgecolor='none')
plt.savefig(output_path_local_png, facecolor='#ffffff', edgecolor='none', dpi=300)

print("Comparison plot compiled successfully.")
print(f"Final totals (2025): Crossref={cr_cum[-1]}, OpenAlex={oa_cum[-1]}, Semantic Scholar={ss_cum[-1]}")
