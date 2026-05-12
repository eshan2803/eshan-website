"""
Peak LMP time-of-day shift chart (3-panel).

Panel 1: x = date, y = daily peak LMP ($/MWh), color = hour of day
Panel 2: Battery Discharge heatmap
Panel 3: Heatmap — x = month, y = hour, color = count of days with peak at that hour

Uses hourly LMP data (caiso_prices.json) for complete coverage (2023-2026),
supplemented by 5-min data (caiso_prices_5min.json) where available.
"""
import json
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.dates as mdates
from datetime import datetime as dt, timedelta, time
import csv
from collections import defaultdict
from zoneinfo import ZoneInfo

script_dir = os.path.dirname(os.path.abspath(__file__))
CAISO_TZ = ZoneInfo("America/Los_Angeles")
UTC_TZ = ZoneInfo("UTC")


def expected_lmp_intervals(date_obj):
    start_local = dt.combine(date_obj.date(), time.min, CAISO_TZ)
    end_local = dt.combine(date_obj.date() + timedelta(days=1), time.min, CAISO_TZ)
    return min(int((end_local.astimezone(UTC_TZ) - start_local.astimezone(UTC_TZ)).total_seconds() // 300), 288)

# ── Read battery discharge data from CSV at 5-min resolution ──
print("Reading comprehensive CSV for battery window...")
CSV_FILE = os.path.join(script_dir, "caiso_comprehensive_data.csv")
daily_5min = defaultdict(dict)
count = 0

with open(CSV_FILE, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        ts = row["timestamp"]
        discharge = row.get("battery_discharging_mw", "")
        if not discharge or not discharge.strip():
            continue
        try:
            val = float(discharge)
        except (ValueError, TypeError):
            continue
        try:
            if "-" in ts.split(" ")[0]:
                parsed = dt.strptime(ts, "%Y-%m-%d %H:%M")
            else:
                parsed = dt.strptime(ts, "%m/%d/%Y %H:%M")
        except ValueError:
            continue
        date_key = parsed.strftime("%Y-%m-%d")
        slot = parsed.hour * 12 + parsed.minute // 5
        daily_5min[date_key][slot] = val
        count += 1
        if count % 500000 == 0:
            print(f"  Read {count:,} rows...")

batt_dates_sorted = sorted(daily_5min.keys())
batt_date_objs = [dt.strptime(d, "%Y-%m-%d") for d in batt_dates_sorted]
batt_n_days = len(batt_dates_sorted)
batt_N_SLOTS = 288
batt_heatmap = np.full((batt_N_SLOTS, batt_n_days), np.nan)
for j, date_key in enumerate(batt_dates_sorted):
    for slot, mw in daily_5min[date_key].items():
        if 0 <= slot < batt_N_SLOTS:
            batt_heatmap[slot, j] = mw

print(f"  Battery heatmap shape: {batt_heatmap.shape}")


# ── Read both LMP data sources ──
print("Reading LMP data...")

with open(os.path.join(script_dir, "caiso_prices.json"), "r") as f:
    hourly_prices = json.load(f)

prices_5min_path = os.path.join(script_dir, "caiso_prices_5min.json")
fivemin_prices = {}
if os.path.exists(prices_5min_path):
    with open(prices_5min_path, "r") as f:
        fivemin_prices = json.load(f)

# ── Find daily peaks, preferring 5-min resolution ──
dates = []
peak_lmps = []
peak_hours = []  # integer hour (0-23)
peak_hours_frac = []  # fractional hour for scatter

for date_str in sorted(set(list(hourly_prices.keys()) + list(fivemin_prices.keys()))):
    try:
        parsed = dt.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        continue

    if parsed.year < 2020:
        continue

    max_lmp = -9999
    max_frac_hour = -1

    if date_str in fivemin_prices and len(fivemin_prices[date_str]) >= expected_lmp_intervals(parsed):
        day = fivemin_prices[date_str]
        for time_str, comps in day.items():
            lmp = comps.get("LMP", None)
            if lmp is None:
                continue
            if lmp > max_lmp:
                max_lmp = lmp
                parts = time_str.split(":")
                max_frac_hour = int(parts[0]) + int(parts[1]) / 60.0
    elif date_str in hourly_prices:
        day = hourly_prices[date_str]
        for hour_str, comps in day.items():
            lmp = comps.get("LMP", None)
            if lmp is None:
                continue
            if lmp > max_lmp:
                max_lmp = lmp
                max_frac_hour = float(int(hour_str) - 1) + 0.5

    if max_lmp <= -9999 or max_frac_hour < 0:
        continue

    dates.append(parsed)
    peak_lmps.append(max_lmp)
    peak_hours.append(int(max_frac_hour))
    peak_hours_frac.append(max_frac_hour)

print(f"  Found {len(dates)} days with peak LMP data")
print(f"  Date range: {dates[0].strftime('%Y-%m-%d')} to {dates[-1].strftime('%Y-%m-%d')}")

dates = np.array(dates)
peak_lmps = np.array(peak_lmps)
peak_hours = np.array(peak_hours)
peak_hours_frac = np.array(peak_hours_frac)

# ── Style ──
BG_OUTER = "#0f1117"
BG_INNER = "#1a1d2e"
TEXT_COLOR = "#e2e8f0"
GRID_COLOR = "#2a2d3e"
SPINE_COLOR = "#3a3d4e"

HOUR_CMAP = mcolors.LinearSegmentedColormap.from_list("hour_of_day", [
    (0/24, "#1e3a5f"),
    (4/24, "#2563eb"),
    (7/24, "#fbbf24"),
    (10/24, "#f97316"),
    (13/24, "#ef4444"),
    (16/24, "#dc2626"),
    (18/24, "#a855f7"),
    (21/24, "#6366f1"),
    (24/24, "#1e3a5f"),
])
hour_norm = mcolors.Normalize(vmin=0, vmax=24)

# Heatmap colormap
heat_cmap = mcolors.LinearSegmentedColormap.from_list("heatcount", [
    "#1a1d2e", "#1e3a5f", "#2563eb", "#06b6d4", "#fbbf24", "#ef4444", "#ffffff"
])

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

YEARS = [2020, 2021, 2022, 2023, 2024, 2025, 2026]

# ── Figure: 3 panels ──
fig, (ax1, ax_batt, ax2) = plt.subplots(3, 1, figsize=(22, 21), facecolor=BG_OUTER,
                                 gridspec_kw={"hspace": 0.35, "height_ratios": [0.8, 1.0, 1.2]})

last_date_label = dates[-1].strftime("%B %d, %Y")
date_nums = mdates.date2num(dates)

# ═══════════ Panel 1: Peak LMP scatter, color = hour ═══════════
ax1.set_facecolor(BG_INNER)

sort_idx = np.argsort(peak_lmps)
sc1 = ax1.scatter(
    date_nums[sort_idx], peak_lmps[sort_idx],
    c=peak_hours_frac[sort_idx], cmap=HOUR_CMAP, norm=hour_norm,
    s=28, alpha=0.75, edgecolors="none", rasterized=True,
)

ax1.set_ylabel("Daily Peak LMP ($/MWh)", color=TEXT_COLOR, fontsize=12, fontweight="bold")
ax1.set_ylim(-10, min(1200, np.percentile(peak_lmps, 99.5) * 1.2))
ax1.axhline(0, color=SPINE_COLOR, linewidth=0.5)

for year in [2021, 2022, 2023, 2024, 2025, 2026]:
    jan1 = mdates.date2num(dt(year, 1, 1))
    ax1.axvline(jan1, color="#888", linewidth=0.8, linestyle="--", alpha=0.5)

ax1.grid(True, axis="y", color=GRID_COLOR, linewidth=0.5, alpha=0.5)
ax1.grid(True, axis="x", color=GRID_COLOR, linewidth=0.5, alpha=0.3)
ax1.tick_params(colors="#888", labelsize=10)
for spine in ax1.spines.values():
    spine.set_color(SPINE_COLOR)

ax1.xaxis.set_major_locator(mdates.YearLocator())
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
ax1.set_xlim(date_nums[0] - 10, date_nums[-1] + 10)

cbar1 = fig.colorbar(sc1, ax=ax1, orientation="vertical", pad=0.08, aspect=25, fraction=0.025)
cbar1.set_label("Hour of Peak", fontsize=10, color=TEXT_COLOR)
cbar1.set_ticks([0, 4, 8, 12, 16, 20, 24])
cbar1.set_ticklabels(["12am", "4am", "8am", "12pm", "4pm", "8pm", "12am"])
cbar1.ax.tick_params(colors=TEXT_COLOR, labelsize=8)
cbar1.outline.set_edgecolor(SPINE_COLOR)

ax1.set_title(f"California Grid: Daily Peak LMP & Time-of-Day Shift\n"
              f"5-Min Resolution — Updated through {last_date_label}",
              color="#fff", fontsize=14, fontweight="bold", pad=12)


# ═══════════ Panel 2 (Battery): Normalized 5-min Heatmap ═══════════
print("Creating Panel 2: Battery discharge heatmap...")
ax_batt.set_facecolor(BG_INNER)

if len(batt_date_objs) > 0:
    batt_x_dates = mdates.date2num(batt_date_objs)
    batt_cmap = mcolors.LinearSegmentedColormap.from_list("battery", [
        "#1a1d2e", "#1e3a5f", "#2563eb", "#06b6d4", "#fbbf24", "#ffffff"
    ])
    batt_cmap.set_bad(BG_INNER)
    batt_vmax = np.nanpercentile(batt_heatmap, 99.5)
    batt_norm = mcolors.Normalize(vmin=0, vmax=batt_vmax)
    
    batt_x_edges = np.append(batt_x_dates, batt_x_dates[-1] + 1)
    batt_y_edges = np.arange(batt_N_SLOTS + 1)
    
    im_batt = ax_batt.pcolormesh(batt_x_edges, batt_y_edges, batt_heatmap, cmap=batt_cmap, norm=batt_norm,
                         shading="flat", rasterized=True)
    
    ax_batt.set_xlim(date_nums[0] - 10, date_nums[-1] + 10)
    
    cbar_batt = fig.colorbar(im_batt, ax=ax_batt, orientation="vertical", pad=0.08, aspect=20, fraction=0.03)
    cbar_batt.set_label("Discharge (MW)", fontsize=10, color=TEXT_COLOR)
    cbar_batt.ax.tick_params(colors=TEXT_COLOR, labelsize=9)
    cbar_batt.outline.set_edgecolor(SPINE_COLOR)

ax_batt.set_ylabel("Hour of Day\n(Battery Discharge)", color=TEXT_COLOR, fontsize=12, fontweight="bold")
ax_batt.set_ylim(0, batt_N_SLOTS)
hour_ticks = [h * 12 for h in [0, 3, 6, 9, 12, 15, 18, 21, 24]]
ax_batt.set_yticks(hour_ticks)
ax_batt.set_yticklabels(["12am", "3am", "6am", "9am", "12pm", "3pm", "6pm", "9pm", "12am"], fontsize=10)
ax_batt.invert_yaxis()

ax_batt.xaxis.set_major_locator(mdates.YearLocator())
ax_batt.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

# --- ADDED OVERLAY START ---
if len(batt_date_objs) > 0:
    batt_daily_gwh = []
    for j in range(batt_heatmap.shape[1]):
        gwh = np.nansum(batt_heatmap[:, j]) / 12.0 / 1000.0
        batt_daily_gwh.append(gwh)

    ax_batt_twin = ax_batt.twinx()
    window = 14
    padded_batt = np.pad(batt_daily_gwh, (window//2, window-1-window//2), mode='edge')
    smoothed_batt = np.convolve(padded_batt, np.ones(window)/window, mode='valid')

    ax_batt_twin.plot(batt_x_dates, batt_daily_gwh, color="#ec4899", alpha=0.3, linewidth=0.5)
    ax_batt_twin.plot(batt_x_dates, smoothed_batt, color="#ec4899", alpha=1.0, linewidth=1.5, label="Total Discharge")

    ax_batt_twin.set_ylabel("Total Discharge (GWh)", color="#ec4899", fontsize=11, fontweight="bold")
    ax_batt_twin.set_ylim(0, max(batt_daily_gwh) * 1.1)
    ax_batt_twin.tick_params(axis='y', colors="#ec4899", labelsize=10)
    for spine in ax_batt_twin.spines.values():
        spine.set_color(SPINE_COLOR)
    ax_batt_twin.spines["right"].set_color("#ec4899")
# --- ADDED OVERLAY END ---


batt_last_date = dt.strptime(batt_dates_sorted[-1], "%Y-%m-%d").strftime("%B %d, %Y") if len(batt_dates_sorted) > 0 else ""
ax_batt.set_title(f"California Grid: Battery Discharge Window Expansion (5-Min Data)",
              color="#fff", fontsize=14, fontweight="bold", pad=12)

ax_batt.tick_params(colors="#888", labelsize=10)
for spine in ax_batt.spines.values():
    spine.set_color(SPINE_COLOR)


# ═══════════ Panel 3: Heatmap — Month × Hour, one sub-panel per year ═══════════

# Build count grids: for each year, 12 months × 24 hours
n_years = len(YEARS)
grids = {}
for year in YEARS:
    grid = np.zeros((24, 12))  # rows=hours 0-23, cols=months 0-11
    mask = np.array([d.year == year for d in dates])
    for d, h in zip(dates[mask], peak_hours[mask]):
        month_idx = d.month - 1
        grid[h, month_idx] += 1
    grids[year] = grid

# Find global max for consistent colorbar
global_max = max(g.max() for g in grids.values())

# Create sub-axes within ax2's position
ax2.set_visible(False)
pos = ax2.get_position()

gap = 0.02
panel_width = (pos.width - gap * (n_years - 1)) / n_years

sub_axes = []
for i, year in enumerate(YEARS):
    left = pos.x0 + i * (panel_width + gap)
    sub_ax = fig.add_axes([left, pos.y0, panel_width, pos.height])
    sub_ax.set_facecolor(BG_INNER)
    sub_axes.append(sub_ax)

    grid = grids[year]
    im = sub_ax.imshow(grid, aspect="auto", origin="lower", cmap=heat_cmap,
                        vmin=0, vmax=global_max, interpolation="nearest")

    # Labels
    sub_ax.set_xticks(range(12))
    sub_ax.set_xticklabels([m[0] for m in MONTH_NAMES], fontsize=8, color="#888")

    if i == 0:
        sub_ax.set_yticks([0, 4, 8, 12, 16, 20, 23])
        sub_ax.set_yticklabels(["12am", "4am", "8am", "12pm", "4pm", "8pm", "11pm"],
                                fontsize=9)
        sub_ax.set_ylabel("Hour of Day", color=TEXT_COLOR, fontsize=11, fontweight="bold")
    else:
        sub_ax.set_yticks([0, 4, 8, 12, 16, 20, 23])
        sub_ax.set_yticklabels([])

    year_label = f"{year}" if year < 2026 else f"{year} (YTD)"
    sub_ax.set_title(year_label, color="#fff", fontsize=12, fontweight="bold", pad=6)

    sub_ax.tick_params(colors="#888", labelsize=8)
    for spine in sub_ax.spines.values():
        spine.set_color(SPINE_COLOR)

# Colorbar for heatmap
cbar2 = fig.colorbar(im, ax=sub_axes, orientation="vertical", pad=0.08,
                      aspect=25, fraction=0.03, shrink=0.9)
cbar2.set_label("Days with Peak at Hour", fontsize=10, color=TEXT_COLOR)
cbar2.ax.tick_params(colors=TEXT_COLOR, labelsize=8)
cbar2.outline.set_edgecolor(SPINE_COLOR)

# Label for the heatmap section
fig.text(pos.x0 + pos.width / 2, pos.y0 + pos.height + 0.02,
         "When Does Peak LMP Occur? — Count of Days by Month × Hour",
         ha="center", va="bottom", color="#fff", fontsize=13, fontweight="bold")

# ── Save ──
out_path = os.path.join(script_dir, "peak_lmp_timeshift.png")
fig.savefig(out_path, dpi=200, facecolor=BG_OUTER, bbox_inches="tight")
print(f"\nSaved to {out_path}")
plt.close()

print("Done!")
