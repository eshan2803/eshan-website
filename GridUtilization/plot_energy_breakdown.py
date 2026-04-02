"""
Energy breakdown visualization with 2 panels.

Panel 1: Daily energy (MWh) stacked area chart (Natural Gas, Clean, Imports) + demand line
Panel 2: Calendar heat map showing daily clean energy %
"""
import json
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.dates as mdates
from datetime import datetime as dt
import calendar

script_dir = os.path.dirname(os.path.abspath(__file__))

# Load daily energy data
print("Loading daily energy breakdown...")
with open(os.path.join(script_dir, "daily_energy_breakdown.json")) as f:
    daily_data = json.load(f)

# Parse data
daily_dates = []
natural_gas_mwh = []
clean_mwh = []
imports_mwh = []
gross_demand_mwh = []
clean_pct = []

for date_str in sorted(daily_data.keys()):
    daily_dates.append(dt.strptime(date_str, "%Y-%m-%d"))
    natural_gas_mwh.append(daily_data[date_str]["natural_gas_mwh"])
    clean_mwh.append(daily_data[date_str]["clean_mwh"])
    imports_mwh.append(daily_data[date_str]["imports_mwh"])
    gross_demand_mwh.append(daily_data[date_str]["gross_demand_mwh"])
    clean_pct.append(daily_data[date_str]["clean_pct"])

daily_dates = np.array(daily_dates)
natural_gas_mwh = np.array(natural_gas_mwh)
clean_mwh = np.array(clean_mwh)
imports_mwh = np.array(imports_mwh)
gross_demand_mwh = np.array(gross_demand_mwh)
clean_pct = np.array(clean_pct)

print(f"Loaded {len(daily_dates):,} daily data points")
print(f"Date range: {daily_dates[0].strftime('%Y-%m-%d')} to {daily_dates[-1].strftime('%Y-%m-%d')}")

# Style constants
BG_OUTER = "#0f1117"
BG_INNER = "#1a1d2e"
TEXT_COLOR = "#e2e8f0"
GRID_COLOR = "#2a2d3e"
SPINE_COLOR = "#3a3d4e"

# Create figure with 2 panels
fig = plt.figure(figsize=(16, 12), facecolor=BG_OUTER)
gs = fig.add_gridspec(2, 1, height_ratios=[1, 1.2], hspace=0.3)

ax1 = fig.add_subplot(gs[0])
ax2 = fig.add_subplot(gs[1])

for ax in [ax1, ax2]:
    ax.set_facecolor(BG_INNER)
    ax.tick_params(colors="#888", labelsize=10)
    for spine in ax.spines.values():
        spine.set_color(SPINE_COLOR)

# ══════════════════════════════════════════════════════════════════════════
# Panel 1: Daily energy stacked area chart
# ══════════════════════════════════════════════════════════════════════════
print("Creating Panel 1: Daily energy stacked area chart...")

x_dates = mdates.date2num(daily_dates)

# Stack the areas (bottom to top): Natural Gas, Clean, Imports
# Convert to GWh for better readability (divide by 1000)
gas_gwh = natural_gas_mwh / 1000.0
clean_gwh = clean_mwh / 1000.0
imports_gwh = imports_mwh / 1000.0
demand_gwh = gross_demand_mwh / 1000.0

# Stacked area plot
ax1.fill_between(x_dates, 0, gas_gwh,
                 color="#f97316", alpha=0.8, label="Natural Gas", zorder=2)
ax1.fill_between(x_dates, gas_gwh, gas_gwh + clean_gwh,
                 color="#4ade80", alpha=0.8, label="Clean Energy", zorder=2)
ax1.fill_between(x_dates, gas_gwh + clean_gwh, gas_gwh + clean_gwh + imports_gwh,
                 color="#a78bfa", alpha=0.7, label="Imports (mixed)", zorder=2)

# Overlay total demand line
ax1.plot(x_dates, demand_gwh,
         color="#ffffff", linewidth=1.0, alpha=0.8,
         zorder=4, label="Gross Demand")

ax1.set_ylabel("Daily Energy (GWh)",
               color=TEXT_COLOR, fontsize=13, fontweight="bold")
