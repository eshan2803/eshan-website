"""
4-panel daily metrics visualization with month-based coloring.

All panels colored by month of year with shared horizontal legend at top.

Panel 1: Daily hours with ≥100% clean energy penetration
Panel 2: Daily natural gas generation (MW)
Panel 3: Daily clean energy percentage
Panel 4: Daily peak LMP price (scatter)
"""
import json
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.cm as cm
from matplotlib.patches import Patch
from datetime import datetime as dt

script_dir = os.path.dirname(os.path.abspath(__file__))

# Style constants
BG_OUTER = "#0f1117"
BG_INNER = "#1a1d2e"
TEXT_COLOR = "#e2e8f0"
GRID_COLOR = "#2a2d3e"
SPINE_COLOR = "#3a3d4e"

# Month color palette (12 distinct colors cycling through the year)
MONTH_COLORS = [
    '#3b82f6',  # Jan - Blue (winter)
    '#60a5fa',  # Feb - Light blue
    '#22d3ee',  # Mar - Cyan (spring begins)
    '#10b981',  # Apr - Green
    '#34d399',  # May - Light green
    '#fbbf24',  # Jun - Yellow (summer begins)
    '#f59e0b',  # Jul - Orange
    '#f97316',  # Aug - Dark orange
    '#ef4444',  # Sep - Red (fall begins)
    '#ec4899',  # Oct - Pink
    '#a855f7',  # Nov - Purple
    '#6366f1',  # Dec - Indigo (winter)
]

MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
               'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

print("Loading data...")

# Load Panel 1 data
with open(os.path.join(script_dir, "renewable_penetration_daily_corrected_full.json")) as f:
    renewable_data = json.load(f)

p1_dates = []
p1_hours = []
for date_str in sorted(renewable_data.keys()):
    p1_dates.append(dt.strptime(date_str, "%Y-%m-%d"))
    p1_hours.append(renewable_data[date_str]["hours_over_100"] / 12.0)

p1_dates = np.array(p1_dates)
p1_hours = np.array(p1_hours)

# Load Panel 2 data
with open(os.path.join(script_dir, "natural_gas_daily.json")) as f:
    gas_data = json.load(f)

p2_dates = []
p2_gas_mw = []
for date_str in sorted(gas_data.keys()):
    p2_dates.append(dt.strptime(date_str, "%Y-%m-%d"))
    p2_gas_mw.append(gas_data[date_str]["avg_gas_mw"])

p2_dates = np.array(p2_dates)
p2_gas_mw = np.array(p2_gas_mw)

# Load Panel 3 data
with open(os.path.join(script_dir, "renewable_penetration_daily_corrected_full.json")) as f:
    energy_data = json.load(f)

p3_dates = []
p3_clean_pct = []
for date_str in sorted(energy_data.keys()):
    p3_dates.append(dt.strptime(date_str, "%Y-%m-%d"))
    p3_clean_pct.append(energy_data[date_str]["avg_penetration"])

p3_dates = np.array(p3_dates)
p3_clean_pct = np.array(p3_clean_pct)

# Load Panel 4 data
with open(os.path.join(script_dir, "caiso_prices.json")) as f:
    price_data = json.load(f)

p4_dates = []
p4_peak_lmp = []
for date_str in sorted(price_data.keys()):
    hourly_prices = price_data[date_str]
    lmp_values = [hourly_prices[str(h)]["LMP"] for h in hourly_prices.keys()]
    if lmp_values:
        peak_lmp = max(lmp_values)
        p4_dates.append(dt.strptime(date_str, "%Y-%m-%d"))
        p4_peak_lmp.append(peak_lmp)

p4_dates = np.array(p4_dates)
p4_peak_lmp = np.array(p4_peak_lmp)

print(f"Loaded data for {len(p1_dates)} days")

# Create figure with 4 panels + space for legend at top
fig = plt.figure(figsize=(18, 15), facecolor=BG_OUTER)
gs = fig.add_gridspec(5, 1, height_ratios=[0.3, 1, 1, 1, 1], hspace=0.4, top=0.96)

# Create axes for panels
axes = [fig.add_subplot(gs[i+1]) for i in range(4)]

for ax in axes:
    ax.set_facecolor(BG_INNER)
    ax.tick_params(colors="#888", labelsize=10)
    for spine in ax.spines.values():
        spine.set_color(SPINE_COLOR)
    ax.grid(True, color=GRID_COLOR, linewidth=0.5, alpha=0.7)

# Helper function to get month colors
def get_month_colors(dates):
    """Return array of colors based on month"""
    return [MONTH_COLORS[d.month - 1] for d in dates]

# Panel 1: Daily hours ≥100% clean energy (colored by month)
print("Creating Panel 1...")
x1 = mdates.date2num(p1_dates)
month_colors_p1 = get_month_colors(p1_dates)

# Plot as scatter with connecting lines
axes[0].scatter(x1, p1_hours, c=month_colors_p1, s=8, alpha=0.8, edgecolors='none', zorder=3)

