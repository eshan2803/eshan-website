"""
4-panel daily metrics visualization.

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
from datetime import datetime as dt

script_dir = os.path.dirname(os.path.abspath(__file__))

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

print("Loading data...")

# ══════════════════════════════════════════════════════════════════════════
# Load Panel 1 data: Daily hours ≥100% clean energy
# ══════════════════════════════════════════════════════════════════════════
# Using corrected data with energy-weighted penetration calculation
with open(os.path.join(script_dir, "renewable_penetration_daily_corrected_full.json")) as f:
    renewable_data = json.load(f)

p1_dates = []
p1_hours = []
for date_str in sorted(renewable_data.keys()):
    p1_dates.append(dt.strptime(date_str, "%Y-%m-%d"))
    p1_hours.append(renewable_data[date_str]["hours_over_100"])

p1_dates = np.array(p1_dates)
p1_hours = np.array(p1_hours)

print(f"Panel 1: {len(p1_dates)} days of clean energy hours data")

# ══════════════════════════════════════════════════════════════════════════
# Load Panel 2 data: Daily natural gas generation
# ══════════════════════════════════════════════════════════════════════════
with open(os.path.join(script_dir, "natural_gas_daily.json")) as f:
    gas_data = json.load(f)

p2_dates = []
p2_gas_mw = []
for date_str in sorted(gas_data.keys()):
    p2_dates.append(dt.strptime(date_str, "%Y-%m-%d"))
    p2_gas_mw.append(gas_data[date_str]["avg_gas_mw"])

p2_dates = np.array(p2_dates)
p2_gas_mw = np.array(p2_gas_mw)

print(f"Panel 2: {len(p2_dates)} days of natural gas data")

# ══════════════════════════════════════════════════════════════════════════
# Load Panel 3 data: Daily clean energy percentage
# ══════════════════════════════════════════════════════════════════════════
# Use corrected renewable penetration data (Clean / Load, not supply mix)
with open(os.path.join(script_dir, "renewable_penetration_daily_corrected_full.json")) as f:
    energy_data = json.load(f)

p3_dates = []
p3_clean_pct = []
for date_str in sorted(energy_data.keys()):
    p3_dates.append(dt.strptime(date_str, "%Y-%m-%d"))
    p3_clean_pct.append(energy_data[date_str]["avg_penetration"])

p3_dates = np.array(p3_dates)
p3_clean_pct = np.array(p3_clean_pct)

print(f"Panel 3: {len(p3_dates)} days of clean energy % data")

# ══════════════════════════════════════════════════════════════════════════
# Load Panel 4 data: Daily peak LMP price
# ══════════════════════════════════════════════════════════════════════════
with open(os.path.join(script_dir, "caiso_prices.json")) as f:
    price_data = json.load(f)

p4_dates = []
p4_peak_lmp = []
for date_str in sorted(price_data.keys()):
    hourly_prices = price_data[date_str]
    # Handle daylight saving time transitions - only use available hours
    lmp_values = [hourly_prices[str(h)]["LMP"] for h in hourly_prices.keys()]
    if lmp_values:  # Only add if we have data
        peak_lmp = max(lmp_values)
        p4_dates.append(dt.strptime(date_str, "%Y-%m-%d"))
        p4_peak_lmp.append(peak_lmp)

p4_dates = np.array(p4_dates)
p4_peak_lmp = np.array(p4_peak_lmp)

print(f"Panel 4: {len(p4_dates)} days of LMP price data")

# ══════════════════════════════════════════════════════════════════════════
# Create figure with 4 panels
# ══════════════════════════════════════════════════════════════════════════
fig = plt.figure(figsize=(18, 14), facecolor=BG_OUTER)
gs = fig.add_gridspec(4, 1, hspace=0.35)

axes = [fig.add_subplot(gs[i]) for i in range(4)]

for ax in axes:
    ax.set_facecolor(BG_INNER)
    ax.tick_params(colors="#888", labelsize=10)
    for spine in ax.spines.values():
        spine.set_color(SPINE_COLOR)
    ax.grid(True, color=GRID_COLOR, linewidth=0.5, alpha=0.7)

# ══════════════════════════════════════════════════════════════════════════
# Panel 1: Daily hours ≥100% clean energy
# ══════════════════════════════════════════════════════════════════════════
print("Creating Panel 1...")
x1 = mdates.date2num(p1_dates)
axes[0].fill_between(x1, 0, p1_hours, color=ACCENT_GREEN, alpha=0.6, linewidth=0)
axes[0].plot(x1, p1_hours, color=ACCENT_GREEN, linewidth=1.5, alpha=0.9)

axes[0].set_ylabel("Hours per Day", color=TEXT_COLOR, fontsize=12, fontweight="bold")
axes[0].set_title("Daily Hours with ≥100% Clean Energy Penetration",
                  color="#fff", fontsize=14, fontweight="bold", pad=12)
axes[0].set_ylim(0, 24)
axes[0].axhline(24, color="#ffffff", linewidth=1, linestyle="--", alpha=0.5)
axes[0].text(x1[-1], 24.5, "24/7 Goal", color="#fff", fontsize=9, ha='right', alpha=0.7)

# ══════════════════════════════════════════════════════════════════════════
# Panel 2: Daily natural gas generation
# ══════════════════════════════════════════════════════════════════════════
print("Creating Panel 2...")
x2 = mdates.date2num(p2_dates)
axes[1].fill_between(x2, 0, p2_gas_mw, color=ACCENT_ORANGE, alpha=0.6, linewidth=0)
axes[1].plot(x2, p2_gas_mw, color=ACCENT_ORANGE, linewidth=1.5, alpha=0.9)

axes[1].set_ylabel("Natural Gas (MW)", color=TEXT_COLOR, fontsize=12, fontweight="bold")
axes[1].set_title("Daily Average Natural Gas Generation",
                  color="#fff", fontsize=14, fontweight="bold", pad=12)
axes[1].set_ylim(0, max(p2_gas_mw) * 1.1)

# ══════════════════════════════════════════════════════════════════════════
# Panel 3: Daily clean energy percentage
# ══════════════════════════════════════════════════════════════════════════
print("Creating Panel 3...")
x3 = mdates.date2num(p3_dates)
axes[2].fill_between(x3, 0, p3_clean_pct, color=ACCENT_CYAN, alpha=0.6, linewidth=0)
axes[2].plot(x3, p3_clean_pct, color=ACCENT_CYAN, linewidth=1.5, alpha=0.9)

axes[2].set_ylabel("Clean Energy (%)", color=TEXT_COLOR, fontsize=12, fontweight="bold")
axes[2].set_title("Daily Clean Energy Penetration (% of Load)",
                  color="#fff", fontsize=14, fontweight="bold", pad=12)
axes[2].set_ylim(0, 100)
axes[2].axhline(100, color="#ffffff", linewidth=1, linestyle="--", alpha=0.5)
axes[2].text(x3[-1], 102, "100%", color="#fff", fontsize=9, ha='right', alpha=0.7)

# ══════════════════════════════════════════════════════════════════════════
# Panel 4: Daily peak LMP price (scatter)
# ══════════════════════════════════════════════════════════════════════════
print("Creating Panel 4...")
x4 = mdates.date2num(p4_dates)

# Color by season (month)
months = np.array([d.month for d in p4_dates])
season_colors = []
for m in months:
    if m in [12, 1, 2]:  # Winter
        season_colors.append('#60a5fa')  # Blue
    elif m in [3, 4, 5]:  # Spring
        season_colors.append('#10b981')  # Green
    elif m in [6, 7, 8]:  # Summer
        season_colors.append('#f97316')  # Orange
    else:  # Fall
        season_colors.append('#a855f7')  # Purple

axes[3].scatter(x4, p4_peak_lmp, c=season_colors, s=15, alpha=0.7, edgecolors='none')

axes[3].set_ylabel("Peak LMP ($/MWh)", color=TEXT_COLOR, fontsize=12, fontweight="bold")
axes[3].set_xlabel("Date", color=TEXT_COLOR, fontsize=12, fontweight="bold")
axes[3].set_title("Daily Peak LMP Price (colored by season)",
                  color="#fff", fontsize=14, fontweight="bold", pad=12)

# Cap at 99th percentile for readability
p99 = np.percentile(p4_peak_lmp, 99)
axes[3].set_ylim(0, p99)

# Add legend for seasons
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor='#60a5fa', label='Winter'),
    Patch(facecolor='#10b981', label='Spring'),
    Patch(facecolor='#f97316', label='Summer'),
    Patch(facecolor='#a855f7', label='Fall')
]
axes[3].legend(handles=legend_elements, loc='upper left', fontsize=9,
              framealpha=0.8, facecolor=BG_INNER, edgecolor=SPINE_COLOR,
              labelcolor=TEXT_COLOR)

# ══════════════════════════════════════════════════════════════════════════
# Common x-axis formatting for all panels
# ══════════════════════════════════════════════════════════════════════════
for i, ax in enumerate(axes):
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax.set_xlim(x1[0], x1[-1])

    # Only show x-axis label on bottom panel
    if i < 3:
        ax.tick_params(axis='x', labelbottom=False)

# Overall title
fig.suptitle("California Grid: Daily Metrics Overview",
            color="#fff", fontsize=18, fontweight="bold", y=0.995)

# Save
print("Saving figure...")
out_path = os.path.join(script_dir, "daily_metrics_4panel.png")
fig.savefig(out_path, dpi=200, facecolor=BG_OUTER, bbox_inches="tight")
print(f"Saved to {out_path}")
plt.close()

print("\nVisualization complete!")
