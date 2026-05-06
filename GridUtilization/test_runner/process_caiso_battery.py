"""
Process CAISO fuel-source CSVs to compute daily peak battery discharge, total daily charging, and total daily solar generation.

For each day, for each 5-min interval:
  - battery_mw = "Batteries" column value
  - solar_mw = "Solar" column value
  - demand_mw  = sum of ALL fuel-source columns (Solar + Wind + ... + Imports + Other)
  - If battery_mw > 0 (discharging) and demand_mw > 0: pct = battery_mw / demand_mw * 100
  - If battery_mw < 0 (charging): accumulate |battery_mw| * (5/60) hours to get MWh
  - Accumulate solar_mw * (5/60) hours to get solar MWh

Outputs:
  - caiso_battery_daily_peak.json          {"YYYY-MM-DD": peak_pct, ...}
  - caiso_battery_daily_peak_mw.json       {"YYYY-MM-DD": peak_mw, ...}
  - caiso_battery_daily_charging_mwh.json  {"YYYY-MM-DD": total_charging_mwh, ...}
  - caiso_solar_daily_generation_mwh.json  {"YYYY-MM-DD": total_solar_mwh, ...}
"""
import os
import csv
import json
import glob
from datetime import datetime

SUPPLY_DIR = os.path.join(os.path.dirname(__file__), "caiso_supply")
OUT_FILE_PCT = os.path.join(os.path.dirname(__file__), "caiso_battery_daily_peak.json")
OUT_FILE_MW  = os.path.join(os.path.dirname(__file__), "caiso_battery_daily_peak_mw.json")
OUT_FILE_CHARGING = os.path.join(os.path.dirname(__file__), "caiso_battery_daily_charging_mwh.json")
OUT_FILE_SOLAR = os.path.join(os.path.dirname(__file__), "caiso_solar_daily_generation_mwh.json")

# These are the value columns (everything except Time)
VALUE_COLS = [
    "Solar", "Wind", "Geothermal", "Biomass", "Biogas", "Small hydro",
    "Coal", "Nuclear", "Natural gas", "Large hydro", "Batteries",
    "Imports", "Other",
]

daily_peak_pct = {}
daily_peak_mw = {}
daily_charging_mwh = {}
daily_solar_mwh = {}
files = sorted(glob.glob(os.path.join(SUPPLY_DIR, "*_fuelsource.csv")))
print(f"Found {len(files)} fuelsource CSV files")

for i, fpath in enumerate(files):
    basename = os.path.basename(fpath)          # e.g. 20200101_fuelsource.csv
    date_str_raw = basename.split("_")[0]       # 20200101
    try:
        dt = datetime.strptime(date_str_raw, "%Y%m%d")
    except ValueError:
        continue
    date_key = dt.strftime("%Y-%m-%d")          # 2020-01-01

    max_pct = None
    max_mw = None
    total_charging_mwh = 0.0  # Sum of negative battery values * (5/60) hours
    total_solar_mwh = 0.0  # Sum of solar generation * (5/60) hours

    try:
        with open(fpath, "r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Parse battery MW
                try:
                    battery_mw = float(row.get("Batteries", 0) or 0)
                except (ValueError, TypeError):
                    continue

                # Parse solar MW
                try:
                    solar_mw = float(row.get("Solar", 0) or 0)
                    if solar_mw > 0:
                        total_solar_mwh += solar_mw * (5.0 / 60.0)
                except (ValueError, TypeError):
                    pass

                # Track charging (negative values)
                if battery_mw < 0:
                    # Convert MW to MWh: |battery_mw| * (5 minutes / 60 minutes per hour)
                    total_charging_mwh += abs(battery_mw) * (5.0 / 60.0)
                    continue  # Skip to next row for charging

                if battery_mw <= 0:
                    continue

                # Sum all generation columns for demand (only for discharging)
                demand_mw = 0.0
                for col in VALUE_COLS:
                    try:
                        demand_mw += float(row.get(col, 0) or 0)
                    except (ValueError, TypeError):
                        pass

                if demand_mw <= 0:
                    continue

                pct = battery_mw / demand_mw * 100.0

                if max_pct is None or pct > max_pct:
                    max_pct = pct

                if max_mw is None or battery_mw > max_mw:
                    max_mw = battery_mw

    except Exception as e:
        print(f"  ERROR reading {basename}: {e}")
        continue

    if max_pct is not None:
        daily_peak_pct[date_key] = round(max_pct, 4)
    if max_mw is not None:
        daily_peak_mw[date_key] = round(max_mw, 2)
    if total_charging_mwh > 0:
        daily_charging_mwh[date_key] = round(total_charging_mwh, 2)
    if total_solar_mwh > 0:
        daily_solar_mwh[date_key] = round(total_solar_mwh, 2)

    if (i + 1) % 500 == 0 or (i + 1) == len(files):
        print(f"  Processed {i+1}/{len(files)} files ...")

# Sort by date and save all files
sorted_peak_pct = dict(sorted(daily_peak_pct.items()))
sorted_peak_mw = dict(sorted(daily_peak_mw.items()))
sorted_charging_mwh = dict(sorted(daily_charging_mwh.items()))
sorted_solar_mwh = dict(sorted(daily_solar_mwh.items()))

with open(OUT_FILE_PCT, "w") as f:
    json.dump(sorted_peak_pct, f, indent=1)

with open(OUT_FILE_MW, "w") as f:
    json.dump(sorted_peak_mw, f, indent=1)

with open(OUT_FILE_CHARGING, "w") as f:
    json.dump(sorted_charging_mwh, f, indent=1)

with open(OUT_FILE_SOLAR, "w") as f:
    json.dump(sorted_solar_mwh, f, indent=1)

print(f"\nSaved {len(sorted_peak_pct)} daily peak percentage values to {OUT_FILE_PCT}")
if sorted_peak_pct:
    vals = list(sorted_peak_pct.values())
    print(f"  Percentage range: {min(vals):.2f}% to {max(vals):.2f}%")
    print(f"  Date range: {list(sorted_peak_pct.keys())[0]} to {list(sorted_peak_pct.keys())[-1]}")

print(f"\nSaved {len(sorted_peak_mw)} daily peak MW values to {OUT_FILE_MW}")
if sorted_peak_mw:
    vals_mw = list(sorted_peak_mw.values())
    print(f"  MW range: {min(vals_mw):.2f} MW to {max(vals_mw):.2f} MW ({max(vals_mw)/1000:.2f} GW)")
    print(f"  Date range: {list(sorted_peak_mw.keys())[0]} to {list(sorted_peak_mw.keys())[-1]}")

print(f"\nSaved {len(sorted_charging_mwh)} daily charging values to {OUT_FILE_CHARGING}")
if sorted_charging_mwh:
    vals_charging = list(sorted_charging_mwh.values())
    print(f"  Charging range: {min(vals_charging):.2f} MWh to {max(vals_charging):.2f} MWh ({max(vals_charging)/1000:.2f} GWh)")
    print(f"  Date range: {list(sorted_charging_mwh.keys())[0]} to {list(sorted_charging_mwh.keys())[-1]}")

print(f"\nSaved {len(sorted_solar_mwh)} daily solar generation values to {OUT_FILE_SOLAR}")
if sorted_solar_mwh:
    vals_solar = list(sorted_solar_mwh.values())
    print(f"  Solar range: {min(vals_solar):.2f} MWh to {max(vals_solar):.2f} MWh ({max(vals_solar)/1000:.2f} GWh)")
    print(f"  Date range: {list(sorted_solar_mwh.keys())[0]} to {list(sorted_solar_mwh.keys())[-1]}")
