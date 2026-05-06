"""
Process CAISO data to calculate daily clean energy penetration (V5).

V5 changes:
  - Uses DEMAND from renewables trend CSV files (caiso_downloads/*_renewables_raw.csv)
  - Total load = CSV demand + battery charging (when negative)
  - Clean energy = Solar + Wind + Geo + Biomass + Biogas + Small hydro + Battery discharge + Nuclear + Large hydro
  - Penetration = clean_mw / total_load * 100

This uses the same demand source as CAISO Daily charts.
"""
import os
import csv
import json
import glob
from datetime import datetime
from collections import defaultdict

SUPPLY_DIR = os.path.join(os.path.dirname(__file__), "caiso_supply")
RENEWABLES_DIR = os.path.join(os.path.dirname(__file__), "caiso_downloads")
OUT_FILE = os.path.join(os.path.dirname(__file__), "renewable_penetration_daily_v5.json")

# Clean energy sources (excluding batteries which are handled separately)
CLEAN_COLS = ["Solar", "Wind", "Geothermal", "Biomass", "Biogas", "Small hydro", "Nuclear", "Large Hydro"]

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

    # Load demand from renewables CSV
    renewables_file = os.path.join(RENEWABLES_DIR, f"{date_str_raw}_renewables_raw.csv")
    if not os.path.exists(renewables_file):
        continue

    # Read demand row from renewables CSV
    try:
        with open(renewables_file, "r", encoding="utf-8-sig") as f:
            demand_5min = None
            for line in f:
                if line.startswith("Demand,"):
                    # Parse demand values (skip last value if it's 289 instead of 288)
                    parts = line.strip().split(",")[1:]
                    demand_5min = [float(x) for x in parts if x.strip()]
                    # Truncate to 288 if needed
                    if len(demand_5min) > 288:
                        demand_5min = demand_5min[:288]
                    break

            if not demand_5min or len(demand_5min) == 0:
                continue

    except Exception as e:
        print(f"  ERROR reading renewables file {renewables_file}: {e}")
        continue

    # Process fuelsource data with demand
    hourly_penetration = []

    try:
        with open(fpath, "r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)

            # Store data by hour to compute hourly average
            hourly_data = defaultdict(list)

            for idx, row in enumerate(reader):
                # Get demand for this 5-minute interval
                if idx >= len(demand_5min):
                    break

                demand_mw = demand_5min[idx]
                if demand_mw <= 0:
                    continue

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

                # Total load = demand + battery charging (when negative)
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

print(f"\nSaved daily clean energy penetration data (V5) to {OUT_FILE}")
print(f"Processed {len(sorted_data)} days from {list(sorted_data.keys())[0]} to {list(sorted_data.keys())[-1]}")

# Print summary
total_hours_over_100 = sum(d["hours_over_100"] for d in sorted_data.values())
days_with_over_100 = sum(1 for d in sorted_data.values() if d["hours_over_100"] > 0)
if days_with_over_100 > 0:
    max_hours_day = max(sorted_data.items(), key=lambda x: x[1]["hours_over_100"])
    max_penetration_day = max(sorted_data.items(), key=lambda x: x[1]["max_penetration"])

    print(f"\nSummary:")
    print(f"  Total hours >=100% clean energy: {total_hours_over_100:,}")
    print(f"  Days with any hours >=100%: {days_with_over_100:,}")
    print(f"  Peak day for >=100% hours: {max_hours_day[0]} with {max_hours_day[1]['hours_over_100']} hours")
    print(f"  Peak clean energy penetration: {max_penetration_day[1]['max_penetration']:.1f}% on {max_penetration_day[0]}")
