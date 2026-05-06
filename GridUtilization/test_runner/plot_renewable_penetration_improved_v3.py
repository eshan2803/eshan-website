"""
Improved 2-panel clean energy penetration visualization (V3 - ENERGY-BASED).

ENERGY-BASED changes:
- Daily penetration = Total Clean Energy (MWh) / Total Load (MWh) × 100
- This differs from V3 which averaged hourly percentages
- Clean energy includes battery discharge + Nuclear + Large hydro
- Demand includes all sources (battery too)
- Shows clean/zero-carbon energy vs actual grid load

Panel 1: All hourly clean energy % values (2020-2025) with 100% threshold line
Panel 2: Calendar heat map showing daily hours ≥100%
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

# Load hourly data (CORRECTED - uses actual demand CSVs)
print("Loading hourly data (CORRECTED)...")
with open(os.path.join(script_dir, "renewable_penetration_hourly_corrected.json")) as f:
    hourly_data = json.load(f)

# Load daily data (ENERGY-BASED)
print("Loading daily data (ENERGY-BASED)...")
with open(os.path.join(script_dir, "renewable_penetration_daily_energy_based.json")) as f:
    daily_data = json.load(f)

# Parse hourly data
hourly_dates = []
hourly_pct = []
for hour_key, pct in sorted(hourly_data.items()):
    # Parse "YYYY-MM-DD HH"
    date_str, hour_str = hour_key.rsplit(' ', 1)
    dt_obj = dt.strptime(f"{date_str} {hour_str}:00", "%Y-%m-%d %H:%M")
    hourly_dates.append(dt_obj)
    hourly_pct.append(pct)

hourly_dates = np.array(hourly_dates)
hourly_pct = np.array(hourly_pct)

print(f"Loaded {len(hourly_dates):,} hourly data points")

# Parse daily data (avg_penetration from energy-based for the daily average line)
daily_dates = []
daily_avg_penetration = []

for date_str in sorted(daily_data.keys()):
    daily_dates.append(dt.strptime(date_str, "%Y-%m-%d"))
    daily_avg_penetration.append(daily_data[date_str]["avg_penetration"])

daily_dates = np.array(daily_dates)
daily_avg_penetration = np.array(daily_avg_penetration)

# Derive hours_over_100 from the SAME hourly corrected data used in Panel 1
# The energy_based script uses generation-sum as denominator (includes exports),
# which rarely exceeds 100%. The hourly corrected data uses actual demand from
# demand CSVs, matching Panel 1's definition of >=100%.
from collections import defaultdict
hours_over_100_by_date = defaultdict(int)
for hour_key, pct in hourly_data.items():
    date_str = hour_key.rsplit(' ', 1)[0]
    if pct >= 100:
        hours_over_100_by_date[date_str] += 1

daily_hours_over_100 = np.array([
    hours_over_100_by_date.get(d.strftime("%Y-%m-%d"), 0) for d in daily_dates
])

print(f"Loaded {len(daily_dates):,} daily data points")

# Style constants
BG_OUTER = "#0f1117"
BG_INNER = "#1a1d2e"
TEXT_COLOR = "#e2e8f0"
GRID_COLOR = "#2a2d3e"
SPINE_COLOR = "#3a3d4e"
ACCENT_GREEN = "#10b981"
ACCENT_ORANGE = "#f97316"
ACCENT_CYAN = "#22d3ee"
ACCENT_PURPLE = "#a855f7"

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
# Panel 1: All hourly clean energy penetration values (scatter)
# ══════════════════════════════════════════════════════════════════════════
print("Creating Panel 1: Hourly penetration...")

x_hours = mdates.date2num(hourly_dates)

# Extract hour of day (0-23) for color mapping
hourly_hours = np.array([d.hour for d in hourly_dates])

# Use hour of day for coloring to show temporal patterns
# HSV colormap: cycles through full color spectrum over 24 hours
norm_hour = mcolors.Normalize(vmin=0, vmax=24)

# Plot as scatter with hour-of-day coloring
scatter = ax1.scatter(x_hours, hourly_pct,
                     c=hourly_hours, cmap='hsv', norm=norm_hour,
                     s=3, alpha=0.6, edgecolors="none", rasterized=True)

# Add daily average line to show overall trend
x_daily = mdates.date2num(daily_dates)
ax1.plot(x_daily, daily_avg_penetration,
         color="#ffffff", linewidth=1.0, alpha=0.8,
         zorder=4, label="Daily Average")

# 100% threshold line
ax1.axhline(100, color="#ffffff", linewidth=2, linestyle="--",
            alpha=0.8, zorder=5)

ax1.set_ylabel("Clean Energy Penetration (%)",
               color=TEXT_COLOR, fontsize=13, fontweight="bold")
ax1.tick_params(axis="y", colors=TEXT_COLOR)
last_date_fmt = sorted(daily_data.keys())[-1]
last_date_label = dt.strptime(last_date_fmt, "%Y-%m-%d").strftime("%B %d, %Y")
ax1.set_title(f"California Grid: Hourly Clean Energy Penetration\n"
              f"Updated through {last_date_label}",
              color="#fff", fontsize=15, fontweight="bold", pad=15)

ax1.xaxis.set_major_locator(mdates.YearLocator())
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
ax1.set_xlim(x_hours[0], x_hours[-1])
ax1.set_ylim(0, max(hourly_pct) * 1.05)
ax1.grid(True, color=GRID_COLOR, linewidth=0.5, alpha=0.7)

# Add legend
ax1.legend(loc='upper left', fontsize=10, framealpha=0.8, facecolor=BG_INNER,
           edgecolor=SPINE_COLOR, labelcolor=TEXT_COLOR)

# Add colorbar for hour of day
cbar1 = fig.colorbar(scatter, ax=ax1, orientation='vertical', pad=0.01,
                    aspect=20, fraction=0.03)
cbar1.set_label("Hour of Day", fontsize=10, color=TEXT_COLOR)
cbar1.set_ticks([0, 6, 12, 18, 23])
cbar1.set_ticklabels(['0 (midnight)', '6am', '12 (noon)', '6pm', '23'])
cbar1.ax.tick_params(colors=TEXT_COLOR, labelsize=9)
cbar1.outline.set_edgecolor(SPINE_COLOR)

# ══════════════════════════════════════════════════════════════════════════
# Panel 2: Calendar heat map of daily hours ≥100%
# ══════════════════════════════════════════════════════════════════════════
print("Creating Panel 2: Calendar heat map...")

# Create a matrix: rows=weeks, cols=7 days
# We'll create a simplified yearly strip chart
years = range(2020, 2027)
n_years = len(years)

# Create year strips
ax2.clear()
ax2.set_facecolor(BG_INNER)

# Calculate positions
strip_height = 0.8
gap = 0.2
y_positions = np.arange(n_years) * (strip_height + gap)

# Create a colormap for hours ≥100%
# Use fixed 0-24 hour scale to show progress toward 24/7 clean energy goal
max_hours = 24  # Fixed scale (0-24 hours per day)
# Use green gradient: white (0 hours) to dark green (24 hours)
cmap = plt.cm.Greens  # Green gradient - higher values = darker green
norm = mcolors.Normalize(vmin=0, vmax=max_hours)

for i, year in enumerate(years):
    year_days = []
    year_hours = []

    for date, hours in zip(daily_dates, daily_hours_over_100):
        if date.year == year:
            day_of_year = date.timetuple().tm_yday
            year_days.append(day_of_year)
            year_hours.append(hours)

    if year_days:
        # Create bars for each day
        for day, hours in zip(year_days, year_hours):
            color = cmap(norm(hours))
            ax2.barh(y_positions[i], 1, left=day-0.5, height=strip_height,
                    color=color, edgecolor=BG_INNER, linewidth=0.5)

# Styling
ax2.set_yticks(y_positions + strip_height/2)
ax2.set_yticklabels([str(y) for y in years], fontsize=11, color=TEXT_COLOR)
ax2.set_xlabel("Day of Year", fontsize=12, color="#888", fontweight="bold")
ax2.set_xlim(0, 366)
ax2.set_ylim(-0.2, n_years * (strip_height + gap))
ax2.set_title("Daily Hours with ≥100% Clean Energy Penetration\n"
              "Each Strip = One Year, Color Intensity = Hours Per Day",
              color="#fff", fontsize=14, fontweight="bold", pad=12)

# Month markers
month_days = [0]
for m in range(1, 13):
    month_days.append(month_days[-1] + calendar.monthrange(2024, m)[1])  # Use 2024 (leap year)
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
cbar.set_label("Hours ≥100%", fontsize=10, color=TEXT_COLOR)
cbar.set_ticks([0, 6, 12, 18, 24])
cbar.ax.tick_params(colors=TEXT_COLOR, labelsize=9)
cbar.outline.set_edgecolor(SPINE_COLOR)

ax2.grid(False)
for spine in ax2.spines.values():
    spine.set_color(SPINE_COLOR)


# Save
print("Saving figure...")
out_path = os.path.join(script_dir, "renewable_penetration_improved_v3.png")
fig.savefig(out_path, dpi=200, facecolor=BG_OUTER, bbox_inches="tight")
print(f"Saved to {out_path}")
plt.close()

print("\nVisualization complete!")
