"""
Process CAISO fuel-source CSVs to extract natural gas generation and penetration data.

Outputs:
  - natural_gas_hourly.json: Hourly natural gas generation (MW) and % of gross demand
  - natural_gas_daily.json: Daily statistics (avg MW, avg %, min %, max %)
"""
import os
import csv
import json
import glob
from datetime import datetime
from collections import defaultdict

SUPPLY_DIR = os.path.join(os.path.dirname(__file__), "caiso_supply")
OUT_FILE_HOURLY = os.path.join(os.path.dirname(__file__), "natural_gas_hourly.json")
OUT_FILE_DAILY = os.path.join(os.path.dirname(__file__), "natural_gas_daily.json")

# All generation columns for demand calculation
VALUE_COLS = [
    "Solar", "Wind", "Geothermal", "Biomass", "Biogas", "Small hydro",
    "Coal", "Nuclear", "Natural Gas", "Large Hydro", "Batteries",
    "Imports", "Other",
]

hourly_data = {}
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
    hourly_intervals = defaultdict(lambda: {"gas_mw": [], "gas_pct": []})

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

                # Get natural gas generation (handle both "Natural Gas" and "Natural gas")
                try:
                    gas_mw = float(row.get("Natural Gas") or row.get("Natural gas") or 0)
                except (ValueError, TypeError):
                    continue

                # Calculate net demand (includes all sources including batteries)
                # Handle both "Natural Gas"/"Natural gas" and "Large Hydro"/"Large hydro"
                net_demand_mw = 0.0
                battery_mw = 0.0
                for col in VALUE_COLS:
                    try:
                        # Try both uppercase and lowercase versions
                        if col == "Natural Gas":
                            val = float(row.get("Natural Gas") or row.get("Natural gas") or 0)
                        elif col == "Large Hydro":
                            val = float(row.get("Large Hydro") or row.get("Large hydro") or 0)
                        else:
                            val = float(row.get(col, 0) or 0)

                        if col == "Batteries":
                            battery_mw = val
                        net_demand_mw += val
                    except (ValueError, TypeError):
                        pass

                # Calculate GROSS demand (actual California consumption)
                gross_demand_mw = net_demand_mw - min(battery_mw, 0)

                # Calculate gas percentage of gross demand
                if gross_demand_mw > 0:
                    gas_pct = (gas_mw / gross_demand_mw) * 100.0
                    hourly_intervals[hour]["gas_mw"].append(gas_mw)
                    hourly_intervals[hour]["gas_pct"].append(gas_pct)

    except Exception as e:
        print(f"  ERROR reading {basename}: {e}")
        continue

    # Calculate hourly averages
    for hour, data in hourly_intervals.items():
        if data["gas_mw"]:
            hour_key = f"{date_key} {hour:02d}"
            avg_gas_mw = sum(data["gas_mw"]) / len(data["gas_mw"])
            avg_gas_pct = sum(data["gas_pct"]) / len(data["gas_pct"])

            hourly_data[hour_key] = {
                "gas_mw": round(avg_gas_mw, 2),
                "gas_pct": round(avg_gas_pct, 2)
            }

    # Calculate daily statistics
    all_gas_mw = []
    all_gas_pct = []
    for data in hourly_intervals.values():
        all_gas_mw.extend(data["gas_mw"])
        all_gas_pct.extend(data["gas_pct"])

    if all_gas_mw:
        daily_data[date_key] = {
            "avg_gas_mw": round(sum(all_gas_mw) / len(all_gas_mw), 2),
            "min_gas_mw": round(min(all_gas_mw), 2),
            "max_gas_mw": round(max(all_gas_mw), 2),
            "avg_gas_pct": round(sum(all_gas_pct) / len(all_gas_pct), 2),
            "min_gas_pct": round(min(all_gas_pct), 2),
            "max_gas_pct": round(max(all_gas_pct), 2)
        }

    if (i + 1) % 500 == 0 or (i + 1) == len(files):
        print(f"  Processed {i+1}/{len(files)} files ...")

# Save hourly data
with open(OUT_FILE_HOURLY, "w") as f:
    json.dump(hourly_data, f, indent=2)

print(f"\nSaved hourly natural gas data to {OUT_FILE_HOURLY}")
print(f"Processed {len(hourly_data)} hours")

# Sort and save daily data
sorted_daily = dict(sorted(daily_data.items()))
with open(OUT_FILE_DAILY, "w") as f:
    json.dump(sorted_daily, f, indent=2)

print(f"Saved daily natural gas data to {OUT_FILE_DAILY}")
print(f"Processed {len(sorted_daily)} days from {list(sorted_daily.keys())[0]} to {list(sorted_daily.keys())[-1]}")

# Print summary statistics
all_avg_gas_mw = [d["avg_gas_mw"] for d in sorted_daily.values()]
all_avg_gas_pct = [d["avg_gas_pct"] for d in sorted_daily.values()]

print(f"\nSummary:")
print(f"  Average daily gas generation: {sum(all_avg_gas_mw)/len(all_avg_gas_mw):.0f} MW")
print(f"  Average gas % of demand: {sum(all_avg_gas_pct)/len(all_avg_gas_pct):.1f}%")
print(f"  Min daily gas generation: {min(all_avg_gas_mw):.0f} MW")
print(f"  Max daily gas generation: {max(all_avg_gas_mw):.0f} MW")
