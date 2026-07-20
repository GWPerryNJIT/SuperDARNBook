import os
import urllib.request
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

# 1. Fetch official publications from SuperDARN Canada CSV database
print("Fetching official publications from SuperDARN Canada...")
url_csv = 'https://sdc-serv.usask.ca/website_updating_tools/publication_reports/articles_2SWA2C.csv'
req_csv = urllib.request.Request(url_csv, headers={'User-Agent': 'Mozilla/5.0'})

publications_by_year = defaultdict(int)
polar_publications_by_year = defaultdict(int)
doi_to_year = {}
doi_to_is_polar = {}
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
                
                # Check for "polar" in title
                is_polar = bool(re.search(r'\bpolar\b', title, re.IGNORECASE))
                if is_polar:
                    polar_publications_by_year[year] += 1
                
                if doi and doi.startswith('10.'):
                    doi_to_year[doi] = year
                    doi_to_is_polar[doi] = is_polar
                else:
                    unresolved_papers.append({'title': title, 'author': author, 'year': year, 'is_polar': is_polar})
        except (ValueError, IndexError):
            continue
    print(f"Parsed {total_official_papers} papers. Has DOI: {len(doi_to_year)}, Needs Resolution: {len(unresolved_papers)}")
except Exception as e:
    print(f"Error fetching SuperDARN Canada CSV: {e}")
    # Exit if CSV is not fetchable
    exit(1)

# 2. Query citations for valid DOIs from Crossref API in batches
print("Fetching citation counts for papers with DOIs from Crossref API...")
citations_by_year = defaultdict(int)
polar_citations_by_year = defaultdict(int)
dois = list(doi_to_year.keys())
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
                    c = item.get('is-referenced-by-count', 0)
                    citations_by_year[y] += c
                    if doi_to_is_polar.get(orig_doi):
                        polar_citations_by_year[y] += c
                    break
        time.sleep(0.05)
    except Exception as e:
        print(f"Error fetching batch {i}: {e}")

# 3. Resolve unresolved papers using Bibliographical Search on Crossref
print("Resolving papers missing DOIs using bibliographic search on Crossref...")
for paper in unresolved_papers:
    title = paper['title']
    author = paper['author']
    year = paper['year']
    is_polar = paper['is_polar']
    if not title:
        continue
        
    query = f"{title} {author}"
    query_esc = urllib.parse.quote(query)
    url = f"https://api.crossref.org/works?query={query_esc}&rows=1&select=DOI,is-referenced-by-count"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (mailto:test@example.com)'})
    try:
        res = urllib.request.urlopen(req).read()
        data = json.loads(res)
        items = data.get('message', {}).get('items', [])
        if items:
            c = items[0].get('is-referenced-by-count', 0)
            citations_by_year[year] += c
            if is_polar:
                polar_citations_by_year[year] += c
        time.sleep(0.05)
    except Exception as e:
        pass

# Fill in arrays from 1980 to 2025
years = np.arange(1980, 2026)
annual_pubs_total = np.array([publications_by_year.get(y, 0) for y in years])
annual_pubs_polar = np.array([polar_publications_by_year.get(y, 0) for y in years])

citations_total = np.array([citations_by_year.get(y, 0) for y in years])
citations_polar = np.array([polar_citations_by_year.get(y, 0) for y in years])

cum_citations_total = np.cumsum(citations_total)
cum_citations_polar = np.cumsum(citations_polar)

# 4. Design the Plot
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
fig, ax1 = plt.subplots(figsize=(18, 12), dpi=300)

fig.patch.set_facecolor('#ffffff')
ax1.set_facecolor('#ffffff')

# Left Y-axis (Annual Publications - Stacked/Overlayed Bars)
color_total_bar = '#cccccc'
color_polar_bar = '#1f77b4'

# Plot total publications first (light gray)
bars_total = ax1.bar(years, annual_pubs_total, color=color_total_bar, alpha=0.5, edgecolor='#aaaaaa', 
                     linewidth=0.8, label='Total Annual Publications', zorder=3)
# Overlay polar publications (blue)
bars_polar = ax1.bar(years, annual_pubs_polar, color=color_polar_bar, alpha=0.8, edgecolor='#333333', 
                     linewidth=0.8, label="Publications with 'polar' in Title", zorder=4)

# Right Y-axis (Cumulative Citations)
ax2 = ax1.twinx()
color_total_line = '#e377c2'
color_polar_line = '#9467bd'  # Sleek purple

