"""
Plot daily renewable energy penetration >100%.
Similar style to battery daily charts.
"""
import json
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.dates as mdates
from datetime import datetime as dt

script_dir = os.path.dirname(os.path.abspath(__file__))

# Load data
with open(os.path.join(script_dir, "renewable_penetration_daily.json")) as f:
    renewable_data = json.load(f)

# Extract daily data
dates = []
hours_over_100 = []
avg_oversupply = []
avg_penetration = []
max_penetration = []

for date_str in sorted(renewable_data.keys()):
    dates.append(dt.strptime(date_str, "%Y-%m-%d"))
    hours_over_100.append(renewable_data[date_str]["hours_over_100"])
    avg_oversupply.append(renewable_data[date_str]["avg_oversupply_pct"])
    avg_penetration.append(renewable_data[date_str]["avg_penetration"])
    max_penetration.append(renewable_data[date_str]["max_penetration"])

dates = np.array(dates)
hours_over_100 = np.array(hours_over_100)
avg_oversupply = np.array(avg_oversupply)
avg_penetration = np.array(avg_penetration)
max_penetration = np.array(max_penetration)

# Convert dates to matplotlib format
x_dates = mdates.date2num(dates)

# Style constants
BG_OUTER = "#0f1117"
BG_INNER = "#1a1d2e"
TEXT_COLOR = "#e2e8f0"
GRID_COLOR = "#2a2d3e"
SPINE_COLOR = "#3a3d4e"
ACCENT_GREEN = "#10b981"
ACCENT_ORANGE = "#f97316"
ACCENT_CYAN = "#22d3ee"

# Create figure
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12), facecolor=BG_OUTER,
                                gridspec_kw={"hspace": 0.28})

for ax in [ax1, ax2]:
    ax.set_facecolor(BG_INNER)
    ax.tick_params(colors="#888", labelsize=10)
    for spine in ax.spines.values():
        spine.set_color(SPINE_COLOR)
    ax.grid(True, color=GRID_COLOR, linewidth=0.5, alpha=0.7)

# ══════════════════════════════════════════════════════════════════════════
# Panel 1: Daily hours with >100% renewable penetration
# ══════════════════════════════════════════════════════════════════════════

# Color by month for seasonal pattern
months = np.array([d.month for d in dates])
month_norm = mcolors.Normalize(vmin=1, vmax=12)

# Use scatter for better visibility of daily data
scatter = ax1.scatter(x_dates, hours_over_100, c=months, cmap='twilight',
                      norm=month_norm, s=12, alpha=0.7, edgecolors="none",
                      rasterized=True)

ax1.set_ylabel("Hours per Day with >100% Renewables", color=ACCENT_GREEN,
               fontsize=13, fontweight="bold")
ax1.tick_params(axis="y", colors=ACCENT_GREEN)
ax1.set_title("California Grid: Daily Renewable Energy Penetration >100% (2020-2025)\n"
              "Hours Each Day When Renewables Exceeded Total Demand",
              color="#fff", fontsize=15, fontweight="bold", pad=15)

# X-axis formatting
ax1.xaxis.set_major_locator(mdates.YearLocator())
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
ax1.xaxis.set_minor_locator(mdates.MonthLocator(bymonth=[4, 7, 10]))
ax1.set_xlim(x_dates[0], x_dates[-1])
ax1.set_ylim(0, max(hours_over_100) * 1.1)

# Colorbar for months
cbar1 = fig.colorbar(scatter, ax=ax1, pad=0.01, aspect=30, fraction=0.015)
cbar1.set_label("Month", fontsize=9, color=TEXT_COLOR)
cbar1.set_ticks([1, 3, 5, 7, 9, 11])
cbar1.set_ticklabels(["Jan", "Mar", "May", "Jul", "Sep", "Nov"])
cbar1.ax.tick_params(colors=TEXT_COLOR, labelsize=8)
cbar1.outline.set_edgecolor(SPINE_COLOR)

# ══════════════════════════════════════════════════════════════════════════
# Panel 2: Daily oversupply and average penetration (dual axis)
# ══════════════════════════════════════════════════════════════════════════