# Add subtle line connecting points
for month in range(1, 13):
    mask = np.array([d.month == month for d in p1_dates])
    if mask.any():
        axes[0].plot(x1[mask], p1_hours[mask], color=MONTH_COLORS[month-1],
                    linewidth=0.5, alpha=0.3, zorder=2)

axes[0].set_ylabel("Hours per Day", color=TEXT_COLOR, fontsize=12, fontweight="bold")
axes[0].set_title("Daily Hours with ≥100% Clean Energy Penetration",
                  color="#fff", fontsize=14, fontweight="bold", pad=12)
axes[0].set_ylim(0, 24)
axes[0].axhline(24, color="#ffffff", linewidth=1, linestyle="--", alpha=0.5)
axes[0].text(x1[-1], 24.5, "24/7 Goal", color="#fff", fontsize=9, ha='right', alpha=0.7)

# Panel 2: Daily natural gas generation (colored by month)
print("Creating Panel 2...")
x2 = mdates.date2num(p2_dates)
month_colors_p2 = get_month_colors(p2_dates)

axes[1].scatter(x2, p2_gas_mw, c=month_colors_p2, s=8, alpha=0.8, edgecolors='none', zorder=3)

for month in range(1, 13):
    mask = np.array([d.month == month for d in p2_dates])
    if mask.any():
        axes[1].plot(x2[mask], p2_gas_mw[mask], color=MONTH_COLORS[month-1],
                    linewidth=0.5, alpha=0.3, zorder=2)

axes[1].set_ylabel("Natural Gas (MW)", color=TEXT_COLOR, fontsize=12, fontweight="bold")
axes[1].set_title("Daily Average Natural Gas Generation",
                  color="#fff", fontsize=14, fontweight="bold", pad=12)
axes[1].set_ylim(0, max(p2_gas_mw) * 1.1)

# Panel 3: Daily clean energy percentage (colored by month)
print("Creating Panel 3...")
x3 = mdates.date2num(p3_dates)
month_colors_p3 = get_month_colors(p3_dates)

axes[2].scatter(x3, p3_clean_pct, c=month_colors_p3, s=8, alpha=0.8, edgecolors='none', zorder=3)

for month in range(1, 13):
    mask = np.array([d.month == month for d in p3_dates])
    if mask.any():
        axes[2].plot(x3[mask], p3_clean_pct[mask], color=MONTH_COLORS[month-1],
                    linewidth=0.5, alpha=0.3, zorder=2)

axes[2].set_ylabel("Clean Energy (%)", color=TEXT_COLOR, fontsize=12, fontweight="bold")
axes[2].set_title("Daily Clean Energy Penetration (% of Load)",
                  color="#fff", fontsize=14, fontweight="bold", pad=12)
axes[2].set_ylim(0, 100)
axes[2].axhline(100, color="#ffffff", linewidth=1, linestyle="--", alpha=0.5)
axes[2].text(x3[-1], 102, "100%", color="#fff", fontsize=9, ha='right', alpha=0.7)

# Panel 4: Daily peak LMP price (scatter, colored by month)
print("Creating Panel 4...")
x4 = mdates.date2num(p4_dates)
month_colors_p4 = get_month_colors(p4_dates)

axes[3].scatter(x4, p4_peak_lmp, c=month_colors_p4, s=15, alpha=0.7, edgecolors='none')

axes[3].set_ylabel("Peak LMP ($/MWh)", color=TEXT_COLOR, fontsize=12, fontweight="bold")
axes[3].set_xlabel("Date", color=TEXT_COLOR, fontsize=12, fontweight="bold")
axes[3].set_title("Daily Peak LMP Price",
                  color="#fff", fontsize=14, fontweight="bold", pad=12)

# Cap at 99th percentile for readability
p99 = np.percentile(p4_peak_lmp, 99)
axes[3].set_ylim(0, p99)

# Common x-axis formatting for all panels
for i, ax in enumerate(axes):
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax.set_xlim(x1[0], x1[-1])

    if i < 3:
        ax.tick_params(axis='x', labelbottom=False)

# Create horizontal month legend at top
legend_ax = fig.add_subplot(gs[0])
legend_ax.axis('off')

# Create legend patches for all 12 months
legend_elements = [Patch(facecolor=MONTH_COLORS[i], label=MONTH_NAMES[i])
                   for i in range(12)]

legend = legend_ax.legend(handles=legend_elements, loc='center', ncol=12,
                         fontsize=11, framealpha=0.9, facecolor=BG_INNER,
                         edgecolor=SPINE_COLOR, labelcolor=TEXT_COLOR,
                         title='Month', title_fontsize=12)
legend.get_title().set_color(TEXT_COLOR)

# Overall title
fig.suptitle("California Grid: Daily Metrics Overview",
            color="#fff", fontsize=18, fontweight="bold", y=0.985)

# Save
print("Saving figure...")
out_path = os.path.join(script_dir, "daily_metrics_4panel.png")
fig.savefig(out_path, dpi=200, facecolor=BG_OUTER, bbox_inches="tight")
print(f"Saved to {out_path}")
plt.close()

print("\nVisualization complete!")
