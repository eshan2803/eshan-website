"""
Process CAISO data to calculate clean energy penetration using downloaded demand CSVs.

CORRECTED VERSION: Uses energy-weighted daily average
- Properly aggregates 5-minute fuelsource data to hourly
- Daily avg penetration = (Total Clean MWh / Total Load MWh) * 100
- Not the simple average of hourly percentages

Uses:
  - Fuelsource CSVs for generation data (5-minute intervals)
  - Downloaded demand CSVs from CAISO Today's Outlook (hourly)
  - Load = CSV demand + battery charging
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
OUT_FILE = os.path.join(os.path.dirname(__file__), "renewable_penetration_daily_corrected_full.json")

CLEAN_COLS = ["Solar", "Wind", "Geothermal", "Biomass", "Biogas", "Small hydro", "Nuclear", "Large Hydro"]

daily_data = {}

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

            # Usually second line has the demand values
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

                # Get demand for this hour (hour 0 -> index 0, hour 23 -> index 23)
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

                # Total load = demand + battery charging
                total_load = demand_mw + abs(min(battery_mw, 0))

                if total_load > 0:
                    # Store 5-minute values for hourly aggregation
                    hourly_clean_mw[hour].append(clean_mw)
                    hourly_load_mw[hour].append(total_load)

    except Exception as e:
        continue

    # Aggregate to hourly averages and calculate daily statistics
    hourly_penetration = []
    total_clean_mwh = 0.0
    total_load_mwh = 0.0

    for hour in sorted(set(hourly_clean_mw.keys()) & set(hourly_load_mw.keys())):
        # Average the 5-minute intervals for this hour
        avg_clean = sum(hourly_clean_mw[hour]) / len(hourly_clean_mw[hour])
        avg_load = sum(hourly_load_mw[hour]) / len(hourly_load_mw[hour])

        # Calculate hourly penetration %
        if avg_load > 0:
            hourly_pct = (avg_clean / avg_load) * 100.0
            hourly_penetration.append(hourly_pct)

            # Accumulate for energy-weighted daily average
            total_clean_mwh += avg_clean
            total_load_mwh += avg_load

    # Calculate daily statistics
    if hourly_penetration:
        # Hours over 100% (based on hourly averages)
        hours_over_100 = sum(1 for p in hourly_penetration if p >= 100)

        # Oversupply metrics
        oversupply_values = [p - 100 for p in hourly_penetration if p >= 100]
        avg_oversupply = (sum(oversupply_values) / len(oversupply_values)) if oversupply_values else 0.0

        # Max penetration
        max_penetration = max(hourly_penetration)

        # Energy-weighted daily average penetration
        if total_load_mwh > 0:
            avg_penetration = (total_clean_mwh / total_load_mwh) * 100.0
        else:
            avg_penetration = 0.0

        daily_data[date_key] = {
            "hours_over_100": hours_over_100,
            "avg_oversupply_pct": round(avg_oversupply, 2),
            "avg_penetration": round(avg_penetration, 2),
            "max_penetration": round(max_penetration, 2)
        }
        processed += 1

    if (i + 1) % 500 == 0 or (i + 1) == len(files):
        print(f"  Processed {i+1}/{len(files)} files - {processed} with demand data, {skipped_no_demand} skipped")

# Sort and save
sorted_data = dict(sorted(daily_data.items()))

with open(OUT_FILE, "w") as f:
    json.dump(sorted_data, f, indent=2)

print(f"\nSaved to {OUT_FILE}")
print(f"Processed {len(sorted_data)} days from {list(sorted_data.keys())[0]} to {list(sorted_data.keys())[-1]}")

# Summary
total_hours_over_100 = sum(d["hours_over_100"] for d in sorted_data.values())
days_with_over_100 = sum(1 for d in sorted_data.values() if d["hours_over_100"] > 0)
if days_with_over_100 > 0:
    max_hours_day = max(sorted_data.items(), key=lambda x: x[1]["hours_over_100"])
    max_penetration_day = max(sorted_data.items(), key=lambda x: x[1]["max_penetration"])

    print(f"\nSummary:")
    print(f"  Total hours >=100%: {total_hours_over_100:,}")
    print(f"  Days with hours >=100%: {days_with_over_100:,}")
    print(f"  Peak day: {max_hours_day[0]} with {max_hours_day[1]['hours_over_100']} hours")
    print(f"  Peak penetration: {max_penetration_day[1]['max_penetration']:.1f}% on {max_penetration_day[0]}")
