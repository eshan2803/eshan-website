"""
Plot ancillary service prices vs LMP by year (2020-2026 Q1)
Creates 4 charts (RU, RD, SR, NR), each with 6 subplots (one per year)
Hourly data: each AS price plotted against LMP for that hour
"""
import json
import os
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

script_dir = os.path.dirname(os.path.abspath(__file__))

# Load ancillary services data
print("Loading ancillary services data...")
with open(os.path.join(script_dir, "ancillary_services.json")) as f:
    as_data = json.load(f)

# Load LMP data from caiso_prices.json (has all years)
print("Loading LMP data...")
with open(os.path.join(script_dir, "caiso_prices.json")) as f:
    lmp_data = json.load(f)

# Parse hourly data by year
print("Parsing hourly data by year...")
data_by_year = {year: {'ru': [], 'rd': [], 'sr': [], 'nr': [], 'lmp': []}
                for year in range(2020, 2027)}

for date_str, hourly_as in as_data.items():
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        year = dt.year

        if year not in data_by_year:
            continue

        # Get hourly LMP data for this date
        hourly_lmp = lmp_data.get(date_str, {})

        # Process each hour
        for hour, as_values in hourly_as.items():
            if not isinstance(as_values, dict):
                continue

            # Get AS prices for this hour
            ru = as_values.get('RU', None)
            rd = as_values.get('RD', None)
            sr = as_values.get('SR', None)
            nr = as_values.get('NR', None)

            # Get LMP for this hour
            lmp_hour_data = hourly_lmp.get(hour, {})
            if not isinstance(lmp_hour_data, dict):
                continue

            lmp = lmp_hour_data.get('LMP', None)

            # Store if all values present
            if all(v is not None for v in [ru, rd, sr, nr, lmp]):
                data_by_year[year]['ru'].append(ru)
                data_by_year[year]['rd'].append(rd)
                data_by_year[year]['sr'].append(sr)
                data_by_year[year]['nr'].append(nr)
                data_by_year[year]['lmp'].append(lmp)

    except (ValueError, KeyError) as e:
        continue

print("Data loaded successfully")
for year in range(2020, 2027):
    print(f"  {year}: {len(data_by_year[year]['ru']):,} hourly data points")

# Calculate global y-axis limits for each AS type (99th percentile across all years)
print("\nCalculating global y-axis limits...")
global_limits = {}
for as_key in ['ru', 'rd', 'sr', 'nr']:
    all_values = []
    for year in range(2020, 2027):
        all_values.extend(data_by_year[year][as_key])
    if all_values:
        global_limits[as_key] = np.percentile(all_values, 99)
        print(f"  {as_key.upper()}: 0 to {global_limits[as_key]:.1f} $/MWh")
    else:
        global_limits[as_key] = 100

# Calculate global x-axis limit for LMP
all_lmp = []
for year in range(2020, 2027):
    all_lmp.extend(data_by_year[year]['lmp'])
lmp_limit = np.percentile(all_lmp, 99)
print(f"  LMP: 0 to {lmp_limit:.1f} $/MWh")

# Style constants
BG_COLOR = "#1a1d2e"
TEXT_COLOR = "#e2e8f0"
GRID_COLOR = "#2a2d3e"
SPINE_COLOR = "#3a3d4e"

# Create charts for each AS type
as_types = [
    ('ru', 'Regulation Up (RU)', '#60a5fa'),
    ('rd', 'Regulation Down (RD)', '#4ade80'),
    ('sr', 'Spinning Reserve (SR)', '#facc15'),
    ('nr', 'Non-Spinning Reserve (NR)', '#f97316')
]

for as_key, as_title, as_color in as_types:
    print(f"\nCreating chart for {as_title}...")

    fig, axes = plt.subplots(2, 4, figsize=(24, 12), facecolor=BG_COLOR)
    fig.suptitle(f"{as_title} Price vs. LMP by Year (2020-2026 Q1)\nHourly Data",
                 fontsize=16, fontweight='bold', color='#fff', y=0.995)

    axes = axes.flatten()
    years = list(range(2020, 2027))

    for idx, year in enumerate(years):
        ax = axes[idx]
        ax.set_facecolor(BG_COLOR)

        as_prices = np.array(data_by_year[year][as_key])
        lmp_prices = np.array(data_by_year[year]['lmp'])

        if len(as_prices) > 0:
            # Cap at global limits for consistent axes
            as_prices_capped = np.clip(as_prices, 0, global_limits[as_key])
            lmp_prices_capped = np.clip(lmp_prices, 0, lmp_limit)

            # Scatter plot
            ax.scatter(lmp_prices_capped, as_prices_capped,
                      c=as_color, s=3, alpha=0.4, edgecolors='none', rasterized=True)

            ax.set_title(f"{year}", fontsize=14, fontweight='bold', color='#fff', pad=10)
            ax.set_xlabel("LMP ($/MWh)", fontsize=11, color=TEXT_COLOR)

            if idx % 3 == 0:
                ax.set_ylabel(f"{as_title} Price ($/MWh)", fontsize=11, color=TEXT_COLOR, fontweight='bold')

            # Set consistent limits across all subplots
            ax.set_xlim(0, lmp_limit)
            ax.set_ylim(0, global_limits[as_key])

            ax.grid(True, color=GRID_COLOR, linewidth=0.5, alpha=0.5)
            ax.tick_params(colors=TEXT_COLOR, labelsize=9)

            for spine in ax.spines.values():
                spine.set_color(SPINE_COLOR)

            # Add sample size
            ax.text(0.02, 0.98, f"n={len(as_prices):,}",
                   transform=ax.transAxes, fontsize=9, color=TEXT_COLOR,
                   verticalalignment='top', alpha=0.7)

    # Hide unused subplot (2027 has no data yet)
    if len(axes) > 7:
        axes[7].set_visible(False)

    plt.tight_layout()
    out_path = os.path.join(script_dir, f"{as_key}_vs_lmp_by_year.png")
    plt.savefig(out_path, dpi=200, bbox_inches='tight', facecolor=BG_COLOR)
    print(f"Saved to {out_path}")
    plt.close()

print("\nAll LMP charts created successfully!")
