"""
Battery discharge window expansion visualization (2-panel).

Panel 1: Heatmap — Date (x) vs 5-min interval (y), color = battery discharge MW
         Shows both capacity growth and widening discharge window over time.
Panel 2: Calendar heatmap — yearly strips, color = total minutes of discharge per day
         Shows the growing duration of daily battery discharge over the years.

Reads from caiso_comprehensive_data.csv (5-minute intervals, 2020-2026).
"""
import csv
import os
import calendar
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.dates as mdates
from datetime import datetime as dt
from collections import defaultdict

script_dir = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(script_dir, "caiso_comprehensive_data.csv")

# ── Read CSV at 5-min resolution ──
print("Reading comprehensive CSV...")
# Structure: { "2020-01-01": { (hour, minute): mw, ... }, ... }
daily_5min = defaultdict(dict)

with open(CSV_FILE, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    count = 0
    for row in reader:
        ts = row["timestamp"]
        discharge = row.get("battery_discharging_mw", "")
        if not discharge or not discharge.strip():
            continue
        try:
            val = float(discharge)
        except (ValueError, TypeError):
            continue

        # Parse timestamp
        try:
            if "-" in ts.split(" ")[0]:
                parsed = dt.strptime(ts, "%Y-%m-%d %H:%M")
            else:
                parsed = dt.strptime(ts, "%m/%d/%Y %H:%M")
        except ValueError:
            continue

        date_key = parsed.strftime("%Y-%m-%d")
        # 5-min slot index: 0..287
        slot = parsed.hour * 12 + parsed.minute // 5
        daily_5min[date_key][slot] = val
        count += 1

        if count % 500000 == 0:
            print(f"  Read {count:,} rows...")

print(f"  Total: {count:,} rows across {len(daily_5min)} days")

# ── Build 5-min heatmap matrix ──
print("Building 5-min heatmap...")
dates_sorted = sorted(daily_5min.keys())
date_objs = [dt.strptime(d, "%Y-%m-%d") for d in dates_sorted]
n_days = len(dates_sorted)
N_SLOTS = 288  # 24 * 12

# Raw discharge matrix: rows = 288 slots, cols = days
raw = np.full((N_SLOTS, n_days), np.nan)

for j, date_key in enumerate(dates_sorted):
    for slot, mw in daily_5min[date_key].items():
        if 0 <= slot < N_SLOTS:
            raw[slot, j] = mw

# Use raw MW values directly (no normalization)
heatmap = raw
print(f"  Heatmap shape: {heatmap.shape}")

# ── Compute daily discharge minutes ──
print("Computing daily discharge minutes...")
# Minimum 100 MW threshold to filter out noise-level discharge in early years
# (2020 avg peak was ~117 MW with lots of 1-10 MW trickle; 2024+ peaks are 5000+ MW)
MIN_DISCHARGE_MW = 100
daily_discharge_minutes = {}

for date_key, slots in daily_5min.items():
    intervals_discharging = sum(1 for mw in slots.values() if mw > MIN_DISCHARGE_MW)
    daily_discharge_minutes[date_key] = intervals_discharging * 5  # 5 min per interval

# ── Style ──
BG_OUTER = "#0f1117"
BG_INNER = "#1a1d2e"
TEXT_COLOR = "#e2e8f0"
GRID_COLOR = "#2a2d3e"
SPINE_COLOR = "#3a3d4e"

YEAR_COLORS = {
    2020: "#94a3b8",  # slate
    2021: "#60a5fa",  # blue
    2022: "#34d399",  # green
    2023: "#a78bfa",  # purple
    2024: "#fbbf24",  # amber
    2025: "#f97316",  # orange
    2026: "#ef4444",  # red
}

# ── Figure ──
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 13), facecolor=BG_OUTER,
                                 gridspec_kw={"hspace": 0.35, "height_ratios": [1.3, 1]})

last_date_label = dt.strptime(dates_sorted[-1], "%Y-%m-%d").strftime("%B %d, %Y")