# Left axis: Average oversupply (only when >100%)
line1 = ax2.plot(x_dates, avg_oversupply, color=ACCENT_ORANGE, linewidth=1.0,
                 alpha=0.8, label="Avg Oversupply (when >100%)", zorder=5)
ax2.fill_between(x_dates, 0, avg_oversupply, color=ACCENT_ORANGE, alpha=0.12)
ax2.set_ylabel("Average Oversupply Above 100% (percentage points)",
               color=ACCENT_ORANGE, fontsize=13, fontweight="bold")
ax2.tick_params(axis="y", colors=ACCENT_ORANGE)

# Right axis: Average renewable penetration (all hours)
ax2b = ax2.twinx()
ax2b.set_facecolor("none")

line2 = ax2b.plot(x_dates, avg_penetration, color=ACCENT_CYAN,
                  linewidth=1.0, alpha=0.7,
                  label="Avg Renewable Penetration", zorder=4)
ax2b.set_ylabel("Average Daily Renewable Penetration (%)",
                color=ACCENT_CYAN, fontsize=13, fontweight="bold")
ax2b.tick_params(axis="y", colors=ACCENT_CYAN)
for spine in ax2b.spines.values():
    spine.set_color(SPINE_COLOR)

# X-axis formatting
ax2.xaxis.set_major_locator(mdates.YearLocator())
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
ax2.xaxis.set_minor_locator(mdates.MonthLocator(bymonth=[4, 7, 10]))
ax2.set_xlim(x_dates[0], x_dates[-1])
ax2.set_xlabel("Year", fontsize=12, color="#888", fontweight="bold")

ax2.set_title("Daily Renewable Oversupply and Penetration\n"
              "Excess Energy When Renewables Exceed Demand",
              color="#fff", fontsize=14, fontweight="bold", pad=12)

# Combined legend
lines = line1 + line2
labels = [l.get_label() for l in lines]
ax2.legend(lines, labels, fontsize=11, facecolor=BG_INNER,
           edgecolor=SPINE_COLOR, labelcolor=TEXT_COLOR,
           loc="upper left", framealpha=0.95)

# Align y-axes at 0
ax2.set_ylim(bottom=0)
ax2b.set_ylim(bottom=0)

# Save
out_path = os.path.join(script_dir, "renewable_penetration_daily.png")
fig.savefig(out_path, dpi=200, facecolor=BG_OUTER, bbox_inches="tight")
print(f"Saved to {out_path}")
plt.close()

# Print insights
days_with_over_100 = sum(1 for h in hours_over_100 if h > 0)
total_hours_over_100 = sum(hours_over_100)

print(f"\nKey insights:")
print(f"  Total days analyzed: {len(dates):,}")
print(f"  Days with any hours >100%: {days_with_over_100:,} ({days_with_over_100/len(dates)*100:.1f}%)")
print(f"  Total hours >100%: {total_hours_over_100:,}")

# Find peaks
peak_hours_idx = np.argmax(hours_over_100)
peak_oversupply_idx = np.argmax(avg_oversupply)
peak_penetration_idx = np.argmax(avg_penetration)

print(f"\n  Peak hours in a day: {hours_over_100[peak_hours_idx]} hours on {dates[peak_hours_idx].strftime('%Y-%m-%d')}")
print(f"  Peak avg oversupply: {avg_oversupply[peak_oversupply_idx]:.1f}% on {dates[peak_oversupply_idx].strftime('%Y-%m-%d')}")
print(f"  Peak avg penetration: {avg_penetration[peak_penetration_idx]:.1f}% on {dates[peak_penetration_idx].strftime('%Y-%m-%d')}")

# Yearly summary
yearly_stats = {}
for i, date in enumerate(dates):
    year = date.year
    if year not in yearly_stats:
        yearly_stats[year] = {"days_over_100": 0, "total_hours": 0}
    if hours_over_100[i] > 0:
        yearly_stats[year]["days_over_100"] += 1
    yearly_stats[year]["total_hours"] += hours_over_100[i]

print(f"\n  Yearly statistics:")
for year in sorted(yearly_stats.keys()):
    stats = yearly_stats[year]
    print(f"    {year}: {stats['days_over_100']:3d} days, {stats['total_hours']:4d} hours total")