ax1.tick_params(axis="y", colors=TEXT_COLOR)
ax1.set_title("California Grid: Daily Energy Supply & Demand \n"
              "Stacked: Natural Gas + Clean Energy + Imports",
              color="#fff", fontsize=15, fontweight="bold", pad=15)

ax1.xaxis.set_major_locator(mdates.YearLocator())
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
ax1.set_xlim(x_dates[0], x_dates[-1])
ax1.set_ylim(0, 1200)
ax1.grid(True, color=GRID_COLOR, linewidth=0.5, alpha=0.7, axis='y')
ax1.grid(True, color=GRID_COLOR, linewidth=0.3, alpha=0.4, axis='x')

# Legend
ax1.legend(loc='upper left', fontsize=11, framealpha=0.9, facecolor=BG_INNER,
           edgecolor=SPINE_COLOR, labelcolor=TEXT_COLOR)

# ══════════════════════════════════════════════════════════════════════════
# Panel 2: Calendar heat map of daily clean energy %
# ══════════════════════════════════════════════════════════════════════════
print("Creating Panel 2: Calendar heat map of clean energy %...")

years = range(2020, 2027)
n_years = len(years)

# Create year strips
ax2.clear()
ax2.set_facecolor(BG_INNER)

# Calculate positions
strip_height = 0.8
gap = 0.2
y_positions = np.arange(n_years) * (strip_height + gap)

# Create a colormap for clean % (0-100%)
# Use Greens colormap: white (0% clean) to dark green (100% clean)
max_clean_pct = 100
cmap = plt.cm.Greens
norm = mcolors.Normalize(vmin=0, vmax=max_clean_pct)

for i, year in enumerate(years):
    year_days = []
    year_clean_pct = []

    for date, pct in zip(daily_dates, clean_pct):
        if date.year == year:
            day_of_year = date.timetuple().tm_yday
            year_days.append(day_of_year)
            year_clean_pct.append(pct)

    if year_days:
        # Create bars for each day
        for day, pct in zip(year_days, year_clean_pct):
            color = cmap(norm(pct))
            ax2.barh(y_positions[i], 1, left=day-0.5, height=strip_height,
                    color=color, edgecolor=BG_INNER, linewidth=0.5)

# Styling
ax2.set_yticks(y_positions + strip_height/2)
ax2.set_yticklabels([str(y) for y in years], fontsize=11, color=TEXT_COLOR)
ax2.set_xlabel("Day of Year", fontsize=12, color="#888", fontweight="bold")
ax2.set_xlim(0, 366)
ax2.set_ylim(-0.2, n_years * (strip_height + gap))
ax2.set_title("Daily Clean Energy Percentage (Strict Definition)\n"
              "Clean % = Clean Energy / (Gas + Clean + Imports) × 100",
              color="#fff", fontsize=14, fontweight="bold", pad=12)

# Month markers
month_days = [0]
for m in range(1, 13):
    month_days.append(month_days[-1] + calendar.monthrange(2024, m)[1])
month_centers = [(month_days[i] + month_days[i+1])/2 for i in range(12)]
ax2.set_xticks(month_centers)
ax2.set_xticklabels(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
                     fontsize=9, color="#888")

# Add vertical lines for months
for day in month_days[1:-1]:
    ax2.axvline(day, color=SPINE_COLOR, linewidth=0.5, alpha=0.5)

# Colorbar
sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
sm.set_array([])
cbar = fig.colorbar(sm, ax=ax2, orientation='vertical', pad=0.01,
                    aspect=20, fraction=0.03)
cbar.set_label("Clean Energy %", fontsize=10, color=TEXT_COLOR)
cbar.set_ticks([0, 20, 40, 60, 80, 100])
cbar.ax.tick_params(colors=TEXT_COLOR, labelsize=9)
cbar.outline.set_edgecolor(SPINE_COLOR)

ax2.grid(False)
for spine in ax2.spines.values():
    spine.set_color(SPINE_COLOR)

# Save
print("Saving figure...")
out_path = os.path.join(script_dir, "energy_breakdown.png")
fig.savefig(out_path, dpi=200, facecolor=BG_OUTER, bbox_inches="tight")
print(f"Saved to {out_path}")
plt.close()

print("\nVisualization complete!")
