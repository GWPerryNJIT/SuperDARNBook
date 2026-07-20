import os
import pydarn.utils
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pandas as pd
import numpy as np
import aacgmv2
import datetime
import urllib.request
import re
from collections import Counter

# 1. Fetch official radar list from SuperDARN Canada website
print("Fetching official radar list from SuperDARN Canada...")
official_codes = set()
try:
    url = 'https://superdarn.ca/radar-info'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    html = urllib.request.urlopen(req).read().decode('utf-8')
    
    words = [w.upper() for w in re.findall(r'\b[a-zA-Z]{3}\b', html)]
    counts = Counter(words)
    
    exclude = {'ALT', 'AND', 'ARE', 'CAN', 'COL', 'COM', 'CSS', 'DIV', 'DOI', 'EDU', 'FOR', 
               'FOV', 'HDW', 'IMG', 'JPG', 'MET', 'MIN', 'NAV', 'ORG', 'PNG', 'REL', 'RES', 
               'ROW', 'SRC', 'SVG', 'THE', 'WWW'}
    
    for w, c in counts.items():
        if c == 9 and w not in exclude:
            official_codes.add(w)
            
    print(f"Found {len(official_codes)} official radar codes: {sorted(list(official_codes))}")
except Exception as e:
    print(f"Error fetching official radar list: {e}")
    print("Using a hardcoded list of verified official SuperDARN radars as a fallback.")
    official_codes = {
        'ADE', 'ADW', 'BKS', 'BPK', 'CLY', 'CVE', 'CVW', 'DCE', 'DCN', 'FHE', 'FHW', 'FIR', 
        'GBR', 'HAL', 'HAN', 'HJE', 'HJW', 'HKW', 'HOK', 'ICE', 'ICW', 'INV', 'JME', 'KAP', 
        'KER', 'KOD', 'KSR', 'LJE', 'LJW', 'LYR', 'MCM', 'PGR', 'PYK', 'RKN', 'SAN', 'SAS', 
        'SCH', 'SPS', 'STO', 'SYE', 'SYS', 'SZE', 'SZW', 'TIG', 'UNW', 'WAL', 'ZHO'
    }

# 2. Locate hardware directory and extract radar data
hdw_path = os.path.join(os.path.dirname(pydarn.utils.__file__), 'hdw')
radars_data = []

for fname in os.listdir(hdw_path):
    if fname.startswith('hdw.dat.'):
        abbr = fname.split('.')[-1].upper()
        
        if abbr not in official_codes:
            continue
            
        filepath = os.path.join(hdw_path, fname)
        try:
            with open(filepath, 'r') as f:
                lines = [l.strip() for l in f.readlines() if not l.startswith('#') and l.strip()]
            if not lines:
                continue
                
            # First record (Start)
            first_parts = lines[0].split()
            first_year = int(first_parts[2][:4])
            first_month = int(first_parts[2][4:6])
            first_day = int(first_parts[2][6:8])
            
            lat = float(first_parts[4])
            lon = float(first_parts[5])
            alt_km = float(first_parts[6]) / 1000.0
            
            # Convert to AACGM latitude using the start date of the radar
            dtime = datetime.datetime(first_year, first_month, first_day)
            try:
                mlat, _, _ = aacgmv2.convert_latlon(lat, lon, alt_km, dtime, 'G2A')
                abs_mlat = abs(mlat)
            except Exception as err:
                print(f"Error converting AACGM for {abbr}: {err}")
                abs_mlat = abs(lat)
            
            radars_data.append({
                'abbrev': abbr,
                'start_year': first_year,
                'lat_geo': lat,
                'lon_geo': lon,
                'lat_aacgm': mlat,
                'abs_lat_aacgm': abs_mlat,
                'hemisphere': 'Northern' if lat >= 0 else 'Southern'
            })
        except Exception as e:
            print(f'Error reading {fname}: {e}')

df = pd.DataFrame(radars_data)
# Sort to help with label placement
df = df.sort_values(by=['start_year', 'abs_lat_aacgm']).reset_index(drop=True)

# 3. Design the plot
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
fig, ax = plt.subplots(figsize=(20, 14), dpi=300)  # Slightly enlarged figure window to accommodate massive text

fig.patch.set_facecolor('#ffffff')
ax.set_facecolor('#ffffff')

# Colors
colors = {'Northern': '#1f77b4', 'Southern': '#e377c2'}

# Plot start points only
for hemi, color in colors.items():
    sub = df[df['hemisphere'] == hemi]
    ax.scatter(sub['start_year'], sub['abs_lat_aacgm'], c=color, label=f'{hemi} Hemisphere', 
               s=220, alpha=0.9, edgecolors='#333333', linewidths=0.8, zorder=3)

# 4. Force-Directed Label Placement Algorithm
# Anchor labels directly to the start year coordinates
x_anchors = df['start_year'].values.astype(float)
y_anchors = df['abs_lat_aacgm'].values
labels = df['abbrev'].values

N = len(df)
x_labels = x_anchors.copy()
y_labels = y_anchors + 4.5 + np.random.uniform(-0.5, 0.5, N)

# Expanded thresholds for separation to match 15pt text
W_thresh = 3.8
H_thresh = 6.2

iterations = 500
learning_rate = 0.12

