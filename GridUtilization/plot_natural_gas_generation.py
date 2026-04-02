"""
Natural gas generation visualization with 2 panels.

Panel 1: Hourly natural gas generation (MW) over time with hour-of-day coloring
Panel 2: Calendar heat map showing daily % of gas in gross demand
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

# Load hourly data
print("Loading hourly natural gas data...")
with open(os.path.join(script_dir, "natural_gas_hourly.json")) as f:
    hourly_data = json.load(f)

# Load daily data
print("Loading daily natural gas data...")
with open(os.path.join(script_dir, "natural_gas_daily.json")) as f:
    daily_data = json.load(f)

# Parse hourly data
hourly_dates = []
hourly_gas_mw = []
for hour_key, data in sorted(hourly_data.items()):
    # Parse "YYYY-MM-DD HH"
    date_str, hour_str = hour_key.rsplit(' ', 1)
    dt_obj = dt.strptime(f"{date_str} {hour_str}:00", "%Y-%m-%d %H:%M")
    hourly_dates.append(dt_obj)
    hourly_gas_mw.append(data["gas_mw"])

hourly_dates = np.array(hourly_dates)
hourly_gas_mw = np.array(hourly_gas_mw)

print(f"Loaded {len(hourly_dates):,} hourly data points")

# Parse daily data
daily_dates = []
daily_avg_gas_mw = []
daily_avg_gas_pct = []

for date_str in sorted(daily_data.keys()):
    daily_dates.append(dt.strptime(date_str, "%Y-%m-%d"))
    daily_avg_gas_mw.append(daily_data[date_str]["avg_gas_mw"])
    daily_avg_gas_pct.append(daily_data[date_str]["avg_gas_pct"])

daily_dates = np.array(daily_dates)
daily_avg_gas_mw = np.array(daily_avg_gas_mw)
daily_avg_gas_pct = np.array(daily_avg_gas_pct)

print(f"Loaded {len(daily_dates):,} daily data points")

# Style constants
BG_OUTER = "#0f1117"
BG_INNER = "#1a1d2e"
TEXT_COLOR = "#e2e8f0"
GRID_COLOR = "#2a2d3e"
SPINE_COLOR = "#3a3d4e"
ACCENT_CYAN = "#22d3ee"

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
# Panel 1: Hourly natural gas generation with hour-of-day coloring
# ══════════════════════════════════════════════════════════════════════════
print("Creating Panel 1: Hourly natural gas generation...")

x_hours = mdates.date2num(hourly_dates)

# Extract hour of day (0-23) for color mapping
hourly_hours = np.array([d.hour for d in hourly_dates])

# Use hour of day for coloring to show temporal patterns
norm_hour = mcolors.Normalize(vmin=0, vmax=24)

# Plot as scatter with hour-of-day coloring
scatter = ax1.scatter(x_hours, hourly_gas_mw,
                     c=hourly_hours, cmap='hsv', norm=norm_hour,
                     s=3, alpha=0.6, edgecolors="none", rasterized=True)

# Add daily average line to show overall trend
x_daily = mdates.date2num(daily_dates)
ax1.plot(x_daily, daily_avg_gas_mw,
         color="#ffffff", linewidth=1.0, alpha=0.8,
         zorder=4, label="Daily Average")

ax1.set_ylabel("Natural Gas Generation (MW)",
               color=TEXT_COLOR, fontsize=13, fontweight="bold")
ax1.tick_params(axis="y", colors=TEXT_COLOR)
ax1.set_title("California Grid: Hourly Natural Gas Generation \n"
              "Showing decline as renewables + storage replace fossil fuels",
              color="#fff", fontsize=15, fontweight="bold", pad=15)

ax1.xaxis.set_major_locator(mdates.YearLocator())
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
ax1.set_xlim(x_hours[0], x_hours[-1])
ax1.set_ylim(0, max(hourly_gas_mw) * 1.05)
ax1.grid(True, color=GRID_COLOR, linewidth=0.5, alpha=0.7)

# Add legend
ax1.legend(loc='upper right', fontsize=10, framealpha=0.8, facecolor=BG_INNER,
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
# Panel 2: Calendar heat map of daily % gas in gross demand
# ══════════════════════════════════════════════════════════════════════════
print("Creating Panel 2: Calendar heat map of gas percentage...")

years = range(2020, 2027)
n_years = len(years)

# Create year strips
ax2.clear()
ax2.set_facecolor(BG_INNER)

# Calculate positions
strip_height = 0.8
gap = 0.2
y_positions = np.arange(n_years) * (strip_height + gap)

# Create a colormap for gas percentage (0-100%)
# Use Reds colormap: white (0% gas) to dark red (100% gas)
max_gas_pct = 100
cmap = plt.cm.Reds
norm = mcolors.Normalize(vmin=0, vmax=max_gas_pct)

for i, year in enumerate(years):
    year_days = []
    year_gas_pct = []

    for date, gas_pct in zip(daily_dates, daily_avg_gas_pct):
        if date.year == year:
            day_of_year = date.timetuple().tm_yday
            year_days.append(day_of_year)
            year_gas_pct.append(gas_pct)

    if year_days:
        # Create bars for each day
        for day, gas_pct in zip(year_days, year_gas_pct):
            color = cmap(norm(gas_pct))
            ax2.barh(y_positions[i], 1, left=day-0.5, height=strip_height,
                    color=color, edgecolor=BG_INNER, linewidth=0.5)

# Styling
ax2.set_yticks(y_positions + strip_height/2)
ax2.set_yticklabels([str(y) for y in years], fontsize=11, color=TEXT_COLOR)
ax2.set_xlabel("Day of Year", fontsize=12, color="#888", fontweight="bold")
ax2.set_xlim(0, 366)
ax2.set_ylim(-0.2, n_years * (strip_height + gap))
ax2.set_title("Daily Natural Gas as % of Gross Demand\n"
              "Each Strip = One Year, Color Intensity = Gas Dependence",
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
cbar.set_label("Gas % of Demand", fontsize=10, color=TEXT_COLOR)
cbar.set_ticks([0, 20, 40, 60, 80, 100])
cbar.ax.tick_params(colors=TEXT_COLOR, labelsize=9)
cbar.outline.set_edgecolor(SPINE_COLOR)

ax2.grid(False)
for spine in ax2.spines.values():
    spine.set_color(SPINE_COLOR)

# Save
print("Saving figure...")
out_path = os.path.join(script_dir, "natural_gas_generation.png")
fig.savefig(out_path, dpi=200, facecolor=BG_OUTER, bbox_inches="tight")
print(f"Saved to {out_path}")
plt.close()

print("\nVisualization complete!")
