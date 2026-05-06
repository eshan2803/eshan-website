"""
Process CAISO fuel-source CSVs to calculate renewable energy penetration.

For each hour, calculate:
  - renewable_mw = Solar + Wind + Geothermal + Biomass + Biogas + Small hydro
  - demand_mw = sum of ALL fuel-source columns
  - renewable_pct = renewable_mw / demand_mw * 100

Count hours with >100% renewable penetration and calculate excess.

Outputs:
  - renewable_penetration_monthly.json  {
      "YYYY-MM": {
        "hours_over_100": count,
        "avg_excess_pct": average_excess_when_over_100,
        "max_penetration": peak_renewable_pct
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
OUT_FILE = os.path.join(os.path.dirname(__file__), "renewable_penetration_monthly.json")

# Renewable sources
RENEWABLE_COLS = ["Solar", "Wind", "Geothermal", "Biomass", "Biogas", "Small hydro"]

# All generation columns (for demand calculation)
VALUE_COLS = [
    "Solar", "Wind", "Geothermal", "Biomass", "Biogas", "Small hydro",
    "Coal", "Nuclear", "Natural gas", "Large hydro", "Batteries",
    "Imports", "Other",
]

monthly_data = defaultdict(lambda: {
    "hours_over_100": 0,
    "excess_values": [],
    "all_penetration": []
})

files = sorted(glob.glob(os.path.join(SUPPLY_DIR, "*_fuelsource.csv")))
print(f"Found {len(files)} fuelsource CSV files")

for i, fpath in enumerate(files):
    basename = os.path.basename(fpath)
    date_str_raw = basename.split("_")[0]
    try:
        dt = datetime.strptime(date_str_raw, "%Y%m%d")
    except ValueError:
        continue

    month_key = dt.strftime("%Y-%m")

    # Collect 5-min intervals grouped by hour
    hourly_data = defaultdict(list)

    try:
        with open(fpath, "r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Parse time to get hour
                time_str = row.get("Time", "")
                if not time_str:
                    continue

                try:
                    # Time format could be "HH:MM" or "H:MM"
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

                # Calculate total demand
                demand_mw = 0.0
                for col in VALUE_COLS:
                    try:
                        demand_mw += float(row.get(col, 0) or 0)
                    except (ValueError, TypeError):
                        pass

                # Calculate penetration percentage
                if demand_mw > 0:
                    renewable_pct = (renewable_mw / demand_mw) * 100.0
                    hourly_data[hour].append(renewable_pct)

    except Exception as e:
        print(f"  ERROR reading {basename}: {e}")
        continue

    # Process hourly averages
    for hour, pct_values in hourly_data.items():
        if pct_values:
            avg_pct = sum(pct_values) / len(pct_values)
            monthly_data[month_key]["all_penetration"].append(avg_pct)

            if avg_pct > 100.0:
                monthly_data[month_key]["hours_over_100"] += 1
                excess = avg_pct - 100.0
                monthly_data[month_key]["excess_values"].append(excess)

    if (i + 1) % 500 == 0 or (i + 1) == len(files):
        print(f"  Processed {i+1}/{len(files)} files ...")

# Calculate final statistics
output_data = {}
for month_key, data in sorted(monthly_data.items()):
    avg_excess = (sum(data["excess_values"]) / len(data["excess_values"])) if data["excess_values"] else 0.0
    max_penetration = max(data["all_penetration"]) if data["all_penetration"] else 0.0

    output_data[month_key] = {
        "hours_over_100": data["hours_over_100"],
        "avg_excess_pct": round(avg_excess, 2),
        "max_penetration": round(max_penetration, 2)
    }

# Save output
with open(OUT_FILE, "w") as f:
    json.dump(output_data, f, indent=2)

print(f"\nSaved renewable penetration data to {OUT_FILE}")
print(f"Processed {len(output_data)} months from {list(output_data.keys())[0]} to {list(output_data.keys())[-1]}")

# Print summary
total_hours_over_100 = sum(d["hours_over_100"] for d in output_data.values())
max_month_hours = max(output_data.items(), key=lambda x: x[1]["hours_over_100"])
max_penetration_month = max(output_data.items(), key=lambda x: x[1]["max_penetration"])

print(f"\nSummary:")
print(f"  Total hours >100% renewable: {total_hours_over_100:,}")
print(f"  Peak month for >100% hours: {max_month_hours[0]} with {max_month_hours[1]['hours_over_100']} hours")
print(f"  Peak renewable penetration: {max_penetration_month[1]['max_penetration']:.1f}% in {max_penetration_month[0]}")
