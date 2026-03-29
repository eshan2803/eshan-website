"""
Process CAISO fuel-source CSVs to calculate daily energy totals (MWh).

Categories:
  - Natural Gas
  - Clean Energy (renewables + nuclear + large hydro + battery discharge)
  - Imports
  - Gross Demand (total consumption)

Outputs:
  - daily_energy_breakdown.json: Daily MWh by category and clean %
"""
import os
import csv
import json
import glob
from datetime import datetime
from collections import defaultdict

SUPPLY_DIR = os.path.join(os.path.dirname(__file__), "caiso_supply")
OUT_FILE = os.path.join(os.path.dirname(__file__), "daily_energy_breakdown.json")

# Clean energy sources
CLEAN_SOURCES = [
    "Solar", "Wind", "Geothermal", "Biomass", "Biogas", "Small hydro",
    "Nuclear", "Large Hydro", "Large hydro"  # Handle both capitalizations
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

    # Accumulate MWh for each category (5-min intervals = 1/12 hour)
    gas_mwh = 0.0
    clean_mwh = 0.0
    imports_mwh = 0.0
    gross_demand_mwh = 0.0

    try:
        with open(fpath, "r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)

            for row in reader:
                # Get natural gas (handle both capitalizations)
                try:
                    gas_mw = float(row.get("Natural Gas") or row.get("Natural gas") or 0)
                except (ValueError, TypeError):
                    gas_mw = 0.0

                # Get imports
                try:
                    imports_mw = float(row.get("Imports") or 0)
                except (ValueError, TypeError):
                    imports_mw = 0.0

                # Get clean energy sources
                clean_mw = 0.0
                for col in CLEAN_SOURCES:
                    try:
                        val = float(row.get(col) or 0)
                        clean_mw += val
                    except (ValueError, TypeError):
                        pass

                # Get battery discharge (positive battery = discharge = supply)
                try:
                    battery_mw = float(row.get("Batteries") or 0)
                    if battery_mw > 0:  # Only count discharge as clean supply
                        clean_mw += battery_mw
                except (ValueError, TypeError):
                    pass

                # Calculate gross demand (everything except battery charging)
                # Gross demand = all generation sources
                net_demand_mw = 0.0
                for col in ["Solar", "Wind", "Geothermal", "Biomass", "Biogas", "Small hydro",
                           "Coal", "Nuclear", "Large Hydro", "Large hydro", "Natural Gas",
                           "Natural gas", "Batteries", "Imports", "Other"]:
                    try:
                        val = float(row.get(col) or 0)
                        net_demand_mw += val
                    except (ValueError, TypeError):
                        pass

                # Gross demand excludes battery charging (negative battery values)
                try:
                    battery_mw_all = float(row.get("Batteries") or 0)
                    gross_demand_mw_interval = net_demand_mw - min(battery_mw_all, 0)
                except (ValueError, TypeError):
                    gross_demand_mw_interval = net_demand_mw

                # Accumulate MWh (5-min interval = 1/12 hour)
                interval_hours = 1.0 / 12.0
                gas_mwh += gas_mw * interval_hours
                clean_mwh += clean_mw * interval_hours
                imports_mwh += imports_mw * interval_hours
                gross_demand_mwh += gross_demand_mw_interval * interval_hours

    except Exception as e:
        print(f"  ERROR reading {basename}: {e}")
        continue

    # Calculate clean %
    total_supply = gas_mwh + clean_mwh + imports_mwh
    if total_supply > 0:
        clean_pct = (clean_mwh / total_supply) * 100.0
    else:
        clean_pct = 0.0

    daily_data[date_key] = {
        "natural_gas_mwh": round(gas_mwh, 2),
        "clean_mwh": round(clean_mwh, 2),
        "imports_mwh": round(imports_mwh, 2),
        "gross_demand_mwh": round(gross_demand_mwh, 2),
        "clean_pct": round(clean_pct, 2)
    }

    if (i + 1) % 500 == 0 or (i + 1) == len(files):
        print(f"  Processed {i+1}/{len(files)} files ...")

# Sort and save
sorted_daily = dict(sorted(daily_data.items()))
with open(OUT_FILE, "w") as f:
    json.dump(sorted_daily, f, indent=2)

print(f"\nSaved daily energy breakdown to {OUT_FILE}")
print(f"Processed {len(sorted_daily)} days from {list(sorted_daily.keys())[0]} to {list(sorted_daily.keys())[-1]}")

# Print summary statistics
all_gas = [d["natural_gas_mwh"] for d in sorted_daily.values()]
all_clean = [d["clean_mwh"] for d in sorted_daily.values()]
all_imports = [d["imports_mwh"] for d in sorted_daily.values()]
all_demand = [d["gross_demand_mwh"] for d in sorted_daily.values()]
all_clean_pct = [d["clean_pct"] for d in sorted_daily.values()]

print(f"\nSummary:")
print(f"  Average daily natural gas: {sum(all_gas)/len(all_gas):,.0f} MWh")
print(f"  Average daily clean energy: {sum(all_clean)/len(all_clean):,.0f} MWh")
print(f"  Average daily imports: {sum(all_imports)/len(all_imports):,.0f} MWh")
print(f"  Average daily gross demand: {sum(all_demand)/len(all_demand):,.0f} MWh")
print(f"  Average clean %: {sum(all_clean_pct)/len(all_clean_pct):.1f}%")
