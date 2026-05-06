"""
Process CAISO data to calculate clean energy penetration using downloaded demand CSVs.

CORRECTED VERSION: Uses energy-weighted daily average
- Daily avg penetration = (Total Clean MWh / Total Load MWh) * 100
- Not the simple average of hourly percentages

Uses:
  - Fuelsource CSVs for generation data
  - Downloaded demand CSVs from CAISO Today's Outlook
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

    # Process fuelsource data - collect energy totals
    hourly_penetration = []
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

                # Total load = demand + battery charging
                total_load = demand_mw + abs(min(battery_mw, 0))

                if total_load > 0:
                    # Store for energy-weighted calculation
                    hourly_clean_mw[hour].append(clean_mw)
                    hourly_load_mw[hour].append(total_load)

                    # Also calculate instant penetration for hours_over_100 metric
                    clean_pct = (clean_mw / total_load) * 100.0
                    hourly_penetration.append(clean_pct)

    except Exception as e:
        continue

    # Calculate daily statistics
    if hourly_penetration:
        # Hours over 100% (based on instantaneous values)
        hours_over_100 = sum(1 for p in hourly_penetration if p >= 100)

        # Oversupply metrics
        oversupply_values = [p - 100 for p in hourly_penetration if p >= 100]
        avg_oversupply = (sum(oversupply_values) / len(oversupply_values)) if oversupply_values else 0.0

        # Max penetration
        max_penetration = max(hourly_penetration)

        # CORRECTED: Energy-weighted daily average penetration
        # Sum all clean energy and all load across the day
        total_clean_mwh = sum(sum(hourly_clean_mw[h]) for h in hourly_clean_mw)
        total_load_mwh = sum(sum(hourly_load_mw[h]) for h in hourly_load_mw)

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
