"""
Generate HOURLY clean energy penetration data with CORRECTED calculation.

Uses:
  - Fuelsource CSVs for generation data (5-minute intervals)
  - Downloaded demand CSVs from CAISO Today's Outlook (hourly)
  - Load = CSV demand + battery charging (CORRECT)
  - Clean = Renewables + Nuclear + Large Hydro + Battery discharge
"""
import os
import csv
import json
import glob
from datetime import datetime
from collections import defaultdict

SUPPLY_DIR = os.path.join(os.path.dirname(__file__), "caiso_supply")
DEMAND_DIR = os.path.join(os.path.dirname(__file__), "caiso_demand_downloads")
OUT_FILE = os.path.join(os.path.dirname(__file__), "renewable_penetration_hourly_corrected.json")

CLEAN_COLS = ["Solar", "Wind", "Geothermal", "Biomass", "Biogas", "Small hydro", "Nuclear", "Large Hydro"]

hourly_penetration = {}

files = sorted(glob.glob(os.path.join(SUPPLY_DIR, "*_fuelsource.csv")))
print(f"Found {len(files)} fuelsource CSV files")

processed = 0
skipped_no_demand = 0

for i, fpath in enumerate(files):
    basename = os.path.basename(fpath)
    date_str_raw = basename.split("_")[0]
    try:
        dt = datetime.strptime(date_str_raw, "%Y%m%d")
    except ValueError:
        continue

    date_key = dt.strftime("%Y-%m-%d")

    # Load demand from demand CSV
    demand_file = os.path.join(DEMAND_DIR, f"{date_str_raw}_demand.csv")
    if not os.path.exists(demand_file):
        skipped_no_demand += 1
        continue

    # Read demand CSV (format: single row with hourly values)
    try:
        with open(demand_file, "r", encoding="utf-8-sig") as f:
            lines = f.readlines()
            if len(lines) < 2:
                skipped_no_demand += 1
                continue

            demand_line = lines[1].strip().split(",")
            demand_hourly = [float(x) for x in demand_line[1:25] if x.strip()]  # Hours 1-24

            if len(demand_hourly) < 24:
                skipped_no_demand += 1
                continue

    except Exception as e:
        skipped_no_demand += 1
        continue

    # Process fuelsource data - aggregate 5-minute intervals to hourly
    hourly_clean_mw = defaultdict(list)
    hourly_load_mw = defaultdict(list)

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

                # Get demand for this hour
                if hour >= len(demand_hourly):
                    continue

                demand_mw = demand_hourly[hour]
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
        # Average the 5-minute intervals for this hour
        avg_clean = sum(hourly_clean_mw[hour]) / len(hourly_clean_mw[hour])
        avg_load = sum(hourly_load_mw[hour]) / len(hourly_load_mw[hour])

        if avg_load > 0:
            hourly_pct = (avg_clean / avg_load) * 100.0
            hour_key = f"{date_key} {hour:02d}"
            hourly_penetration[hour_key] = round(hourly_pct, 2)
            processed += 1

    if (i + 1) % 500 == 0 or (i + 1) == len(files):
        print(f"  Processed {i+1}/{len(files)} files - {processed} hours generated, {skipped_no_demand} days skipped")

# Sort and save
sorted_data = dict(sorted(hourly_penetration.items()))

with open(OUT_FILE, "w") as f:
    json.dump(sorted_data, f, indent=2)

print(f"\nSaved to {OUT_FILE}")
print(f"Total hours: {len(sorted_data):,}")
if sorted_data:
    keys = list(sorted_data.keys())
    print(f"Date range: {keys[0]} to {keys[-1]}")

# Count hours >100%
hours_over_100 = sum(1 for v in sorted_data.values() if v >= 100)
print(f"\nHours >=100%: {hours_over_100:,} ({hours_over_100/len(sorted_data)*100:.2f}%)")
