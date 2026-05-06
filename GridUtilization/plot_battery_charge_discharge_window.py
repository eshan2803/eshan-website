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
charge_5min = defaultdict(dict)
discharge_5min = defaultdict(dict)

with open(CSV_FILE, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    count = 0
    for row in reader:
        ts = row["timestamp"]
        charge_str = row.get("battery_charging_mw", "")
        discharge_str = row.get("battery_discharging_mw", "")
        
        charge_val = None
        discharge_val = None
        
        if charge_str and charge_str.strip():
            try: charge_val = float(charge_str)
            except ValueError: pass
            
        if discharge_str and discharge_str.strip():
            try: discharge_val = float(discharge_str)
            except ValueError: pass

        if charge_val is None and discharge_val is None:
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
        
        if charge_val is not None:
            charge_5min[date_key][slot] = charge_val
        if discharge_val is not None:
            discharge_5min[date_key][slot] = discharge_val
            
        count += 1
        if count % 500000 == 0:
            print(f"  Read {count:,} rows...")

print(f"  Total: {count:,} valid rows.")

# ── Build 5-min heatmap matrices ──
dates_set = set(charge_5min.keys()) | set(discharge_5min.keys())
dates_sorted = sorted(list(dates_set))
date_objs = [dt.strptime(d, "%Y-%m-%d") for d in dates_sorted]
n_days = len(dates_sorted)
N_SLOTS = 288  # 24 * 12

raw_charge = np.full((N_SLOTS, n_days), np.nan)
raw_discharge = np.full((N_SLOTS, n_days), np.nan)

for j, date_key in enumerate(dates_sorted):
    for slot, mw in charge_5min.get(date_key, {}).items():
        if 0 <= slot < N_SLOTS:
            raw_charge[slot, j] = mw
    for slot, mw in discharge_5min.get(date_key, {}).items():
        if 0 <= slot < N_SLOTS:
            raw_discharge[slot, j] = mw

# ── Style ──
BG_OUTER = "#0f1117"
BG_INNER = "#1a1d2e"
TEXT_COLOR = "#e2e8f0"
GRID_COLOR = "#2a2d3e"
SPINE_COLOR = "#3a3d4e"

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 13), facecolor=BG_OUTER,
                                 gridspec_kw={"hspace": 0.35, "height_ratios": [1, 1]})

last_date_label = dt.strptime(dates_sorted[-1], "%Y-%m-%d").strftime("%B %d, %Y")
x_dates = mdates.date2num(date_objs)
x_edges = np.append(x_dates, x_dates[-1] + 1)
y_edges = np.arange(N_SLOTS + 1)

# ═══════════ Panel 1: Battery Charging Heatmap ═══════════
print("Creating Panel 1: Battery Charging heatmap...")
ax1.set_facecolor(BG_INNER)

# Colormap for charging: background -> dark green -> emerald -> yellow-green -> white
cmap1 = mcolors.LinearSegmentedColormap.from_list("battery_charge", [
    "#1a1d2e",   # background
    "#064e3b",   # very dark green
    "#10b981",   # emerald
    "#84cc16",   # lime
    "#ffffff",   # white
])
cmap1.set_bad(BG_INNER)
vmax1 = np.nanpercentile(raw_charge, 99.5)
norm1 = mcolors.Normalize(vmin=0, vmax=vmax1)

im1 = ax1.pcolormesh(x_edges, y_edges, raw_charge, cmap=cmap1, norm=norm1,
                     shading="flat", rasterized=True)

ax1.set_ylabel("Hour of Day", color=TEXT_COLOR, fontsize=12, fontweight="bold")
ax1.set_ylim(0, N_SLOTS)
hour_ticks = [h * 12 for h in [0, 3, 6, 9, 12, 15, 18, 21, 24]]
ax1.set_yticks(hour_ticks)
ax1.set_yticklabels(["12am", "3am", "6am", "9am", "12pm", "3pm", "6pm", "9pm", "12am"], fontsize=10)
ax1.invert_yaxis()

ax1.xaxis.set_major_locator(mdates.YearLocator())
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
ax1.set_xlim(x_dates[0], x_dates[-1])

# Charging GWh Overlay
daily_gwh1 = []
for j in range(raw_charge.shape[1]):
    gwh = np.nansum(raw_charge[:, j]) / 12.0 / 1000.0
    daily_gwh1.append(gwh)

