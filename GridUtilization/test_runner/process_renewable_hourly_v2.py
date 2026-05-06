"""
Process CAISO fuel-source CSVs to extract hourly renewable penetration values (V2).

V2 changes:
  - renewable_mw = Solar + Wind + Geothermal + Biomass + Biogas + Small hydro + Battery discharge (when positive)
  - gross_demand_mw = Actual California consumption (excludes battery charging, includes battery discharge)
  - renewable_pct = renewable_mw / gross_demand_mw * 100

This version:
1. Treats battery discharge as renewable energy (stored solar)
2. Uses GROSS DEMAND methodology:
   - When discharging: Battery is in both numerator and denominator (meeting real demand)
   - When charging: Battery is excluded from denominator (storage, not consumption)

Output:
  - renewable_penetration_hourly_v2.json  {
      "YYYY-MM-DD HH": renewable_pct
    }
"""
import os
import csv
import json
import glob
from datetime import datetime
from collections import defaultdict

SUPPLY_DIR = os.path.join(os.path.dirname(__file__), "caiso_supply")
OUT_FILE = os.path.join(os.path.dirname(__file__), "renewable_penetration_hourly_v2.json")

# Renewable sources (batteries handled separately)
RENEWABLE_COLS = ["Solar", "Wind", "Geothermal", "Biomass", "Biogas", "Small hydro"]

# All generation columns
VALUE_COLS = [
    "Solar", "Wind", "Geothermal", "Biomass", "Biogas", "Small hydro",
    "Coal", "Nuclear", "Natural Gas", "Large Hydro", "Batteries",
    "Imports", "Other",
]

hourly_data = {}

files = sorted(glob.glob(os.path.join(SUPPLY_DIR, "*_fuelsource.csv")))
print(f"Found {len(files)} fuelsource CSV files")

for i, fpath in enumerate(files):
    basename = os.path.basename(fpath)
    date_str_raw = basename.split("_")[0]
    try:
        dt = datetime.strptime(date_str_raw, "%Y%m%d")
    except ValueError:
        continue

    date_key = dt.strftime("%Y-%m-%d")

    # Collect 5-min intervals grouped by hour
    hourly_intervals = defaultdict(list)

    try:
        with open(fpath, "r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)

            for row in reader:
                # Parse time to get hour
                time_str = row.get("Time", "")
                if not time_str:
                    continue

                try:
                    time_parts = time_str.split(":")
                    hour = int(time_parts[0])
                except (ValueError, IndexError):
                    continue

                # Calculate renewable generation
                renewable_mw = 0.0
                for col in RENEWABLE_COLS:
                    try:
                        renewable_mw += float(row.get(col, 0) or 0)
                    except (ValueError, TypeError):
                        pass

                # Add battery discharge (only when positive) to renewables
                battery_mw = 0.0
                try:
                    battery_mw = float(row.get("Batteries", 0) or 0)
                    if battery_mw > 0:
                        renewable_mw += battery_mw
                except (ValueError, TypeError):
                    pass

                # Calculate net demand (includes all sources including batteries)
                net_demand_mw = 0.0
                for col in VALUE_COLS:
                    try:
                        net_demand_mw += float(row.get(col, 0) or 0)
                    except (ValueError, TypeError):
                        pass

                # Calculate GROSS demand (actual California consumption)
                # When discharging (battery >= 0): Keep battery in demand (meeting real load)
                # When charging (battery < 0): Remove battery from demand (storage, not consumption)
                gross_demand_mw = net_demand_mw - min(battery_mw, 0)

                # Calculate penetration percentage
                if gross_demand_mw > 0:
                    renewable_pct = (renewable_mw / gross_demand_mw) * 100.0
                    hourly_intervals[hour].append(renewable_pct)

    except Exception as e:
        print(f"  ERROR reading {basename}: {e}")
        continue

    # Average 5-min intervals to get hourly values
    for hour, pct_values in hourly_intervals.items():
        if pct_values:
            avg_pct = sum(pct_values) / len(pct_values)
            hour_key = f"{date_key} {hour:02d}"
            hourly_data[hour_key] = round(avg_pct, 2)

    if (i + 1) % 500 == 0 or (i + 1) == len(files):
        print(f"  Processed {i+1}/{len(files)} files ...")

# Sort by datetime and save
sorted_data = dict(sorted(hourly_data.items()))

with open(OUT_FILE, "w") as f:
    json.dump(sorted_data, f, indent=1)

print(f"\nSaved hourly renewable penetration data (V2) to {OUT_FILE}")
print(f"Processed {len(sorted_data):,} hours from {list(sorted_data.keys())[0]} to {list(sorted_data.keys())[-1]}")

# Summary
hours_over_100 = sum(1 for v in sorted_data.values() if v >= 100)
max_penetration = max(sorted_data.values())
avg_penetration = sum(sorted_data.values()) / len(sorted_data)

print(f"\nSummary:")
print(f"  Hours with >=100% renewable: {hours_over_100:,} ({hours_over_100/len(sorted_data)*100:.2f}%)")
print(f"  Average renewable penetration: {avg_penetration:.1f}%")
print(f"  Peak renewable penetration: {max_penetration:.1f}%")
