"""
4-panel daily metrics visualization with month gradient coloring.

All panels colored by month of year using continuous gradient with colorbar legend.

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
import matplotlib.colors as mcolors
from datetime import datetime as dt

script_dir = os.path.dirname(os.path.abspath(__file__))

# Style constants
BG_OUTER = "#0f1117"
BG_INNER = "#1a1d2e"
TEXT_COLOR = "#e2e8f0"
GRID_COLOR = "#2a2d3e"
SPINE_COLOR = "#3a3d4e"

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

# Create figure with 4 panels
fig = plt.figure(figsize=(18, 15), facecolor=BG_OUTER)
gs = fig.add_gridspec(4, 1, height_ratios=[1, 1, 1, 1], hspace=0.3, top=0.94, right=0.92)

# Create axes for panels
axes = [fig.add_subplot(gs[i]) for i in range(4)]

for ax in axes:
    ax.set_facecolor(BG_INNER)
    ax.tick_params(colors="#888", labelsize=10)
    for spine in ax.spines.values():
        spine.set_color(SPINE_COLOR)
    ax.grid(True, color=GRID_COLOR, linewidth=0.5, alpha=0.7)

# Seasonal colormap (cycles through year: blue→green→yellow→orange→red→blue)
def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))

season_anchors = [
    (0.00, hex_to_rgb("#60a5fa")),   # Jan  – winter blue
    (0.17, hex_to_rgb("#34d399")),   # Mar  – spring green
    (0.33, hex_to_rgb("#4ade80")),   # May  – late spring
    (0.50, hex_to_rgb("#facc15")),   # Jul  – summer gold
    (0.67, hex_to_rgb("#f97316")),   # Sep  – early fall orange
    (0.83, hex_to_rgb("#ef4444")),   # Nov  – late fall red
    (1.00, hex_to_rgb("#60a5fa")),   # Dec→Jan wrap
]
sdict = {"red": [], "green": [], "blue": []}
for pos, (r, g, b) in season_anchors:
    sdict["red"].append((pos, r, r))
    sdict["green"].append((pos, g, g))
    sdict["blue"].append((pos, b, b))
month_cmap = mcolors.LinearSegmentedColormap("season", sdict, N=256)
month_norm = mcolors.Normalize(vmin=1, vmax=13)

# Helper function to get month values for coloring
def get_month_values(dates):
    """Return array of month numbers (1-12) for coloring"""
    return np.array([d.month for d in dates])

# Panel 1: Daily hours ≥100% clean energy (gradient by month)
print("Creating Panel 1...")
x1 = mdates.date2num(p1_dates)
month_values_p1 = get_month_values(p1_dates)

scatter1 = axes[0].scatter(x1, p1_hours, c=month_values_p1, cmap=month_cmap, norm=month_norm,
                          s=12, alpha=0.7, edgecolors='none', zorder=3)

axes[0].set_ylabel("Hours per Day", color=TEXT_COLOR, fontsize=12, fontweight="bold")
axes[0].set_title("Daily Hours with ≥100% Clean Energy Penetration",
                  color="#fff", fontsize=14, fontweight="bold", pad=12)
axes[0].set_ylim(0, 24)
axes[0].axhline(24, color="#ffffff", linewidth=1, linestyle="--", alpha=0.5)
axes[0].text(x1[-1], 24.5, "24/7 Goal", color="#fff", fontsize=9, ha='right', alpha=0.7)

# Panel 2: Daily natural gas generation (gradient by month)
print("Creating Panel 2...")
x2 = mdates.date2num(p2_dates)
month_values_p2 = get_month_values(p2_dates)

scatter2 = axes[1].scatter(x2, p2_gas_mw, c=month_values_p2, cmap=month_cmap, norm=month_norm,
                          s=12, alpha=0.7, edgecolors='none', zorder=3)

axes[1].set_ylabel("Natural Gas (MW)", color=TEXT_COLOR, fontsize=12, fontweight="bold")
axes[1].set_title("Daily Average Natural Gas Generation",
                  color="#fff", fontsize=14, fontweight="bold", pad=12)
axes[1].set_ylim(0, max(p2_gas_mw) * 1.1)

# Panel 3: Daily clean energy percentage (gradient by month)
print("Creating Panel 3...")
x3 = mdates.date2num(p3_dates)
month_values_p3 = get_month_values(p3_dates)

scatter3 = axes[2].scatter(x3, p3_clean_pct, c=month_values_p3, cmap=month_cmap, norm=month_norm,
                          s=12, alpha=0.7, edgecolors='none', zorder=3)

axes[2].set_ylabel("Clean Energy (%)", color=TEXT_COLOR, fontsize=12, fontweight="bold")
axes[2].set_title("Daily Clean Energy Penetration (% of Load)",
                  color="#fff", fontsize=14, fontweight="bold", pad=12)
axes[2].set_ylim(0, 100)
axes[2].axhline(100, color="#ffffff", linewidth=1, linestyle="--", alpha=0.5)
axes[2].text(x3[-1], 102, "100%", color="#fff", fontsize=9, ha='right', alpha=0.7)

# Panel 4: Daily peak LMP price (gradient by month)
print("Creating Panel 4...")
x4 = mdates.date2num(p4_dates)
month_values_p4 = get_month_values(p4_dates)

scatter4 = axes[3].scatter(x4, p4_peak_lmp, c=month_values_p4, cmap=month_cmap, norm=month_norm,
                          s=18, alpha=0.7, edgecolors='none')

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

# Add colorbar on the right side
cbar_ax = fig.add_axes([0.93, 0.15, 0.015, 0.7])
sm = plt.cm.ScalarMappable(cmap=month_cmap, norm=month_norm)
sm.set_array([])
cbar = fig.colorbar(sm, cax=cbar_ax)
cbar.set_label("Month of Year", fontsize=12, color=TEXT_COLOR, fontweight="bold")
cbar.set_ticks([1, 3, 5, 7, 9, 11])
cbar.set_ticklabels(['Jan', 'Mar', 'May', 'Jul', 'Sep', 'Nov'])
cbar.ax.tick_params(colors=TEXT_COLOR, labelsize=10)
cbar.outline.set_edgecolor(SPINE_COLOR)

# Overall title
fig.suptitle("California Grid: Daily Metrics Overview",
            color="#fff", fontsize=18, fontweight="bold", y=0.98)

# Save
print("Saving figure...")
out_path = os.path.join(script_dir, "daily_metrics_4panel.png")
fig.savefig(out_path, dpi=200, facecolor=BG_OUTER, bbox_inches="tight")
print(f"Saved to {out_path}")
plt.close()

print("\nVisualization complete!")