# ═══════════ Panel 1: Normalized 5-min Heatmap ═══════════
print("Creating Panel 1: Normalized 5-min heatmap...")
ax1.set_facecolor(BG_INNER)

x_dates = mdates.date2num(date_objs)

# Colormap: background -> blue -> cyan -> amber -> white
cmap = mcolors.LinearSegmentedColormap.from_list("battery", [
    "#1a1d2e",   # background (0%)
    "#1e3a5f",   # dark blue
    "#2563eb",   # blue
    "#06b6d4",   # cyan
    "#fbbf24",   # amber
    "#ffffff",   # white (100% of peak)
])
cmap.set_bad(BG_INNER)  # NaN days show as background

vmax = np.nanpercentile(heatmap, 99.5)
norm = mcolors.Normalize(vmin=0, vmax=vmax)

# Edges for pcolormesh
x_edges = np.append(x_dates, x_dates[-1] + 1)
y_edges = np.arange(N_SLOTS + 1)  # 0..288

im = ax1.pcolormesh(x_edges, y_edges, heatmap, cmap=cmap, norm=norm,
                     shading="flat", rasterized=True)

ax1.set_ylabel("Hour of Day", color=TEXT_COLOR, fontsize=12, fontweight="bold")
ax1.set_ylim(0, N_SLOTS)
# Tick at every 3 hours (3 * 12 = 36 slots)
hour_ticks = [h * 12 for h in [0, 3, 6, 9, 12, 15, 18, 21, 24]]
ax1.set_yticks(hour_ticks)
ax1.set_yticklabels(["12am", "3am", "6am", "9am", "12pm", "3pm", "6pm", "9pm", "12am"],
                     fontsize=10)
ax1.invert_yaxis()

ax1.xaxis.set_major_locator(mdates.YearLocator())
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
ax1.set_xlim(x_dates[0], x_dates[-1])

# --- ADDED OVERLAY START ---
daily_gwh = []
for j in range(heatmap.shape[1]):
    gwh = np.nansum(heatmap[:, j]) / 12.0 / 1000.0
    daily_gwh.append(gwh)