ax1_twin = ax1.twinx()
window = 14
padded_gwh1 = np.pad(daily_gwh1, (window//2, window-1-window//2), mode='edge')
smoothed_gwh1 = np.convolve(padded_gwh1, np.ones(window)/window, mode='valid')

ax1_twin.plot(x_dates, daily_gwh1, color="#34d399", alpha=0.3, linewidth=0.5)
ax1_twin.plot(x_dates, smoothed_gwh1, color="#34d399", alpha=1.0, linewidth=1.5, label="Total Charging")

ax1_twin.set_ylabel("Total Daily Charging (GWh)", color="#34d399", fontsize=11, fontweight="bold")
ax1_twin.set_ylim(0, max(daily_gwh1) * 1.1)
ax1_twin.tick_params(axis='y', colors="#34d399", labelsize=10)
for spine in ax1_twin.spines.values():
    spine.set_color(SPINE_COLOR)
ax1_twin.spines["right"].set_color("#34d399")

ax1.set_title(f"California Grid: Battery Charging Window (Mid-Day)\n"
              f"5-Minute Resolution — Updated through {last_date_label}",
              color="#fff", fontsize=14, fontweight="bold", pad=12)

ax1.tick_params(colors="#888", labelsize=10)
for spine in ax1.spines.values():
    spine.set_color(SPINE_COLOR)

cbar1 = fig.colorbar(im1, ax=ax1, orientation="vertical", pad=0.08, aspect=20, fraction=0.03)
cbar1.set_label("Charging (MW)", fontsize=10, color=TEXT_COLOR)
cbar1.ax.tick_params(colors=TEXT_COLOR, labelsize=9)
cbar1.outline.set_edgecolor(SPINE_COLOR)


# ═══════════ Panel 2: Battery Discharging Heatmap ═══════════
print("Creating Panel 2: Battery Discharging heatmap...")
ax2.set_facecolor(BG_INNER)

cmap2 = mcolors.LinearSegmentedColormap.from_list("battery_discharge", [
    "#1a1d2e",   # background 
    "#1e3a5f",   # dark blue
    "#2563eb",   # blue
    "#06b6d4",   # cyan
    "#fbbf24",   # amber
    "#ffffff",   # white
])
cmap2.set_bad(BG_INNER)
vmax2 = np.nanpercentile(raw_discharge, 99.5)
norm2 = mcolors.Normalize(vmin=0, vmax=vmax2)

im2 = ax2.pcolormesh(x_edges, y_edges, raw_discharge, cmap=cmap2, norm=norm2,
                     shading="flat", rasterized=True)

ax2.set_ylabel("Hour of Day", color=TEXT_COLOR, fontsize=12, fontweight="bold")
ax2.set_ylim(0, N_SLOTS)
ax2.set_yticks(hour_ticks)
ax2.set_yticklabels(["12am", "3am", "6am", "9am", "12pm", "3pm", "6pm", "9pm", "12am"], fontsize=10)
ax2.invert_yaxis()

ax2.xaxis.set_major_locator(mdates.YearLocator())
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
ax2.set_xlim(x_dates[0], x_dates[-1])

# Discharging GWh Overlay
daily_gwh2 = []
for j in range(raw_discharge.shape[1]):
    gwh = np.nansum(raw_discharge[:, j]) / 12.0 / 1000.0
    daily_gwh2.append(gwh)

ax2_twin = ax2.twinx()
padded_gwh2 = np.pad(daily_gwh2, (window//2, window-1-window//2), mode='edge')
smoothed_gwh2 = np.convolve(padded_gwh2, np.ones(window)/window, mode='valid')

ax2_twin.plot(x_dates, daily_gwh2, color="#ec4899", alpha=0.3, linewidth=0.5)
ax2_twin.plot(x_dates, smoothed_gwh2, color="#ec4899", alpha=1.0, linewidth=1.5, label="Total Discharge")

ax2_twin.set_ylabel("Total Daily Discharge (GWh)", color="#ec4899", fontsize=11, fontweight="bold")
ax2_twin.set_ylim(0, max(daily_gwh2) * 1.1)
ax2_twin.tick_params(axis='y', colors="#ec4899", labelsize=10)
for spine in ax2_twin.spines.values():
    spine.set_color(SPINE_COLOR)
ax2_twin.spines["right"].set_color("#ec4899")

ax2.set_title(f"California Grid: Battery Discharge Window (Evening/Morning)\n"
              f"5-Minute Resolution",
              color="#fff", fontsize=14, fontweight="bold", pad=12)

ax2.tick_params(colors="#888", labelsize=10)
for spine in ax2.spines.values():
    spine.set_color(SPINE_COLOR)

cbar2 = fig.colorbar(im2, ax=ax2, orientation="vertical", pad=0.08, aspect=20, fraction=0.03)
cbar2.set_label("Discharge (MW)", fontsize=10, color=TEXT_COLOR)
cbar2.ax.tick_params(colors=TEXT_COLOR, labelsize=9)
cbar2.outline.set_edgecolor(SPINE_COLOR)

# ── Save ──
print("Saving figure...")
out_path = os.path.join(script_dir, "battery_charge_discharge_window.png")
fig.savefig(out_path, dpi=200, facecolor=BG_OUTER, bbox_inches="tight")
print(f"Saved to {out_path}")
plt.close()

print("\nDone!")