line_total = ax2.plot(years, cum_citations_total, color=color_total_line, linewidth=2.5, linestyle='--',
                      marker='o', markersize=6, label='Total Cumulative Citations', zorder=5)
line_polar = ax2.plot(years, cum_citations_polar, color=color_polar_line, linewidth=3.5,
                      marker='s', markersize=7, label="Cumulative Citations ('polar' papers)", zorder=6)

# Gridlines configuration
ax1.grid(True, which='major', linestyle='--', color='#dcdcdc', alpha=0.7, zorder=1)
ax1.grid(True, which='minor', linestyle=':', color='#f0f0f0', alpha=0.5, zorder=1)
ax2.grid(False)

# Title and Labels
ax1.set_title("SuperDARN Publications & Citations: Impact of 'Polar'-Titled Research (1980 - 2025)", 
             fontsize=24, pad=35, color='#111111', fontweight='bold')
ax1.set_xlabel('Year', fontsize=20, labelpad=20, color='#333333')
ax1.set_ylabel('Annual Publications (Bars)', fontsize=20, labelpad=20, color='#333333', fontweight='bold')
ax2.set_ylabel('Cumulative Citations (Lines)', fontsize=20, labelpad=20, color='#111111', fontweight='bold')

# Formatting Spines
for ax in [ax1, ax2]:
    for spine in ax.spines.values():
        spine.set_color('#cccccc')
        spine.set_visible(True)

# Ticks configuration (Major every 5 years, minor every 1 year)
ax1.set_xlim(1978, 2027)
ax1.xaxis.set_major_locator(ticker.MultipleLocator(5))
ax1.xaxis.set_minor_locator(ticker.MultipleLocator(1))

# Set tick parameters with large fonts
ax1.tick_params(axis='x', which='major', length=10, width=1.5, color='#888888', labelcolor='#333333', labelsize=16)
ax1.tick_params(axis='x', which='minor', length=5, width=1.0, color='#bbbbbb')

ax1.tick_params(axis='y', which='major', length=8, width=1.2, color='#333333', labelcolor='#333333', labelsize=16)
ax2.tick_params(axis='y', which='major', length=8, width=1.2, color='#333333', labelcolor='#333333', labelsize=16)

# Set Y-axis tick intervals
ax1.yaxis.set_major_locator(ticker.MultipleLocator(10))
ax2.yaxis.set_major_locator(ticker.MultipleLocator(2000))

# Add a text label explaining the citation history and sources
ax1.text(1980, 50, "*Publications: SuperDARN Canada Registry\n*Citations: Crossref scholarly metadata index\n*Filters: Case-insensitive regex match '\\bpolar\\b'", 
         fontsize=14, color='#666666', fontstyle='italic', bbox=dict(boxstyle="round,pad=0.3", fc='#ffffff', ec='#dcdcdc', alpha=0.8))

# Add Legend combining both plots
lines = [bars_total, bars_polar] + line_total + line_polar
labels_legend = [l.get_label() for l in lines]
legend = ax1.legend(lines, labels_legend, loc='upper left', 
                    frameon=True, fontsize=18, facecolor='#ffffff', edgecolor='#cccccc')

# Save paths (Saves both PDF and PNG)
output_dir = '/Users/garethperry/.gemini/antigravity/brain/fb917de1-2433-4404-8b52-2d1d797295a5'
os.makedirs(output_dir, exist_ok=True)

output_path_artifact_pdf = os.path.join(output_dir, 'superdarn_publications_polar.pdf')
output_path_artifact_png = os.path.join(output_dir, 'superdarn_publications_polar.png')
output_path_local_pdf = 'superdarn_publications_polar.pdf'
output_path_local_png = 'superdarn_publications_polar.png'

plt.tight_layout()
plt.savefig(output_path_artifact_pdf, facecolor='#ffffff', edgecolor='none')
plt.savefig(output_path_artifact_png, facecolor='#ffffff', edgecolor='none', dpi=300)
plt.savefig(output_path_local_pdf, facecolor='#ffffff', edgecolor='none')
plt.savefig(output_path_local_png, facecolor='#ffffff', edgecolor='none', dpi=300)

print("Successfully generated and saved publication & citation plots.")
print(f"Total cumulative citations for Polar papers by 2025: {cum_citations_polar[-1]} of {cum_citations_total[-1]}")
