"""
Negative LMP scatter charts — HOURLY resolution (2020-2026), colored by curtailment.

Chart 1: x = grid load (GWh), y = LMP ($/MWh), color = local curtailment
Chart 2: x = net load (GWh), y = LMP ($/MWh), color = local curtailment
Chart 3: x = grid load (GWh), y = LMP ($/MWh), color = system curtailment
Chart 4: x = net load (GWh), y = LMP ($/MWh), color = system curtailment

Each dot = one hour with negative LMP. Consistent hourly resolution across all years.
Reads from caiso_comprehensive_data.csv, filtering to :00 rows only.
Curtailment data from combined_curtailment_data_2019_2026.csv.
"""
import csv
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from datetime import datetime as dt
from collections import defaultdict

script_dir = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(script_dir, "caiso_comprehensive_data.csv")
CURTAILMENT_FILE = os.path.join(
    os.path.dirname(os.path.dirname(script_dir)), "curtailmentdata", "combined_curtailment_data_2019_2026.csv"
)

# ── Load curtailment data ──
# Curtailment CSV: Date (YYYY-MM-DD), Hour (1-24 hour-ending), Local Curtailment, System Curtailment
# Convert hour-ending 1-24 to hour-beginning 0-23
print("Loading curtailment data...")
curtailment = {}  # (date_str, hour_0_23) -> (local_mw, system_mw)

