"""
Process CAISO fuel-source CSVs to calculate daily clean energy penetration (ENERGY-BASED).

This version calculates: Total Clean Energy (MWh) / Total Load (MWh) × 100

Key differences from V3:
- V3: Averages hourly percentages -> avg_penetration = average(clean[h]/load[h])
- This: Calculates percentage of totals -> penetration = sum(clean_mwh) / sum(load_mwh) × 100

Methodology:
1. clean_mw = Solar + Wind + Geothermal + Biomass + Biogas + Small hydro + Battery discharge + Nuclear + Large hydro
2. gross_demand_mw = Sum of all generation sources (excludes battery charging, includes battery discharge)
3. For each 5-minute interval: accumulate clean_mwh and load_mwh
4. Daily penetration = total_clean_mwh / total_load_mwh × 100

Output: renewable_penetration_daily_energy_based.json
{
  "YYYY-MM-DD": {
    "hours_over_100": count,
    "avg_oversupply_pct": average_excess_when_over_100,
    "avg_penetration": energy_based_penetration,  <- This is the key change
    "max_penetration": peak_clean_pct,
    "total_clean_mwh": total_clean_energy,
    "total_load_mwh": total_load
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
OUT_FILE = os.path.join(os.path.dirname(__file__), "renewable_penetration_daily_energy_based.json")

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

    # Collect 5-min intervals grouped by hour (for hourly stats)
    hourly_penetration = []
    hourly_data = defaultdict(list)

    # Accumulate totals for energy-based calculation
    total_clean_mwh = 0.0
    total_load_mwh = 0.0

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
                gross_demand_mw = net_demand_mw - min(battery_mw, 0)

                # Calculate penetration percentage for this 5-min interval (for hourly stats)
                if gross_demand_mw > 0:
                    clean_pct = (clean_mw / gross_demand_mw) * 100.0
                    hourly_data[hour].append(clean_pct)

                # Accumulate energy totals (5-min interval = 1/12 hour)
                interval_hours = 1.0 / 12.0
                total_clean_mwh += clean_mw * interval_hours
                total_load_mwh += gross_demand_mw * interval_hours

    except Exception as e:
        print(f"  ERROR reading {basename}: {e}")
        continue

    # Compute hourly averages (for hours_over_100 and max_penetration stats)
    for hour, pct_values in hourly_data.items():
        if pct_values:
            avg_pct = sum(pct_values) / len(pct_values)
            hourly_penetration.append(avg_pct)

    # Calculate daily statistics
    if hourly_penetration and total_load_mwh > 0:
        hours_over_100 = sum(1 for p in hourly_penetration if p >= 100)
        oversupply_values = [p - 100 for p in hourly_penetration if p >= 100]
        avg_oversupply = (sum(oversupply_values) / len(oversupply_values)) if oversupply_values else 0.0
        max_penetration = max(hourly_penetration)

        # KEY CHANGE: Energy-based penetration instead of averaging hourly percentages
        energy_based_penetration = (total_clean_mwh / total_load_mwh) * 100.0

        daily_data[date_key] = {
            "hours_over_100": hours_over_100,
            "avg_oversupply_pct": round(avg_oversupply, 2),
            "avg_penetration": round(energy_based_penetration, 2),  # <- Changed from averaging hourly %
            "max_penetration": round(max_penetration, 2),
            "total_clean_mwh": round(total_clean_mwh, 2),
            "total_load_mwh": round(total_load_mwh, 2)
        }

    if (i + 1) % 500 == 0 or (i + 1) == len(files):
        print(f"  Processed {i+1}/{len(files)} files ...")

# Sort by date and save
sorted_data = dict(sorted(daily_data.items()))

with open(OUT_FILE, "w") as f:
    json.dump(sorted_data, f, indent=2)

print(f"\nSaved daily clean energy penetration data (ENERGY-BASED) to {OUT_FILE}")
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

# Compare May 24, 2025 specifically
if "2025-05-24" in sorted_data:
    may24 = sorted_data["2025-05-24"]
    print(f"\nMay 24, 2025 Verification:")
    print(f"  Energy-based penetration: {may24['avg_penetration']:.2f}%")
    print(f"  Total clean energy: {may24['total_clean_mwh']:,.0f} MWh")
    print(f"  Total load: {may24['total_load_mwh']:,.0f} MWh")
    print(f"  Expected: 90.65%")