for _ in range(iterations):
    dx_forces = np.zeros(N)
    dy_forces = np.zeros(N)
    
    # A. Repulsion between labels
    for i in range(N):
        for j in range(N):
            if i == j:
                continue
            dx = x_labels[i] - x_labels[j]
            dy = y_labels[i] - y_labels[j]
            
            rx = dx / W_thresh
            ry = dy / H_thresh
            dist = np.sqrt(rx**2 + ry**2)
            
            if dist < 1.0:
                if dist < 1e-3:
                    rx += np.random.uniform(-0.1, 0.1)
                    ry += np.random.uniform(-0.1, 0.1)
                    dist = np.sqrt(rx**2 + ry**2)
                
                force = (1.0 - dist) / dist
                dx_forces[i] += force * rx * W_thresh
                dy_forces[i] += force * ry * H_thresh
                
    # B. Repulsion from ALL anchor points (colored dots)
    for i in range(N):
        for j in range(N):
            dx = x_labels[i] - df.loc[j, 'start_year']
            dy = y_labels[i] - df.loc[j, 'abs_lat_aacgm']
            rx = dx / 1.5
            ry = dy / 3.2
            dist = np.sqrt(rx**2 + ry**2)
            
            min_dist = 1.3 if i == j else 1.0
            if dist < min_dist:
                force = (min_dist - dist) / (dist + 1e-3)
                dx_forces[i] += force * rx * 1.5
                dy_forces[i] += force * ry * 3.5

    # C. Attractive forces to own start_year anchor (spring)
    for i in range(N):
        ax_dist = x_labels[i] - x_anchors[i]
        ay_dist = y_labels[i] - y_anchors[i]
        
        dx_forces[i] -= 0.12 * ax_dist
        dy_forces[i] -= 0.12 * ay_dist

    # Apply updates
    x_labels += learning_rate * dx_forces
    y_labels += learning_rate * dy_forces
    y_labels = np.clip(y_labels, 31.5, 93.5)

# Annotate using calculated positions
for i in range(N):
    ax.annotate(
        labels[i],
        (x_anchors[i], y_anchors[i]),
        xytext=(x_labels[i], y_labels[i]),
        textcoords='data',
        ha='center',
        va='center',
        fontsize=15,  # Increased font size
        color='#111111',
        fontweight='bold',
        zorder=4,
        bbox=dict(boxstyle="round,pad=0.22", fc='#ffffff', ec='#b0b0b8', lw=0.6, alpha=0.9),
        arrowprops=dict(arrowstyle="-", color='#77777c', lw=0.8, alpha=0.6)
    )

# Formatting axes and gridlines
ax.grid(True, which='major', linestyle='--', color='#dcdcdc', alpha=0.7, zorder=1)
ax.grid(True, which='minor', linestyle=':', color='#f0f0f0', alpha=0.5, zorder=1)

ax.set_title('SuperDARN Radars: Absolute AACGM Latitude vs. Operational Start Year', 
             fontsize=30, pad=35, color='#111111', fontweight='bold')  # Increased title size
ax.set_xlabel('Start Year (Earliest Operational Record)', fontsize=24, labelpad=25, color='#333333')  # Increased label size
ax.set_ylabel('Absolute AACGM Latitude (|°|)', fontsize=24, labelpad=25, color='#333333')  # Increased label size

# Customizing spines and ticks
for spine in ax.spines.values():
    spine.set_color('#cccccc')
    spine.set_visible(True)

# Build legend (only hemispheres)
legend = ax.legend(frameon=True, loc='lower left', fontsize=22, facecolor='#ffffff', edgecolor='#cccccc')  # Increased legend size
for text in legend.get_texts():
    text.set_color('#111111')

# Adjust limits, major ticks, and minor ticks
ax.set_xlim(1978, 2027)
ax.set_ylim(30, 95)

# Major ticks
plt.xticks(np.arange(1980, 2026, 5), color='#333333', fontsize=20)  # Increased tick label size
plt.yticks(np.arange(30, 96, 10), color='#333333', fontsize=20)  # Increased tick label size

# Minor ticks
ax.xaxis.set_minor_locator(ticker.MultipleLocator(1))
ax.yaxis.set_minor_locator(ticker.MultipleLocator(5))

# Style the ticks
ax.tick_params(which='major', length=10, width=1.5, color='#888888', labelcolor='#333333')
ax.tick_params(which='minor', length=5, width=1.0, color='#bbbbbb')

# Save paths (Saves both PDF and PNG)
output_dir = '/Users/garethperry/.gemini/antigravity/brain/fb917de1-2433-4404-8b52-2d1d797295a5'
os.makedirs(output_dir, exist_ok=True)

output_path_artifact_pdf = os.path.join(output_dir, 'superdarn_latitude_vs_start_year.pdf')
output_path_artifact_png = os.path.join(output_dir, 'superdarn_latitude_vs_start_year.png')
output_path_local_pdf = 'superdarn_latitude_vs_start_year.pdf'
output_path_local_png = 'superdarn_latitude_vs_start_year.png'

plt.tight_layout()
plt.savefig(output_path_artifact_pdf, facecolor='#ffffff', edgecolor='none')
plt.savefig(output_path_artifact_png, facecolor='#ffffff', edgecolor='none', dpi=300)
plt.savefig(output_path_local_pdf, facecolor='#ffffff', edgecolor='none')
plt.savefig(output_path_local_png, facecolor='#ffffff', edgecolor='none', dpi=300)

print("Successfully saved plot files (both PDF and PNG).")
print(f'Total radars plotted: {len(df)}')