with open(CURTAILMENT_FILE, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        date_str = row["Date"].strip()
        try:
            hour_ending = int(row["Hour"])
            hour_beginning = hour_ending - 1  # 1-24 -> 0-23
            if hour_beginning < 0:
                continue
            local = float(row["Local Curtailment"])
            system = float(row["System Curtailment"])
            curtailment[(date_str, hour_beginning)] = (local, system)
        except (ValueError, TypeError):
            continue

print(f"  Loaded {len(curtailment):,} curtailment records")

# ── Read CSV and compute Hourly Averages ──
print("Reading comprehensive CSV and computing true hourly averages...")
import pandas as pd
df = pd.read_csv(CSV_FILE, usecols=['timestamp', 'lmp', 'load_mw', 'demand_mw', 'solar_mw', 'wind_mw', 'battery_charging_mw'])

# Combine load and demand safely
if 'load_mw' in df.columns and 'demand_mw' in df.columns:
    df['load_mw'] = df['load_mw'].fillna(df['demand_mw'])

# Convert numeric columns
cols_to_avg = ['lmp', 'load_mw', 'solar_mw', 'wind_mw', 'battery_charging_mw']
for c in cols_to_avg:
    df[c] = pd.to_numeric(df[c], errors='coerce')

df['timestamp'] = pd.to_datetime(df['timestamp'])
df.set_index('timestamp', inplace=True)

# Important: Resample mathematically averages the 12 5-minute intervals inside each hour
hourly_df = df[cols_to_avg].resample('1h').mean()

negative_intervals = defaultdict(list)
count = 0
matched = 0

for ts, row in hourly_df.iterrows():
    if pd.isna(row['lmp']) or row['lmp'] >= 0:
        continue
        
    year = ts.year
    date_str = ts.strftime("%Y-%m-%d")
    hour = ts.hour
    
    lmp = float(row['lmp'])
    load_mw = float(row['load_mw']) if not pd.isna(row['load_mw']) else 0
    solar_mw = float(row['solar_mw']) if not pd.isna(row['solar_mw']) else 0
    wind_mw = float(row['wind_mw']) if not pd.isna(row['wind_mw']) else 0
    battery_charging_mw = float(row['battery_charging_mw']) if not pd.isna(row['battery_charging_mw']) else 0
    
    # Floor at 0 for generation/metrics just like previous script
    load_mw = max(load_mw, 0)
    solar_mw = max(solar_mw, 0)
    wind_mw = max(wind_mw, 0)
    battery_charging_mw = max(battery_charging_mw, 0)
    
    load_gwh = load_mw / 1000.0
    net_load_gwh = (load_mw - solar_mw - wind_mw) / 1000.0
    
    local_curtail = 0.0
    system_curtail = 0.0
    if (date_str, hour) in curtailment:
        local_curtail, system_curtail = curtailment[(date_str, hour)]
        matched += 1
        
    total_curtail = local_curtail + system_curtail
    batt_charging_gw = battery_charging_mw / 1000.0
    
    negative_intervals[year].append((lmp, load_gwh, net_load_gwh, local_curtail, system_curtail, total_curtail, batt_charging_gw))
    count += 1

print(f"  Total negative-LMP hours: {count:,}")
print(f"  Matched curtailment data: {matched:,} ({100*matched/max(count,1):.1f}%)")

for year in sorted(negative_intervals.keys()):
    n = len(negative_intervals[year])
    min_lmp = min(t[0] for t in negative_intervals[year])
    max_local = max(t[3] for t in negative_intervals[year])
    max_system = max(t[4] for t in negative_intervals[year])
    print(f"  {year}: {n:,} hours, min LMP ${min_lmp:.2f}, max local curtail {max_local:,.0f} MW, max system curtail {max_system:,.0f} MW")

# ── Style ──
BG_OUTER = "#0f1117"
BG_INNER = "#1a1d2e"
TEXT_COLOR = "#e2e8f0"
GRID_COLOR = "#2a2d3e"
SPINE_COLOR = "#3a3d4e"

YEARS = [2020, 2021, 2022, 2023, 2024, 2025, 2026]
n_panels = len(YEARS)

# Global y range
all_lmps = []
for year in YEARS:
    if year in negative_intervals:
        all_lmps.extend(t[0] for t in negative_intervals[year])
y_min = min(all_lmps) if all_lmps else -100

# Global curtailment ranges for consistent colorbars
all_local = []
all_system = []
all_total = []
all_batt_charge = []
for year in YEARS:
    if year in negative_intervals:
        all_local.extend(t[3] for t in negative_intervals[year])
        all_system.extend(t[4] for t in negative_intervals[year])
        all_total.extend(t[5] for t in negative_intervals[year])
        all_batt_charge.extend(t[6] for t in negative_intervals[year])

local_max = max(all_local) if all_local else 1000
system_max = max(all_system) if all_system else 1000
total_max = max(all_total) if all_total else 1000
batt_charge_max = max(all_batt_charge) if all_batt_charge else 100

# Curtailment colormap: light gray (0) -> cyan -> yellow -> red (high)
curtail_cmap = mcolors.LinearSegmentedColormap.from_list("curtailment", [
    "#cbd5e1", "#06b6d4", "#10b981", "#fbbf24", "#f97316", "#ef4444",
])


def make_chart(x_index, x_label, title_suffix, filename, curtail_index, curtail_label, curtail_max_val):
    """Generate one scatter chart colored by curtailment.
    x_index: 1=load_gwh, 2=net_load_gwh
    curtail_index: 3=local, 4=system
    """
    fig, axes = plt.subplots(1, n_panels, figsize=(28, 9), facecolor=BG_OUTER,
                              sharey=True, gridspec_kw={"wspace": 0.06})

    # Global x-axis range across all years
    x_max = 0
    x_min = 0
    for year in YEARS:
        if year in negative_intervals:
            vals = [t[x_index] for t in negative_intervals[year]]
            x_max = max(x_max, max(vals))
            if x_index == 2:
                x_min = min(x_min, min(vals))
    x_max *= 1.1
    x_min *= 1.1

    norm = mcolors.Normalize(vmin=0, vmax=curtail_max_val)
    sm = plt.cm.ScalarMappable(cmap=curtail_cmap, norm=norm)

    for idx, (ax, year) in enumerate(zip(axes, YEARS)):
        ax.set_facecolor(BG_INNER)
        ax.tick_params(colors="#888", labelsize=8)
        for spine in ax.spines.values():
            spine.set_color(SPINE_COLOR)

        intervals = negative_intervals.get(year, [])
        if not intervals:
            ax.set_title(f"{year}", color="#fff", fontsize=13, fontweight="bold")
            ax.set_ylim(y_min * 1.05, 0)
            ax.set_xlim(x_min, x_max)
            continue

        lmps = np.array([t[0] for t in intervals])
        x_vals = np.array([t[x_index] for t in intervals])
        c_vals = np.array([t[curtail_index] for t in intervals])

        # Sort by curtailment so high values are drawn on top
        sort_idx = np.argsort(c_vals)

        ax.scatter(x_vals[sort_idx], lmps[sort_idx], c=c_vals[sort_idx],
                   cmap=curtail_cmap, norm=norm,
                   s=14, alpha=0.7, edgecolors="none", rasterized=True)

        # Stats
        n_hours = len(intervals)
        total_gwh = sum(t[1] for t in intervals)
        min_price = min(lmps)
        avg_curtail = np.mean(c_vals)

        ax.text(0.96, 0.03,
                f"{n_hours:,} hrs\n{total_gwh:,.0f} GWh\nMin: ${min_price:.0f}\nAvg curtail: {avg_curtail:,.0f} MW",
                transform=ax.transAxes, ha="right", va="bottom",
                fontsize=7.5, color=TEXT_COLOR,
                bbox=dict(boxstyle="round,pad=0.2", fc=BG_INNER, ec=SPINE_COLOR, alpha=0.9))

        ax.set_ylim(y_min * 1.05, 2)
        ax.axhline(0, color=SPINE_COLOR, linewidth=0.5)
        ax.set_xlim(x_min, x_max)

        # Vertical line at x=0 for net load chart
        if x_index == 2:
            ax.axvline(0, color="#ef4444", linewidth=0.8, alpha=0.5, linestyle="--")

        ax.grid(True, axis="y", color=GRID_COLOR, linewidth=0.5, alpha=0.5)
        ax.grid(True, axis="x", color=GRID_COLOR, linewidth=0.5, alpha=0.3)

        year_label = f"{year}" if year < 2026 else f"{year} (YTD)"
        ax.set_title(year_label, color="#fff", fontsize=13, fontweight="bold", pad=8)
        ax.set_xlabel(x_label, fontsize=8, color="#888")

        if idx == 0:
            ax.set_ylabel("LMP Price ($/MWh)", color=TEXT_COLOR, fontsize=11, fontweight="bold")

    # Colorbar
    cbar = fig.colorbar(sm, ax=axes.tolist(), orientation="vertical", pad=0.015,
                         aspect=30, fraction=0.02, shrink=0.85)
    cbar.set_label(f"{curtail_label}", fontsize=10, color=TEXT_COLOR, fontweight="bold")
    cbar.ax.tick_params(colors=TEXT_COLOR, labelsize=9)
    cbar.outline.set_edgecolor(SPINE_COLOR)

    fig.suptitle(f"California Grid: Negative LMP Events — {title_suffix}\n"
                 f"Each dot = one hour with negative price, colored by {curtail_label.lower()} (hourly, 2020-2026)",
                 color="#fff", fontsize=15, fontweight="bold", y=1.02)

    out_path = os.path.join(script_dir, filename)
    fig.savefig(out_path, dpi=200, facecolor=BG_OUTER, bbox_inches="tight")
    print(f"Saved to {out_path}")
    plt.close()


# ── Generate charts ──
print("\nChart 1: LMP vs Grid Load, colored by Local Curtailment...")
make_chart(1, "Grid Load (GWh)", "LMP vs Grid Load",
           "negative_lmp_local_curtail_hourly.png", 3, "Local Curtailment (MW)", local_max)

print("\nChart 2: LMP vs Net Load, colored by Local Curtailment...")
make_chart(2, "Net Load (GWh)", "LMP vs Net Load (Load − Solar − Wind)",
           "negative_lmp_net_load_local_curtail_hourly.png", 3, "Local Curtailment (MW)", local_max)

print("\nChart 3: LMP vs Grid Load, colored by System Curtailment...")
make_chart(1, "Grid Load (GWh)", "LMP vs Grid Load",
           "negative_lmp_system_curtail_hourly.png", 4, "System Curtailment (MW)", system_max)

print("\nChart 4: LMP vs Net Load, colored by System Curtailment...")
make_chart(2, "Net Load (GWh)", "LMP vs Net Load (Load − Solar − Wind)",
           "negative_lmp_net_load_system_curtail_hourly.png", 4, "System Curtailment (MW)", system_max)

print("\nChart 5: LMP vs Grid Load, colored by Total Curtailment...")
make_chart(1, "Grid Load (GWh)", "LMP vs Grid Load",
           "negative_lmp_total_curtail_hourly.png", 5, "Total Curtailment (MW)", total_max)

print("\nChart 6: LMP vs Net Load, colored by Total Curtailment...")
make_chart(2, "Net Load (GWh)", "LMP vs Net Load (Load − Solar − Wind)",
           "negative_lmp_net_load_total_curtail_hourly.png", 5, "Total Curtailment (MW)", total_max)

print("\nChart 7: LMP vs Grid Load, colored by Battery Charging...")
make_chart(1, "Grid Load (GWh)", "LMP vs Grid Load",
           "negative_lmp_batt_charge_hourly.png", 6, "Battery Charging (GW)", batt_charge_max)

print("\nChart 8: LMP vs Net Load, colored by Battery Charging...")
make_chart(2, "Net Load (GWh)", "LMP vs Net Load (Load − Solar − Wind)",
           "negative_lmp_net_load_batt_charge_hourly.png", 6, "Battery Charging (GW)", batt_charge_max)

print("\nDone!")
