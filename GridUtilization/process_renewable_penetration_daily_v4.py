"""
Process CAISO fuel-source CSVs to calculate daily clean energy penetration (V4).

V4 changes:
  - Uses ACTUAL DEMAND from OASIS API (demand_forecast.json)
  - Total load = OASIS demand + battery charging (when negative)
  - Clean energy = Solar + Wind + Geo + Biomass + Biogas + Small hydro + Battery discharge + Nuclear + Large hydro
  - Penetration = clean_mw / total_load * 100

This fixes the issue where V3 was trying to calculate demand from sum of sources.
"""
import os
import csv
import json
import glob
from datetime import datetime
from collections import defaultdict

SUPPLY_DIR = os.path.join(os.path.dirname(__file__), "caiso_supply")
DEMAND_FILE = os.path.join(os.path.dirname(__file__), "demand_forecast.json")
OUT_FILE = os.path.join(os.path.dirname(__file__), "renewable_penetration_daily_v4.json")

# Clean energy sources (excluding batteries which are handled separately)
CLEAN_COLS = ["Solar", "Wind", "Geothermal", "Biomass", "Biogas", "Small hydro", "Nuclear", "Large Hydro"]

# Load OASIS demand data
print("Loading OASIS demand data...")
with open(DEMAND_FILE) as f:
    oasis_demand = json.load(f)
print(f"Loaded demand for {len(oasis_demand)} days")

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

    # Check if we have demand data for this date
    if date_key not in oasis_demand:
        continue

    demand_hourly = oasis_demand[date_key]
    if not demand_hourly or all(v is None for v in demand_hourly):
        continue

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

                # Get OASIS demand for this hour (hours 1-24 in OASIS, 0-23 in our data)
                # OASIS hour 1 = midnight hour (0:00-0:59)
                oasis_hour_idx = hour  # hour 0 -> demand_hourly[0], hour 1 -> demand_hourly[1], etc.
                if oasis_hour_idx < len(demand_hourly) and demand_hourly[oasis_hour_idx] is not None:
                    demand_mw = demand_hourly[oasis_hour_idx]

                    # Add battery charging as load
                    # When battery is negative (charging), add that as load
                    total_load = demand_mw + abs(min(battery_mw, 0))

                    # Calculate penetration percentage
                    if total_load > 0:
                        clean_pct = (clean_mw / total_load) * 100.0
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

print(f"\nSaved daily clean energy penetration data (V4) to {OUT_FILE}")
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
