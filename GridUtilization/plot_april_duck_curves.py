"""
Plot average April duck curves from 2020-2025 showing:
- Demand
- Solar generation
- Battery charging (negative)
- Net load (demand - solar + battery charging)
"""
import os
import csv
import glob
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from collections import defaultdict

SUPPLY_DIR = os.path.join(os.path.dirname(__file__), "caiso_supply")

# Collect data by year and hour
data_by_year = {year: defaultdict(lambda: {'demand': [], 'solar': [], 'battery': []})
                for year in range(2020, 2026)}

files = sorted(glob.glob(os.path.join(SUPPLY_DIR, "*_fuelsource.csv")))
print(f"Processing {len(files)} files for April data...")

for fpath in files:
    basename = os.path.basename(fpath)
    date_str_raw = basename.split("_")[0]
    try:
        dt = datetime.strptime(date_str_raw, "%Y%m%d")
    except ValueError:
        continue

    # Only April data
    if dt.month != 4:
        continue

    year = dt.year
    if year not in data_by_year:
        continue

    try:
        with open(fpath, "r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)

            for row in reader:
                time_str = row.get("Time", "")
                if not time_str:
                    continue

                try:
                    time_parts = time_str.split(":")
                    hour = int(time_parts[0])
                except (ValueError, IndexError):
                    continue

                # Get solar
                try:
                    solar_mw = float(row.get("Solar") or 0)
                except (ValueError, TypeError):
                    solar_mw = 0.0

                # Get battery (negative = charging, positive = discharging)
                try:
                    battery_mw = float(row.get("Batteries") or 0)
                except (ValueError, TypeError):
                    battery_mw = 0.0

                # Calculate demand (all sources)
                demand_mw = 0.0
                for col in ["Solar", "Wind", "Geothermal", "Biomass", "Biogas", "Small hydro",
                           "Coal", "Nuclear", "Large Hydro", "Large hydro", "Natural Gas",
                           "Natural gas", "Batteries", "Imports", "Other"]:
                    try:
                        val = float(row.get(col) or 0)
                        demand_mw += val
                    except (ValueError, TypeError):
                        pass

                # Gross demand excludes battery charging
                gross_demand_mw = demand_mw - min(battery_mw, 0)

                data_by_year[year][hour]['demand'].append(gross_demand_mw)
                data_by_year[year][hour]['solar'].append(solar_mw)
                data_by_year[year][hour]['battery'].append(battery_mw)

    except Exception as e:
        continue

# Calculate averages
hours = list(range(24))
curves_by_year = {}

for year in range(2020, 2026):
    demand_avg = []
    solar_avg = []
    battery_avg = []
    net_load_avg = []

    for hour in hours:
        if data_by_year[year][hour]['demand']:
            d = np.mean(data_by_year[year][hour]['demand'])
            s = np.mean(data_by_year[year][hour]['solar'])
            b = np.mean(data_by_year[year][hour]['battery'])

            demand_avg.append(d / 1000.0)  # Convert to GW
            solar_avg.append(s / 1000.0)
            battery_avg.append(b / 1000.0)

            # Net load = demand - solar + battery_charging
            # (battery charging is negative, so we subtract it to add load)
            net_load = d - s - min(b, 0)
            net_load_avg.append(net_load / 1000.0)
        else:
            demand_avg.append(0)
            solar_avg.append(0)
            battery_avg.append(0)
            net_load_avg.append(0)

    curves_by_year[year] = {
        'demand': demand_avg,
        'solar': solar_avg,
        'battery': battery_avg,
        'net_load': net_load_avg
    }

    print(f"{year}: Processed {len(data_by_year[year][12]['demand'])} days")

# Plot
BG_COLOR = "#1a1d2e"
TEXT_COLOR = "#e2e8f0"
GRID_COLOR = "#2a2d3e"
SPINE_COLOR = "#3a3d4e"

fig, axes = plt.subplots(2, 3, figsize=(20, 11), facecolor=BG_COLOR)
fig.suptitle("California Duck Curve Evolution: April Average (2020-2025)\n"
             "Showing Demand, Solar Generation, Battery Charging, and Net Load",
             fontsize=16, fontweight="bold", color="#fff", y=0.995)

axes = axes.flatten()
years = [2020, 2021, 2022, 2023, 2024, 2025]

for idx, year in enumerate(years):
    ax = axes[idx]
    ax.set_facecolor(BG_COLOR)

    data = curves_by_year[year]

    # Plot curves
    ax.plot(hours, data['demand'], color="#60a5fa", linewidth=2.5, label="Gross Demand", zorder=4)
    ax.plot(hours, data['solar'], color="#facc15", linewidth=2.5, label="Solar Generation", zorder=3)
    ax.plot(hours, data['net_load'], color="#f97316", linewidth=2.5, label="Net Load", zorder=3, linestyle="--")

    # Plot battery (show charging as negative area)
    battery_charging = [-min(b, 0) for b in data['battery']]
    ax.fill_between(hours, 0, battery_charging, color="#a78bfa", alpha=0.6, label="Battery Charging", zorder=2)

    # Styling
    ax.set_title(f"{year}", fontsize=14, fontweight="bold", color="#fff", pad=10)
    ax.set_xlabel("Hour of Day", fontsize=11, color=TEXT_COLOR)
    if idx % 3 == 0:
        ax.set_ylabel("Power (GW)", fontsize=11, color=TEXT_COLOR, fontweight="bold")

    ax.set_xlim(0, 23)
    ax.set_ylim(0, 50)
    ax.set_xticks([0, 6, 12, 18, 23])
    ax.set_xticklabels(['0:00', '6:00', '12:00', '18:00', '23:00'], fontsize=9)

    ax.grid(True, color=GRID_COLOR, linewidth=0.5, alpha=0.5)
    ax.tick_params(colors=TEXT_COLOR, labelsize=9)

    for spine in ax.spines.values():
        spine.set_color(SPINE_COLOR)

    if idx == 0:
        ax.legend(loc='upper left', fontsize=9, framealpha=0.9, facecolor=BG_COLOR,
                 edgecolor=SPINE_COLOR, labelcolor=TEXT_COLOR)

plt.tight_layout()
out_path = os.path.join(os.path.dirname(__file__), "april_duck_curves.png")
plt.savefig(out_path, dpi=200, bbox_inches="tight", facecolor=BG_COLOR)
print(f"\nSaved to {out_path}")
plt.close()

print("Visualization complete!")
