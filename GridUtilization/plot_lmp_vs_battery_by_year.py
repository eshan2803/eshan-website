"""
Scatter plots showing relationship between battery discharge (GW) and peak LMP prices.
One subplot per year (2020-2025), colored by battery % of peak demand.
"""
import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.dates as mdates
from datetime import datetime

# ── Load data ──────────────────────────────────────────────────────────────
with open("caiso_battery_daily_peak_mw.json") as f:
    daily_peak_mw_raw = json.load(f)

with open("caiso_battery_daily_peak.json") as f:
    daily_peak_pct_raw = json.load(f)

with open("caiso_prices.json") as f:
    price_data = json.load(f)

# ── Daily peak battery GW and % ───────────────────────────────────────────
peak_bat_dates = [datetime.strptime(d, "%Y-%m-%d") for d in sorted(daily_peak_mw_raw.keys())]
peak_bat_mw = [daily_peak_mw_raw[d] for d in sorted(daily_peak_mw_raw.keys())]
peak_bat_gw = [mw / 1000.0 for mw in peak_bat_mw]  # Convert MW to GW
peak_bat_pct = [daily_peak_pct_raw.get(d, 0) for d in sorted(daily_peak_mw_raw.keys())]

# ── Daily peak LMP ───────────────────────────────────────────────────────
daily_peak_lmp = {}
for date_str, hours_dict in price_data.items():
    if not isinstance(hours_dict, dict):
        continue
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    for h_str, vals in hours_dict.items():
        if isinstance(vals, dict) and "LMP" in vals:
            lmp = vals["LMP"]
            if dt not in daily_peak_lmp or lmp > daily_peak_lmp[dt]:
                daily_peak_lmp[dt] = lmp

# ── Match up dates and organize by year ───────────────────────────────────
data_by_year = {year: {'gw': [], 'pct': [], 'lmp': []} for year in range(2020, 2027)}

for i, date in enumerate(peak_bat_dates):
    if date in daily_peak_lmp:
        year = date.year
        if year in data_by_year:
            data_by_year[year]['gw'].append(peak_bat_gw[i])
            data_by_year[year]['pct'].append(peak_bat_pct[i])
            data_by_year[year]['lmp'].append(daily_peak_lmp[date])

# Convert to numpy arrays
for year in data_by_year:
    data_by_year[year]['gw'] = np.array(data_by_year[year]['gw'])
    data_by_year[year]['pct'] = np.array(data_by_year[year]['pct'])
    data_by_year[year]['lmp'] = np.array(data_by_year[year]['lmp'])
    print(f"{year}: {len(data_by_year[year]['gw'])} days")

# ── Calculate global ranges for consistent axes ───────────────────────────
all_gw = np.concatenate([data_by_year[y]['gw'] for y in range(2020, 2027)])
all_pct = np.concatenate([data_by_year[y]['pct'] for y in range(2020, 2027)])
all_lmp = np.concatenate([data_by_year[y]['lmp'] for y in range(2020, 2027)])

max_gw = all_gw.max()
max_pct = all_pct.max()
lmp_p99 = np.percentile(all_lmp, 99)

print(f"\nGlobal ranges:")
print(f"  Battery GW: 0-{max_gw:.2f}")
print(f"  Battery %: 0-{max_pct:.1f}%")
print(f"  LMP (p99): ${lmp_p99:.1f}")

# ── Style constants ───────────────────────────────────────────────────────
BG_COLOR = "#1a1d2e"
TEXT_COLOR = "#e2e8f0"
GRID_COLOR = "#2a2d3e"
SPINE_COLOR = "#334155"

# Colormap for battery % (plasma: purple -> yellow)
pct_cmap = plt.cm.plasma
pct_norm = mcolors.Normalize(vmin=0, vmax=100)

# ══════════════════════════════════════════════════════════════════════════
# Create 2x4 grid of subplots
# ══════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(2, 4, figsize=(24, 12), facecolor=BG_COLOR)
fig.suptitle("Peak Electricity Price vs Battery Storage Capacity by Year\n"
             "Color = Battery as % of Peak Demand",
             fontsize=16, fontweight="bold", color="#fff", y=0.995)

axes = axes.flatten()

for idx, year in enumerate(range(2020, 2027)):
    ax = axes[idx]
    ax.set_facecolor(BG_COLOR)

    gw = data_by_year[year]['gw']
    pct = data_by_year[year]['pct']
    lmp = data_by_year[year]['lmp']

    if len(gw) > 0:
        scatter = ax.scatter(gw, lmp,
                           c=pct, cmap=pct_cmap, norm=pct_norm,
                           s=20, alpha=0.6, edgecolors="none", rasterized=True)

    # Axis labels
    if idx >= 3:  # Bottom row
        ax.set_xlabel("Daily Peak Battery Discharge (GW)",
                     fontsize=11, color=TEXT_COLOR, fontweight="bold")
    if idx % 3 == 0:  # Left column
        ax.set_ylabel("Daily Peak LMP ($/MWh)",
                     fontsize=11, color=TEXT_COLOR, fontweight="bold")

    # Title for each subplot
    ax.set_title(f"{year}", fontsize=13, fontweight="bold", color="#fff", pad=10)

    # Set consistent ranges
    ax.set_xlim(-0.2, max_gw * 1.05)
    ax.set_ylim(0, lmp_p99 * 1.1)

    # Grid and styling
    ax.grid(True, color=GRID_COLOR, linewidth=0.5, alpha=0.4)
    ax.tick_params(colors=TEXT_COLOR, labelsize=9)

    for spine in ax.spines.values():
        spine.set_color(SPINE_COLOR)

    # Add data count
    ax.text(0.02, 0.98, f"n={len(gw)}", transform=ax.transAxes,
            fontsize=9, color="#888", va='top', ha='left')

# Hide unused subplot (2027 has no data yet)
if len(axes) > 7:
    axes[7].set_visible(False)

# Add single colorbar for all subplots
fig.subplots_adjust(right=0.92)
cbar_ax = fig.add_axes([0.94, 0.15, 0.015, 0.7])
sm = plt.cm.ScalarMappable(cmap=pct_cmap, norm=pct_norm)
sm.set_array([])
cbar = fig.colorbar(sm, cax=cbar_ax)
cbar.set_label("Battery % of Peak Demand", fontsize=12, color=TEXT_COLOR, fontweight="bold")
cbar.set_ticks([0, 20, 40, 60, 80, 100])
cbar.ax.tick_params(colors=TEXT_COLOR, labelsize=10)
cbar.outline.set_edgecolor(SPINE_COLOR)

plt.savefig("lmp_vs_battery_by_year.png", dpi=200,
            bbox_inches="tight", facecolor=BG_COLOR)
print(f"\nSaved lmp_vs_battery_by_year.png")
print("Visualization complete!")
