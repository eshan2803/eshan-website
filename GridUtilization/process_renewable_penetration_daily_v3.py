"""
Process CAISO fuel-source CSVs to calculate daily clean energy penetration (V3).

V3 changes:
  - clean_mw = Solar + Wind + Geothermal + Biomass + Biogas + Small hydro + Battery discharge (when positive) + Nuclear + Large hydro
  - gross_demand_mw = Actual California consumption (excludes battery charging, includes battery discharge)
  - clean_pct = clean_mw / gross_demand_mw * 100

This version:
1. Treats battery discharge as renewable energy (stored solar)
2. Includes Nuclear and Large hydro as clean/zero-carbon resources
3. Uses GROSS DEMAND methodology:
   - When discharging: Battery is in both numerator and denominator (meeting real demand)
   - When charging: Battery is excluded from denominator (storage, not consumption)

Output daily statistics:
  - renewable_penetration_daily_v3.json  {
      "YYYY-MM-DD": {
        "hours_over_100": count,
        "avg_oversupply_pct": average_excess_when_over_100,
        "avg_penetration": average_penetration_all_hours,
        "max_penetration": peak_clean_pct
      }
    }
"""
import os
import csv
import json
import glob
from datetime import datetime
from collections import defaultdict

SUPPLY_DIR = os.path.join(os.path.dirname(__file__), "caiso_supply")
OUT_FILE = os.path.join(os.path.dirname(__file__), "renewable_penetration_daily_v3.json")

# Clean energy sources (excluding batteries which are handled separately)
CLEAN_COLS = ["Solar", "Wind", "Geothermal", "Biomass", "Biogas", "Small hydro", "Nuclear", "Large Hydro"]

# All generation columns (for demand calculation)
VALUE_COLS = [
    "Solar", "Wind", "Geothermal", "Biomass", "Biogas", "Small hydro",
    "Coal", "Nuclear", "Natural Gas", "Large Hydro", "Batteries",
    "Imports", "Other",
]

daily_data = {}

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
    hourly_penetration = []

    try:
        with open(fpath, "r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)

            # Store data by hour to compute hourly average
            hourly_data = defaultdict(list)

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

                # Calculate clean energy generation
                clean_mw = 0.0
                for col in CLEAN_COLS:
                    try:
                        clean_mw += float(row.get(col, 0) or 0)
                    except (ValueError, TypeError):
                        pass

                # Add battery discharge (only when positive) to clean energy
                battery_mw = 0.0
                try:
                    battery_mw = float(row.get("Batteries", 0) or 0)
                    if battery_mw > 0:
                        clean_mw += battery_mw
                except (ValueError, TypeError):
                    pass

                # Calculate net demand (sum of all sources including battery)
                net_demand_mw = 0.0
                for col in VALUE_COLS:
                    try:
                        net_demand_mw += float(row.get(col, 0) or 0)
                    except (ValueError, TypeError):
                        pass

                # Calculate gross demand (total load including battery charging)
                # When battery charges (negative), we need to ADD that load back
                # gross_demand = net_demand - min(battery, 0)
                # If battery = -5000, then min(-5000, 0) = -5000, so we add 5000 to demand
                # If battery = +2000, then min(+2000, 0) = 0, so demand unchanged
                gross_demand_mw = net_demand_mw - min(battery_mw, 0)

                # Calculate penetration percentage
                if gross_demand_mw > 0:
                    clean_pct = (clean_mw / gross_demand_mw) * 100.0
                    hourly_data[hour].append(clean_pct)

    except Exception as e:
        print(f"  ERROR reading {basename}: {e}")
        continue

    # Compute hourly averages
    for hour, pct_values in hourly_data.items():
        if pct_values:
            avg_pct = sum(pct_values) / len(pct_values)
            hourly_penetration.append(avg_pct)

    # Calculate daily statistics
    if hourly_penetration:
        hours_over_100 = sum(1 for p in hourly_penetration if p >= 100)
        oversupply_values = [p - 100 for p in hourly_penetration if p >= 100]
        avg_oversupply = (sum(oversupply_values) / len(oversupply_values)) if oversupply_values else 0.0
        avg_penetration = sum(hourly_penetration) / len(hourly_penetration)
        max_penetration = max(hourly_penetration)

        daily_data[date_key] = {
            "hours_over_100": hours_over_100,
            "avg_oversupply_pct": round(avg_oversupply, 2),
            "avg_penetration": round(avg_penetration, 2),
            "max_penetration": round(max_penetration, 2)
        }

    if (i + 1) % 500 == 0 or (i + 1) == len(files):
        print(f"  Processed {i+1}/{len(files)} files ...")

# Sort by date and save
sorted_data = dict(sorted(daily_data.items()))

with open(OUT_FILE, "w") as f:
    json.dump(sorted_data, f, indent=2)

print(f"\nSaved daily clean energy penetration data (V3) to {OUT_FILE}")
print(f"Processed {len(sorted_data)} days from {list(sorted_data.keys())[0]} to {list(sorted_data.keys())[-1]}")

# Print summary
total_hours_over_100 = sum(d["hours_over_100"] for d in sorted_data.values())
days_with_over_100 = sum(1 for d in sorted_data.values() if d["hours_over_100"] > 0)
max_hours_day = max(sorted_data.items(), key=lambda x: x[1]["hours_over_100"])
max_penetration_day = max(sorted_data.items(), key=lambda x: x[1]["max_penetration"])

print(f"\nSummary:")
print(f"  Total hours >=100% clean energy: {total_hours_over_100:,}")
print(f"  Days with any hours >=100%: {days_with_over_100:,}")
print(f"  Peak day for >=100% hours: {max_hours_day[0]} with {max_hours_day[1]['hours_over_100']} hours")
print(f"  Peak clean energy penetration: {max_penetration_day[1]['max_penetration']:.1f}% on {max_penetration_day[0]}")
