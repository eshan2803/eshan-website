"""
Generate HOURLY clean energy penetration data for 2026 Q1 with CORRECTED calculation.

Uses renewables CSV files which include the demand row.
"""
import os
import csv
import json
import glob
from datetime import datetime
from collections import defaultdict

DOWNLOADS_DIR = os.path.join(os.path.dirname(__file__), "caiso_downloads")
SUPPLY_DIR = os.path.join(os.path.dirname(__file__), "caiso_supply")
OUT_FILE = os.path.join(os.path.dirname(__file__), "renewable_penetration_hourly_2026q1_corrected.json")

CLEAN_COLS = ["Solar", "Wind", "Geothermal", "Biomass", "Biogas", "Small hydro", "Nuclear", "Large Hydro"]

hourly_penetration = {}

# Get 2026 Q1 files
renewables_files = sorted(glob.glob(os.path.join(DOWNLOADS_DIR, "2026*_renewables_raw.csv")))
print(f"Found {len(renewables_files)} renewables CSV files for 2026 Q1")

processed_hours = 0

for i, renewables_file in enumerate(renewables_files):
    basename = os.path.basename(renewables_file)
    date_str_raw = basename.split("_")[0]

    try:
        dt = datetime.strptime(date_str_raw, "%Y%m%d")
    except ValueError:
        continue

    date_key = dt.strftime("%Y-%m-%d")

    # Read demand from renewables CSV
    demand_5min = []
    try:
        with open(renewables_file, "r", encoding="utf-8-sig") as f:
            for line in f:
                if line.startswith("Demand,"):
                    demand_5min = [float(x) for x in line.strip().split(",")[1:] if x.strip()]
                    break

        if not demand_5min:
            continue

    except Exception as e:
        continue

    # Get fuelsource data
    fuelsource_file = os.path.join(SUPPLY_DIR, f"{date_str_raw}_fuelsource.csv")
    if not os.path.exists(fuelsource_file):
        continue

    # Process fuelsource - aggregate 5-minute to hourly
    hourly_clean_mw = defaultdict(list)
    hourly_load_mw = defaultdict(list)

    try:
        with open(fuelsource_file, "r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)

            for idx, row in enumerate(reader):
                if idx >= len(demand_5min):
                    break

                time_str = row.get("Time", "")
                if not time_str:
                    continue

                try:
                    time_parts = time_str.split(":")
                    hour = int(time_parts[0])
                except (ValueError, IndexError):
                    continue

                demand_mw = demand_5min[idx]
                if demand_mw <= 0:
                    continue

                # Clean energy
                clean_mw = 0.0
                for col in CLEAN_COLS:
                    try:
                        clean_mw += float(row.get(col, 0) or 0)
                    except (ValueError, TypeError):
                        pass

                # Battery
                battery_mw = 0.0
                try:
                    battery_mw = float(row.get("Batteries", 0) or 0)
                    if battery_mw > 0:
                        clean_mw += battery_mw
                except (ValueError, TypeError):
                    pass

                # CORRECT: Total load = demand + battery charging
                total_load = demand_mw + abs(min(battery_mw, 0))

                if total_load > 0:
                    hourly_clean_mw[hour].append(clean_mw)
                    hourly_load_mw[hour].append(total_load)

    except Exception as e:
        continue

    # Calculate hourly averages
    for hour in sorted(set(hourly_clean_mw.keys()) & set(hourly_load_mw.keys())):
        avg_clean = sum(hourly_clean_mw[hour]) / len(hourly_clean_mw[hour])
        avg_load = sum(hourly_load_mw[hour]) / len(hourly_load_mw[hour])

        if avg_load > 0:
            hourly_pct = (avg_clean / avg_load) * 100.0
            hour_key = f"{date_key} {hour:02d}"
            hourly_penetration[hour_key] = round(hourly_pct, 2)
            processed_hours += 1

    if (i + 1) % 30 == 0 or (i + 1) == len(renewables_files):
        print(f"  Processed {i+1}/{len(renewables_files)} files - {processed_hours} hours generated")

# Sort and save
sorted_data = dict(sorted(hourly_penetration.items()))

with open(OUT_FILE, "w") as f:
    json.dump(sorted_data, f, indent=2)

print(f"\nSaved to {OUT_FILE}")
print(f"Total hours: {len(sorted_data):,}")
if sorted_data:
    keys = list(sorted_data.keys())
    print(f"Date range: {keys[0]} to {keys[-1]}")

hours_over_100 = sum(1 for v in sorted_data.values() if v >= 100)
print(f"Hours >=100%: {hours_over_100:,}")
