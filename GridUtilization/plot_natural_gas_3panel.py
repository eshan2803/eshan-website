"""
Natural gas generation 3-panel chart.

Panel 1: Daily total energy from natural gas (GWh) — integrated from 5-min intervals
Panel 2: Daily maximum natural gas generation (MW)
Panel 3: Daily average natural gas generation (MW)

Reads fuelsource CSVs directly for panels 1 & 2, and natural_gas_daily.json for panel 3.
"""
import os
import csv
import json
import glob
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime as dt
from collections import defaultdict

script_dir = os.path.dirname(os.path.abspath(__file__))
SUPPLY_DIR = os.path.join(script_dir, "caiso_supply")

# ── Process fuelsource CSVs to get daily total MWh and max MW ──
print("Processing fuelsource CSVs for natural gas...")
daily_gas = {}  # date_key -> {total_mwh, max_mw, avg_mw}

files = sorted(glob.glob(os.path.join(SUPPLY_DIR, "*_fuelsource.csv")))
print(f"  Found {len(files)} files")

for i, fpath in enumerate(files):
    basename = os.path.basename(fpath)
    date_str_raw = basename.split("_")[0]
    try:
        date_obj = dt.strptime(date_str_raw, "%Y%m%d")
    except ValueError:
        continue

    date_key = date_obj.strftime("%Y-%m-%d")
    total_mw_intervals = []

    try:
        with open(fpath, "r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            col_map = None

            for row in reader:
                if col_map is None:
                    col_map = {c.lower(): c for c in row.keys()}

                gas_col = col_map.get("natural gas", None)
                if gas_col is None:
                    break

                try:
                    gas_mw = float(row.get(gas_col, 0) or 0)
                except (ValueError, TypeError):
                    gas_mw = 0.0

                total_mw_intervals.append(gas_mw)

    except Exception:
        continue

    if total_mw_intervals:
        interval_hours = 1.0 / 12.0  # 5-min = 1/12 hour
        total_mwh = sum(v * interval_hours for v in total_mw_intervals)
        daily_gas[date_key] = {
            "total_gwh": total_mwh / 1000.0,  # Convert to GWh
            "max_mw": max(total_mw_intervals),
            "avg_mw": sum(total_mw_intervals) / len(total_mw_intervals),
        }

    if (i + 1) % 500 == 0 or (i + 1) == len(files):
        print(f"  Processed {i+1}/{len(files)} files")

print(f"  {len(daily_gas)} days of data")

# ── Build arrays ──
dates = []
total_gwh = []
max_mw = []
avg_mw = []

for date_key in sorted(daily_gas.keys()):
    dates.append(dt.strptime(date_key, "%Y-%m-%d"))
    total_gwh.append(daily_gas[date_key]["total_gwh"])
    max_mw.append(daily_gas[date_key]["max_mw"])
    avg_mw.append(daily_gas[date_key]["avg_mw"])

dates = np.array(dates)
total_gwh = np.array(total_gwh)
max_mw = np.array(max_mw)
avg_mw = np.array(avg_mw)

x = mdates.date2num(dates)

# ── Compute yearly averages for annotation ──
yearly_stats = defaultdict(lambda: {"gwh": [], "max": [], "avg": []})
for d, g, mx, av in zip(dates, total_gwh, max_mw, avg_mw):
    yearly_stats[d.year]["gwh"].append(g)
    yearly_stats[d.year]["max"].append(mx)
    yearly_stats[d.year]["avg"].append(av)

# ── Style ──
BG_OUTER = "#0f1117"
BG_INNER = "#1a1d2e"
TEXT_COLOR = "#e2e8f0"
GRID_COLOR = "#2a2d3e"
SPINE_COLOR = "#3a3d4e"

# Orange palette for natural gas
COLOR_GWH = "#f97316"
COLOR_MAX = "#ef4444"
COLOR_AVG = "#fb923c"

# ── Plot ──
fig, axes = plt.subplots(3, 1, figsize=(16, 14), facecolor=BG_OUTER,
                          gridspec_kw={"hspace": 0.35})

last_date_label = sorted(daily_gas.keys())[-1]
last_date_fmt = dt.strptime(last_date_label, "%Y-%m-%d").strftime("%B %d, %Y")

for ax in axes:
    ax.set_facecolor(BG_INNER)
    ax.tick_params(colors="#888", labelsize=10)
    for spine in ax.spines.values():
        spine.set_color(SPINE_COLOR)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax.set_xlim(x[0], x[-1])
    ax.grid(True, color=GRID_COLOR, linewidth=0.5, alpha=0.7)

# ═══════════ Panel 1: Daily Total Energy (GWh) ═══════════
print("Creating Panel 1: Daily total energy...")
ax1 = axes[0]
ax1.fill_between(x, total_gwh, alpha=0.3, color=COLOR_GWH)
ax1.plot(x, total_gwh, color=COLOR_GWH, linewidth=0.6, alpha=0.8)

# 30-day rolling average
window = 30
if len(total_gwh) > window:
    rolling = np.convolve(total_gwh, np.ones(window)/window, mode='valid')
    ax1.plot(x[window-1:], rolling, color="#ffffff", linewidth=1.5, alpha=0.9,
             label=f"{window}-day avg")

# Yearly annotations
for year, stats in sorted(yearly_stats.items()):
    y_avg = sum(stats["gwh"]) / len(stats["gwh"])
    mid_date = dt(year, 7, 1) if year < 2026 else dt(year, 2, 15)
    ax1.annotate(f"{y_avg:.0f}", xy=(mdates.date2num(mid_date), y_avg),
                 fontsize=9, color=TEXT_COLOR, ha="center", va="bottom",
                 fontweight="bold",
                 bbox=dict(boxstyle="round,pad=0.2", fc=BG_INNER, ec=SPINE_COLOR, alpha=0.8))

ax1.set_ylabel("GWh / day", color=TEXT_COLOR, fontsize=12, fontweight="bold")
ax1.set_title(f"California Grid: Daily Natural Gas Energy\nUpdated through {last_date_fmt}",
              color="#fff", fontsize=14, fontweight="bold", pad=12)
ax1.legend(loc="upper right", fontsize=9, framealpha=0.8, facecolor=BG_INNER,
           edgecolor=SPINE_COLOR, labelcolor=TEXT_COLOR)
ax1.set_ylim(0, max(total_gwh) * 1.08)

# ═══════════ Panel 2: Daily Maximum MW ═══════════
print("Creating Panel 2: Daily max MW...")
ax2 = axes[1]
ax2.fill_between(x, max_mw, alpha=0.3, color=COLOR_MAX)
ax2.plot(x, max_mw, color=COLOR_MAX, linewidth=0.6, alpha=0.8)

if len(max_mw) > window:
    rolling_max = np.convolve(max_mw, np.ones(window)/window, mode='valid')
    ax2.plot(x[window-1:], rolling_max, color="#ffffff", linewidth=1.5, alpha=0.9,
             label=f"{window}-day avg")

for year, stats in sorted(yearly_stats.items()):
    y_avg = sum(stats["max"]) / len(stats["max"])
    mid_date = dt(year, 7, 1) if year < 2026 else dt(year, 2, 15)
    ax2.annotate(f"{y_avg:,.0f}", xy=(mdates.date2num(mid_date), y_avg),
                 fontsize=9, color=TEXT_COLOR, ha="center", va="bottom",
                 fontweight="bold",
                 bbox=dict(boxstyle="round,pad=0.2", fc=BG_INNER, ec=SPINE_COLOR, alpha=0.8))

ax2.set_ylabel("MW (peak)", color=TEXT_COLOR, fontsize=12, fontweight="bold")
ax2.set_title("Daily Peak Natural Gas Generation",
              color="#fff", fontsize=13, fontweight="bold", pad=10)
ax2.legend(loc="upper right", fontsize=9, framealpha=0.8, facecolor=BG_INNER,
           edgecolor=SPINE_COLOR, labelcolor=TEXT_COLOR)
ax2.set_ylim(0, max(max_mw) * 1.08)

# ═══════════ Panel 3: Daily Average MW ═══════════
print("Creating Panel 3: Daily average MW...")
ax3 = axes[2]
ax3.fill_between(x, avg_mw, alpha=0.3, color=COLOR_AVG)
ax3.plot(x, avg_mw, color=COLOR_AVG, linewidth=0.6, alpha=0.8)

if len(avg_mw) > window:
    rolling_avg = np.convolve(avg_mw, np.ones(window)/window, mode='valid')
    ax3.plot(x[window-1:], rolling_avg, color="#ffffff", linewidth=1.5, alpha=0.9,
             label=f"{window}-day avg")

for year, stats in sorted(yearly_stats.items()):
    y_avg = sum(stats["avg"]) / len(stats["avg"])
    mid_date = dt(year, 7, 1) if year < 2026 else dt(year, 2, 15)
    ax3.annotate(f"{y_avg:,.0f}", xy=(mdates.date2num(mid_date), y_avg),
                 fontsize=9, color=TEXT_COLOR, ha="center", va="bottom",
                 fontweight="bold",
                 bbox=dict(boxstyle="round,pad=0.2", fc=BG_INNER, ec=SPINE_COLOR, alpha=0.8))

ax3.set_ylabel("MW (avg)", color=TEXT_COLOR, fontsize=12, fontweight="bold")
ax3.set_title("Daily Average Natural Gas Generation",
              color="#fff", fontsize=13, fontweight="bold", pad=10)
ax3.legend(loc="upper right", fontsize=9, framealpha=0.8, facecolor=BG_INNER,
           edgecolor=SPINE_COLOR, labelcolor=TEXT_COLOR)
ax3.set_ylim(0, max(avg_mw) * 1.08)

# ── Save ──
print("Saving figure...")
out_path = os.path.join(script_dir, "natural_gas_3panel.png")
fig.savefig(out_path, dpi=200, facecolor=BG_OUTER, bbox_inches="tight")
print(f"Saved to {out_path}")
plt.close()

print("\nDone!")
