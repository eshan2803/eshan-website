"""
Plot renewable energy penetration >100%: hours over 100% and average excess.
Similar style to battery charts.
"""
import json
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

script_dir = os.path.dirname(os.path.abspath(__file__))

# Load data
with open(os.path.join(script_dir, "renewable_penetration_monthly.json")) as f:
    renewable_data = json.load(f)

# Extract monthly data
months = sorted(renewable_data.keys())
hours_over_100 = [renewable_data[m]["hours_over_100"] for m in months]
avg_excess = [renewable_data[m]["avg_excess_pct"] for m in months]
max_penetration = [renewable_data[m]["max_penetration"] for m in months]

month_indices = np.arange(len(months))

# Style constants
BG_OUTER = "#0f1117"
BG_INNER = "#1a1d2e"
TEXT_COLOR = "#e2e8f0"
GRID_COLOR = "#2a2d3e"
SPINE_COLOR = "#3a3d4e"
ACCENT_GREEN = "#10b981"
ACCENT_ORANGE = "#f97316"

# Create figure
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12), facecolor=BG_OUTER,
                                gridspec_kw={"hspace": 0.25})

for ax in [ax1, ax2]:
    ax.set_facecolor(BG_INNER)
    ax.tick_params(colors="#888", labelsize=10)
    for spine in ax.spines.values():
        spine.set_color(SPINE_COLOR)
    ax.grid(True, color=GRID_COLOR, linewidth=0.5, alpha=0.7)

# ══════════════════════════════════════════════════════════════════════════
# Panel 1: Hours with >100% renewable penetration
# ══════════════════════════════════════════════════════════════════════════

# Color bars by year
bar_colors = []
for m in months:
    year = int(m[:4])
    frac = (year - 2020) / 5.0
    bar_colors.append(plt.cm.viridis(frac))

bars = ax1.bar(month_indices, hours_over_100, color=bar_colors, alpha=0.8,
               width=0.8, edgecolor="none")
ax1.set_ylabel("Hours with >100% Renewables", color=ACCENT_GREEN,
               fontsize=13, fontweight="bold")
ax1.tick_params(axis="y", colors=ACCENT_GREEN)
ax1.set_title("California Grid: Renewable Energy Penetration >100% (2020-2025)\n"
              "Hours When Renewables Exceeded Total Demand",
              color="#fff", fontsize=15, fontweight="bold", pad=15)

# X-axis: show January labels only
tick_pos = []
tick_lab = []
for i, m in enumerate(months):
    if m.endswith("-01"):
        tick_pos.append(i)
        tick_lab.append(m[:4])

ax1.set_xticks(tick_pos)
ax1.set_xticklabels(tick_lab, fontsize=11, color="#888")
ax1.set_xlim(-0.5, len(months) - 0.5)

# ══════════════════════════════════════════════════════════════════════════
# Panel 2: Average excess % when >100% (dual axis with max penetration)
# ══════════════════════════════════════════════════════════════════════════

# Left axis: Average excess
line1 = ax2.plot(month_indices, avg_excess, color=ACCENT_ORANGE, linewidth=2.5,
                 marker="o", markersize=4, markerfacecolor=ACCENT_ORANGE,
                 markeredgewidth=0, label="Avg Excess (when >100%)", zorder=5)
ax2.fill_between(month_indices, 0, avg_excess, color=ACCENT_ORANGE, alpha=0.15)
ax2.set_ylabel("Average Excess Above 100% (percentage points)",
               color=ACCENT_ORANGE, fontsize=13, fontweight="bold")
ax2.tick_params(axis="y", colors=ACCENT_ORANGE)

# Right axis: Max penetration
ax2b = ax2.twinx()
ax2b.set_facecolor("none")

line2 = ax2b.plot(month_indices, max_penetration, color=ACCENT_GREEN,
                  linewidth=2.0, linestyle="--", alpha=0.7,
                  label="Peak Penetration", zorder=4)
ax2b.set_ylabel("Peak Monthly Renewable Penetration (%)",
                color=ACCENT_GREEN, fontsize=13, fontweight="bold")
ax2b.tick_params(axis="y", colors=ACCENT_GREEN)
for spine in ax2b.spines.values():
    spine.set_color(SPINE_COLOR)

# X-axis
ax2.set_xticks(tick_pos)
ax2.set_xticklabels(tick_lab, fontsize=11, color="#888")
ax2.set_xlim(-0.5, len(months) - 0.5)
ax2.set_xlabel("Year", fontsize=12, color="#888", fontweight="bold")

ax2.set_title("Renewable Oversupply Intensity\n"
              "How Much Renewables Exceeded Demand During Peak Hours",
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
out_path = os.path.join(script_dir, "renewable_penetration_over_100.png")
fig.savefig(out_path, dpi=200, facecolor=BG_OUTER, bbox_inches="tight")
print(f"Saved to {out_path}")
plt.close()

# Print some insights
print(f"\nKey insights:")
print(f"  Total months analyzed: {len(months)}")
print(f"  Total hours >100% renewables: {sum(hours_over_100):,}")

# Find peaks
peak_hours_idx = np.argmax(hours_over_100)
peak_excess_idx = np.argmax(avg_excess)
peak_penetration_idx = np.argmax(max_penetration)

print(f"\n  Peak hours >100%: {hours_over_100[peak_hours_idx]} hours in {months[peak_hours_idx]}")
print(f"  Peak avg excess: {avg_excess[peak_excess_idx]:.1f}% in {months[peak_excess_idx]}")
print(f"  Peak penetration: {max_penetration[peak_penetration_idx]:.1f}% in {months[peak_penetration_idx]}")

# Yearly totals
yearly_hours = {}
for m, hours in zip(months, hours_over_100):
    year = m[:4]
    yearly_hours[year] = yearly_hours.get(year, 0) + hours

print(f"\n  Yearly hours >100% renewable:")
for year in sorted(yearly_hours.keys()):
    print(f"    {year}: {yearly_hours[year]:4d} hours")
