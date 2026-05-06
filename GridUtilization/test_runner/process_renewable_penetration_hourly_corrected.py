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

    # Read demand CSV (Row 3 = Actual Demand, 5-minute intervals)
    try:
        with open(demand_file, "r", encoding="utf-8-sig") as f:
            lines = f.readlines()
            if len(lines) < 5:  # Need at least 5 rows (header + 3 forecast rows + actual)
                skipped_no_demand += 1
                continue

            # Parse header to get time intervals
            header_line = lines[0].strip().split(",")
            time_labels = header_line[1:]  # Skip first column

            # Row 3 (index 3) has actual demand at 5-minute intervals
            demand_line = lines[3].strip().split(",")
            demand_values_5min = [float(x) if x.strip() else None for x in demand_line[1:]]

            # Create dict of demand by (hour, minute)
            demand_by_time = {}
            for idx, (time_label, demand_val) in enumerate(zip(time_labels, demand_values_5min)):
                if demand_val is not None:
                    try:
                        hour, minute = map(int, time_label.strip().split(":"))
                        demand_by_time[(hour, minute)] = demand_val
                    except:
                        pass

            if len(demand_by_time) < 100:  # Should have ~288 intervals
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

            # Build case-insensitive column map once per file
            col_map = None

            for row in reader:
                if col_map is None:
                    col_map = {c.lower(): c for c in row.keys()}

                time_str = row.get("Time", "")
                if not time_str:
                    continue

                try:
                    time_parts = time_str.split(":")
                    hour = int(time_parts[0])
                    minute = int(time_parts[1])
                except (ValueError, IndexError):
                    continue

                # Get demand for this 5-minute interval
                if (hour, minute) not in demand_by_time:
                    continue

                demand_mw = demand_by_time[(hour, minute)]
                if demand_mw is None or demand_mw <= 0:
                    continue

                # Helper to get value with case-insensitive column name
                def get_val(col_name):
                    actual = col_map.get(col_name.lower(), col_name)
                    try:
                        return float(row.get(actual, 0) or 0)
                    except (ValueError, TypeError):
                        return 0.0

                # Clean energy
                clean_mw = 0.0
                for col in CLEAN_COLS:
                    clean_mw += get_val(col)

                # Battery
                battery_mw = get_val("Batteries")
                if battery_mw > 0:
                    clean_mw += battery_mw

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