ax1_twin = ax1.twinx()
window = 14
padded_gwh = np.pad(daily_gwh, (window//2, window-1-window//2), mode='edge')
smoothed_gwh = np.convolve(padded_gwh, np.ones(window)/window, mode='valid')

ax1_twin.plot(x_dates, daily_gwh, color="#ec4899", alpha=0.3, linewidth=0.5)
ax1_twin.plot(x_dates, smoothed_gwh, color="#ec4899", alpha=1.0, linewidth=1.5, label="Total Discharge")

ax1_twin.set_ylabel("Total Daily Discharge (GWh)", color="#ec4899", fontsize=11, fontweight="bold")
ax1_twin.set_ylim(0, max(daily_gwh) * 1.1)
ax1_twin.tick_params(axis='y', colors="#ec4899", labelsize=10)
for spine in ax1_twin.spines.values():
    spine.set_color(SPINE_COLOR)
ax1_twin.spines["right"].set_color("#ec4899")
# --- ADDED OVERLAY END ---

ax1.set_title(f"California Grid: Battery Discharge Window Expansion\n"
              f"5-Minute Resolution — Updated through {last_date_label}",
              color="#fff", fontsize=14, fontweight="bold", pad=12)

ax1.tick_params(colors="#888", labelsize=10)
for spine in ax1.spines.values():
    spine.set_color(SPINE_COLOR)

# Colorbar (padded strongly to avoid overlapping twinx)
cbar = fig.colorbar(im, ax=ax1, orientation="vertical", pad=0.08,
                     aspect=20, fraction=0.03)
cbar.set_label("Discharge (MW)", fontsize=10, color=TEXT_COLOR)
cbar.ax.tick_params(colors=TEXT_COLOR, labelsize=9)
cbar.outline.set_edgecolor(SPINE_COLOR)

# ═══════════ Panel 2: Calendar Heatmap — Discharge Minutes ═══════════
print("Creating Panel 2: Calendar heatmap of discharge minutes...")
ax2.set_facecolor(BG_INNER)

years = range(2020, 2027)
n_years = len(years)

strip_height = 0.8
gap = 0.2
y_positions = np.arange(n_years) * (strip_height + gap)

# Colormap: background -> cyan -> amber -> white
cmap2 = mcolors.LinearSegmentedColormap.from_list("discharge_min", [
    "#1a1d2e",   # 0 min
    "#1e3a5f",   # dark blue
    "#06b6d4",   # cyan
    "#fbbf24",   # amber
    "#ef4444",   # red
    "#ffffff",   # white (24h = 1440 min)
])
max_minutes = 24 * 60  # 1440
norm2 = mcolors.Normalize(vmin=0, vmax=max_minutes)

# Yearly averages for annotation
yearly_avg_minutes = {}

for i, year in enumerate(years):
    year_days = []
    year_minutes = []

    for date_key, minutes in sorted(daily_discharge_minutes.items()):
        if date_key.startswith(str(year)):
            d = dt.strptime(date_key, "%Y-%m-%d")
            day_of_year = d.timetuple().tm_yday
            year_days.append(day_of_year)
            year_minutes.append(minutes)

    if year_days:
        yearly_avg_minutes[year] = np.mean(year_minutes)
        for day, minutes in zip(year_days, year_minutes):
            color = cmap2(norm2(minutes))
            ax2.barh(y_positions[i], 1, left=day - 0.5, height=strip_height,
                     color=color, edgecolor=BG_INNER, linewidth=0.3)

# Year labels with average hours
ax2.set_yticks(y_positions + strip_height / 2)
ylabels = []
for year in years:
    avg = yearly_avg_minutes.get(year, 0)
    avg_hours = avg / 60
    ylabels.append(f"{year}  ({avg_hours:.1f}h avg)")
ax2.set_yticklabels(ylabels, fontsize=10, color=TEXT_COLOR)

ax2.set_xlabel("Day of Year", fontsize=12, color="#888", fontweight="bold")
ax2.set_xlim(0, 366)
ax2.set_ylim(-0.2, n_years * (strip_height + gap))

ax2.set_title("Daily Battery Discharge Duration\n"
              "Each Strip = One Year, Color = Minutes Discharging Per Day",
              color="#fff", fontsize=13, fontweight="bold", pad=12)

# Month markers
month_days = [0]
for m in range(1, 13):
    month_days.append(month_days[-1] + calendar.monthrange(2024, m)[1])
month_centers = [(month_days[i] + month_days[i + 1]) / 2 for i in range(12)]
ax2.set_xticks(month_centers)
ax2.set_xticklabels(["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
                     fontsize=9, color="#888")

for day in month_days[1:-1]:
    ax2.axvline(day, color=SPINE_COLOR, linewidth=0.5, alpha=0.5)

# Colorbar (padded)
sm = plt.cm.ScalarMappable(cmap=cmap2, norm=norm2)
sm.set_array([])
cbar2 = fig.colorbar(sm, ax=ax2, orientation="vertical", pad=0.08,
                      aspect=20, fraction=0.03)
cbar2.set_label("Minutes Discharging", fontsize=10, color=TEXT_COLOR)
cbar2.set_ticks([0, 360, 720, 1080, 1440])
cbar2.set_ticklabels(["0", "6h", "12h", "18h", "24h"])
cbar2.ax.tick_params(colors=TEXT_COLOR, labelsize=9)
cbar2.outline.set_edgecolor(SPINE_COLOR)

ax2.grid(False)
for spine in ax2.spines.values():
    spine.set_color(SPINE_COLOR)

# ── Save ──
print("Saving figure...")
out_path = os.path.join(script_dir, "battery_discharge_window.png")
fig.savefig(out_path, dpi=200, facecolor=BG_OUTER, bbox_inches="tight")
print(f"Saved to {out_path}")
plt.close()

print("\nDone!")
