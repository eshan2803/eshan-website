"""
Scatter plots showing relationship between battery discharge and peak LMP prices.
Creates two versions:
  1. LMP vs Battery GW (colored by time)
  2. LMP vs Battery % of demand (colored by time)
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

# ── Match up dates for scatter (only days with both battery and LMP data) ──
scatter_dates = []
scatter_bat_gw = []
scatter_bat_pct = []
scatter_lmp = []

for i, date in enumerate(peak_bat_dates):
    if date in daily_peak_lmp:
        scatter_dates.append(date)
        scatter_bat_gw.append(peak_bat_gw[i])
        scatter_bat_pct.append(peak_bat_pct[i])
        scatter_lmp.append(daily_peak_lmp[date])

scatter_dates = np.array(scatter_dates)
scatter_bat_gw = np.array(scatter_bat_gw)
scatter_bat_pct = np.array(scatter_bat_pct)
scatter_lmp = np.array(scatter_lmp)

print(f"Matched {len(scatter_dates):,} days with both battery and LMP data")
print(f"  Battery GW range: {scatter_bat_gw.min():.2f}-{scatter_bat_gw.max():.2f}")
print(f"  Battery % range: {scatter_bat_pct.min():.2f}-{scatter_bat_pct.max():.2f}%")
print(f"  LMP range: ${scatter_lmp.min():.1f}-${scatter_lmp.max():.1f}")

# ── Time-based colormap (2020 to 2025) ────────────────────────────────────
# Convert dates to numeric values for coloring
date_nums = mdates.date2num(scatter_dates)
time_norm = mcolors.Normalize(vmin=date_nums.min(), vmax=date_nums.max())
time_cmap = plt.cm.viridis  # Purple (2020) -> Yellow (2025)

# For LMP, clip to 99th percentile for better visualization
lmp_p99 = np.percentile(scatter_lmp, 99)

# ── Style constants ───────────────────────────────────────────────────────
BG_COLOR = "#1a1d2e"
TEXT_COLOR = "#e2e8f0"
GRID_COLOR = "#2a2d3e"
SPINE_COLOR = "#334155"

# ══════════════════════════════════════════════════════════════════════════
# Chart 1: LMP vs Battery GW
# ══════════════════════════════════════════════════════════════════════════
fig1, ax1 = plt.subplots(figsize=(10, 8), facecolor=BG_COLOR)
ax1.set_facecolor(BG_COLOR)

scatter1 = ax1.scatter(scatter_bat_gw, scatter_lmp,
                       c=date_nums, cmap=time_cmap, norm=time_norm,
                       s=15, alpha=0.6, edgecolors="none", rasterized=True)

ax1.set_xlabel("Daily Peak Battery Discharge (GW)",
               fontsize=13, color=TEXT_COLOR, fontweight="bold")
ax1.set_ylabel("Daily Peak LMP ($/MWh)",
               fontsize=13, color=TEXT_COLOR, fontweight="bold")
last_data_date = max(sorted(daily_peak_mw_raw.keys())[-1], sorted(price_data.keys())[-1])
last_data_label = datetime.strptime(last_data_date, "%Y-%m-%d").strftime("%B %d, %Y")
ax1.set_title(f"Peak Electricity Price vs Battery Storage Capacity\n"
              f"Updated through {last_data_label}",
              fontsize=14, fontweight="bold", color="#fff", pad=15)

ax1.set_xlim(0, scatter_bat_gw.max() * 1.05)
ax1.set_ylim(0, lmp_p99 * 1.1)
ax1.grid(True, color=GRID_COLOR, linewidth=0.5, alpha=0.5)
ax1.tick_params(colors=TEXT_COLOR, labelsize=10)

for spine in ax1.spines.values():
    spine.set_color(SPINE_COLOR)

# Colorbar
cbar1 = fig1.colorbar(scatter1, ax=ax1, pad=0.02, aspect=30, fraction=0.046)
cbar1.set_label("Time", fontsize=11, color=TEXT_COLOR, fontweight="bold")

# Format colorbar ticks as years
year_dates = [datetime(y, 1, 1) for y in range(2020, 2026)]
year_nums = mdates.date2num(year_dates)
cbar1.set_ticks(year_nums)
cbar1.set_ticklabels(['2020', '2021', '2022', '2023', '2024', '2025'])
cbar1.ax.tick_params(colors=TEXT_COLOR, labelsize=9)
cbar1.outline.set_edgecolor(SPINE_COLOR)

plt.tight_layout()
plt.savefig("lmp_vs_battery_gw_scatter.png", dpi=200,
            bbox_inches="tight", facecolor=BG_COLOR)
print("Saved lmp_vs_battery_gw_scatter.png")
plt.close()

# ══════════════════════════════════════════════════════════════════════════
# Chart 2: LMP vs Battery % of Demand
# ══════════════════════════════════════════════════════════════════════════
fig2, ax2 = plt.subplots(figsize=(10, 8), facecolor=BG_COLOR)
ax2.set_facecolor(BG_COLOR)

scatter2 = ax2.scatter(scatter_bat_pct, scatter_lmp,
                       c=date_nums, cmap=time_cmap, norm=time_norm,
                       s=15, alpha=0.6, edgecolors="none", rasterized=True)

ax2.set_xlabel("Daily Peak Battery Discharge (% of Peak Demand)",
               fontsize=13, color=TEXT_COLOR, fontweight="bold")
ax2.set_ylabel("Daily Peak LMP ($/MWh)",
               fontsize=13, color=TEXT_COLOR, fontweight="bold")
ax2.set_title(f"Peak Electricity Price vs Battery Grid Penetration\n"
              f"Updated through {last_data_label}",
              fontsize=14, fontweight="bold", color="#fff", pad=15)

ax2.set_xlim(0, scatter_bat_pct.max() * 1.05)
ax2.set_ylim(0, lmp_p99 * 1.1)
ax2.grid(True, color=GRID_COLOR, linewidth=0.5, alpha=0.5)
ax2.tick_params(colors=TEXT_COLOR, labelsize=10)

for spine in ax2.spines.values():
    spine.set_color(SPINE_COLOR)

# Colorbar
cbar2 = fig2.colorbar(scatter2, ax=ax2, pad=0.02, aspect=30, fraction=0.046)
cbar2.set_label("Time", fontsize=11, color=TEXT_COLOR, fontweight="bold")

# Format colorbar ticks as years
cbar2.set_ticks(year_nums)
cbar2.set_ticklabels(['2020', '2021', '2022', '2023', '2024', '2025'])
cbar2.ax.tick_params(colors=TEXT_COLOR, labelsize=9)
cbar2.outline.set_edgecolor(SPINE_COLOR)

plt.tight_layout()
plt.savefig("lmp_vs_battery_pct_scatter.png", dpi=200,
            bbox_inches="tight", facecolor=BG_COLOR)
print("Saved lmp_vs_battery_pct_scatter.png")
plt.close()

print("\nVisualization complete!")
