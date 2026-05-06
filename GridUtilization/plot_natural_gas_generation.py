import json
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.dates as mdates
import pandas as pd
from datetime import datetime as dt
import calendar

script_dir = os.path.dirname(os.path.abspath(__file__))

# ══════════════════════════════════════════════════════════════════════════
# Load and Parse Data using Pandas for speed
# ══════════════════════════════════════════════════════════════════════════
print("Loading natural gas data...")

# Load hourly data
with open(os.path.join(script_dir, "natural_gas_hourly.json")) as f:
    hourly_data_raw = json.load(f)

# Fast parsing of hourly data
hourly_records = []
for k, v in hourly_data_raw.items():
    hourly_records.append({'timestamp': f"{k}:00", 'gas_mw': v['gas_mw']})

hourly_df = pd.DataFrame.from_records(hourly_records)
hourly_df['timestamp'] = pd.to_datetime(hourly_df['timestamp'], format="%Y-%m-%d %H:%M")
hourly_df.set_index('timestamp', inplace=True)
hourly_df.sort_index(inplace=True)

# Load daily data
with open(os.path.join(script_dir, "natural_gas_daily.json")) as f:
    daily_data_raw = json.load(f)

daily_records = []
for k, v in daily_data_raw.items():
    daily_records.append({
        'date': k, 
        'avg_gas_mw': v['avg_gas_mw'],
        'avg_gas_pct': v.get('avg_gas_pct', 0)
    })

daily_df = pd.DataFrame.from_records(daily_records)
daily_df['date'] = pd.to_datetime(daily_df['date'])
daily_df.set_index('date', inplace=True)
daily_df.sort_index(inplace=True)

print(f"Loaded {len(hourly_df):,} hourly data points")
print(f"Loaded {len(daily_df):,} daily data points")

# Style constants
BG_OUTER = "#0f1117"
BG_INNER = "#1a1d2e"
TEXT_COLOR = "#e2e8f0"
GRID_COLOR = "#2a2d3e"
SPINE_COLOR = "#3a3d4e"
ACCENT_CYAN = "#22d3ee"

# Create figure with 2 panels
print("Generating chart panels...")
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

x_hours = mdates.date2num(hourly_df.index)
hourly_hours = hourly_df.index.hour.values
hourly_gas_mw = hourly_df['gas_mw'].values

# Use hour of day for coloring to show temporal patterns
norm_hour = mcolors.Normalize(vmin=0, vmax=24)

# Plot as scatter with hour-of-day coloring
scatter = ax1.scatter(x_hours, hourly_gas_mw,
                     c=hourly_hours, cmap='hsv', norm=norm_hour,
                     s=3, alpha=0.6, edgecolors="none", rasterized=True)

# Add daily average line to show overall trend
x_daily = mdates.date2num(daily_df.index)
ax1.plot(x_daily, daily_df['avg_gas_mw'].values,
         color="#ffffff", linewidth=1.0, alpha=0.8,
         zorder=4, label="Daily Average")

ax1.set_ylabel("Natural Gas Generation (MW)",
               color=TEXT_COLOR, fontsize=13, fontweight="bold")
ax1.tick_params(axis="y", colors=TEXT_COLOR)

last_date_fmt = daily_df.index[-1].strftime("%B %d, %Y")
ax1.set_title(f"California Grid: Hourly Natural Gas Generation\n"
              f"Updated through {last_date_fmt}",
              color="#fff", fontsize=15, fontweight="bold", pad=15)

ax1.xaxis.set_major_locator(mdates.YearLocator())
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
ax1.set_xlim(x_hours[0], x_hours[-1])
ax1.set_ylim(0, hourly_gas_mw.max() * 1.05)
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

# Vectorized approach for calendar heatmap
daily_df['year'] = daily_df.index.year
daily_df['day_of_year'] = daily_df.index.dayofyear

years = list(range(2020, 2027)) # Consistent with other charts
n_years = len(years)
year_to_idx = {y: i for i, y in enumerate(years)}

ax2.clear()
ax2.set_facecolor(BG_INNER)

# Calculate positions
strip_height = 0.8
gap = 0.2
y_positions = np.arange(n_years) * (strip_height + gap)

cmap = plt.cm.Reds
norm = mcolors.Normalize(vmin=0, vmax=100)

# Filter dataframe to the years we care about
plot_df = daily_df[daily_df['year'].isin(years)]

if not plot_df.empty:
    # Map years to their y-position
    y_vals = plot_df['year'].map(year_to_idx).values * (strip_height + gap)
    
    # Calculate colors vectorized
    colors = cmap(norm(plot_df['avg_gas_pct'].values))
    
    # Plot using a collection for maximum performance
    ax2.barh(y_vals, width=1.0, left=plot_df['day_of_year'].values - 0.5, 
            height=strip_height, color=colors, edgecolor=BG_INNER, linewidth=0.5)

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
    month_days.append(month_days[-1] + calendar.monthrange(2024, m)[1]) # use leap year for reference
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
