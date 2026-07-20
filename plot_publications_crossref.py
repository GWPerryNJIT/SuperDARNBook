import os
import urllib.request
import json
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import time
from collections import defaultdict

# 1. Query Crossref API directly for all works matching "SuperDARN"
print("Querying Crossref API for all works matching 'SuperDARN'...")
publications_by_year = defaultdict(int)
citations_by_year = defaultdict(int)

# Use cursor pagination to download all results (typically ~414 total results)
cursor = '*'
total_fetched = 0

while True:
    cursor_esc = urllib.parse.quote(cursor)
    url = f'https://api.crossref.org/works?query=SuperDARN&rows=100&select=DOI,published,is-referenced-by-count&cursor={cursor_esc}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (mailto:test@example.com)'})
    try:
        res = urllib.request.urlopen(req).read()
        data = json.loads(res)
        items = data.get('message', {}).get('items', [])
        if not items:
            break
            
        total_fetched += len(items)
        for item in items:
            pub = item.get('published')
            year = None
            if pub and 'date-parts' in pub and pub['date-parts']:
                try:
                    year = int(pub['date-parts'][0][0])
                except:
                    continue
            if year and 1980 <= year <= 2025:
                publications_by_year[year] += 1
                citations_by_year[year] += item.get('is-referenced-by-count', 0)
                
        next_cursor = data.get('message', {}).get('next-cursor')
        if not next_cursor or len(items) < 100:
            break
        cursor = next_cursor
        time.sleep(0.1)  # Polite sleep
    except Exception as e:
        print(f"Error querying Crossref: {e}")
        break

print(f"Fetched {total_fetched} records from Crossref.")

# Fill in arrays from 1980 to 2025
years = np.arange(1980, 2026)
annual_pubs = np.array([publications_by_year.get(y, 0) for y in years])
annual_citations = np.array([citations_by_year.get(y, 0) for y in years])
cumulative_citations = np.cumsum(annual_citations)

# 2. Design the Plot (Dual Axis, White Theme, Large Fonts)
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
fig, ax1 = plt.subplots(figsize=(18, 12), dpi=300)

fig.patch.set_facecolor('#ffffff')
ax1.set_facecolor('#ffffff')

# Left Y-axis (Annual Publications - Bar Chart)
color_pubs = '#1f77b4'
bars = ax1.bar(years, annual_pubs, color=color_pubs, alpha=0.8, edgecolor='#333333', 
               linewidth=0.8, label='Annual Publications (Crossref Query)', zorder=3)

# Right Y-axis (Cumulative Citations - Line Chart)
ax2 = ax1.twinx()
color_citations = '#e377c2'
line = ax2.plot(years, cumulative_citations, color=color_citations, linewidth=3.5, 
                marker='o', markersize=8, label='Cumulative Citations (Crossref)', zorder=4)

# Gridlines configuration
ax1.grid(True, which='major', linestyle='--', color='#dcdcdc', alpha=0.7, zorder=1)
ax1.grid(True, which='minor', linestyle=':', color='#f0f0f0', alpha=0.5, zorder=1)
ax2.grid(False)

# Title and Labels
ax1.set_title('SuperDARN Publications and Cumulative Citations (Crossref Only, 1980 - 2025)', 
             fontsize=26, pad=35, color='#111111', fontweight='bold')
ax1.set_xlabel('Year', fontsize=20, labelpad=20, color='#333333')
ax1.set_ylabel('Annual Publications (Bars)', fontsize=20, labelpad=20, color=color_pubs, fontweight='bold')
ax2.set_ylabel('Cumulative Citations of Published Papers (Line)', fontsize=20, labelpad=20, color=color_citations, fontweight='bold')

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

ax1.tick_params(axis='y', which='major', length=8, width=1.2, color=color_pubs, labelcolor=color_pubs, labelsize=16)
ax2.tick_params(axis='y', which='major', length=8, width=1.2, color=color_citations, labelcolor=color_citations, labelsize=16)

# Set Y-axis tick intervals
ax1.yaxis.set_major_locator(ticker.MultipleLocator(5))
ax2.yaxis.set_major_locator(ticker.MultipleLocator(1000))

# Add a text label explaining the citation history and sources
ax1.text(1980, 20, "*Restricted to Crossref index query 'SuperDARN'\n*Plotted by publication year cohort\n*Total citations based on current Crossref counts", 
         fontsize=14, color='#666666', fontstyle='italic', bbox=dict(boxstyle="round,pad=0.3", fc='#ffffff', ec='#dcdcdc', alpha=0.8))

# Add Legend combining both plots
lines, labels_legend = ax1.get_legend_handles_labels()
lines2, labels_legend2 = ax2.get_legend_handles_labels()
legend = ax1.legend(lines + lines2, labels_legend + labels_legend2, loc='upper left', 
                    frameon=True, fontsize=18, facecolor='#ffffff', edgecolor='#cccccc')

# Save paths (Saves both PDF and PNG)
output_dir = '/Users/garethperry/.gemini/antigravity/brain/fb917de1-2433-4404-8b52-2d1d797295a5'
os.makedirs(output_dir, exist_ok=True)

output_path_artifact_pdf = os.path.join(output_dir, 'superdarn_publications_crossref.pdf')
output_path_artifact_png = os.path.join(output_dir, 'superdarn_publications_crossref.png')
output_path_local_pdf = 'superdarn_publications_crossref.pdf'
output_path_local_png = 'superdarn_publications_crossref.png'

plt.tight_layout()
plt.savefig(output_path_artifact_pdf, facecolor='#ffffff', edgecolor='none')
plt.savefig(output_path_artifact_png, facecolor='#ffffff', edgecolor='none', dpi=300)
plt.savefig(output_path_local_pdf, facecolor='#ffffff', edgecolor='none')
plt.savefig(output_path_local_png, facecolor='#ffffff', edgecolor='none', dpi=300)

print("Successfully generated and saved publication & citation plots.")
print(f"Total cumulative citations by 2025: {cumulative_citations[-1]}")
