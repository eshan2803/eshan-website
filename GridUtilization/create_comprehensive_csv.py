"""
Create a comprehensive CSV file with all CAISO data:
- 5-minute generation data (from fuelsource CSVs)
- Hourly demand data (from demand CSVs)
- Hourly LMP prices (from caiso_prices.json)
- Hourly ancillary services prices (from ancillary_services.json)

Time-based structure: 5-minute intervals
- Generation: filled for all 5-minute intervals
- Demand, LMP, AS: filled only at :00 minutes (hourly)
"""
import os
import csv
import json
import glob
from datetime import datetime, timedelta
from collections import defaultdict

SUPPLY_DIR = os.path.join(os.path.dirname(__file__), "caiso_supply")
DEMAND_DIR = os.path.join(os.path.dirname(__file__), "caiso_demand_downloads")
OUT_FILE = os.path.join(os.path.dirname(__file__), "caiso_comprehensive_data.csv")

# Load hourly data
print("Loading hourly data...")

# Load LMP prices
with open("caiso_prices.json") as f:
    lmp_data = json.load(f)
print(f"  LMP data: {len(lmp_data)} days")

# Load ancillary services
with open("ancillary_services.json") as f:
    as_data = json.load(f)
print(f"  A/S data: {len(as_data)} days")

# CSV header
HEADER = [
    "timestamp",
    # Generation (5-minute)
    "solar_mw", "wind_mw", "natural_gas_mw", "nuclear_mw", "large_hydro_mw",
    "small_hydro_mw", "geothermal_mw", "biomass_mw", "biogas_mw",
    "batteries_mw", "imports_mw", "other_mw", "coal_mw",
    # Demand (hourly at :00)
    "demand_mw",
    # LMP prices (hourly at :00, $/MWh)
    "lmp", "mcc", "mec", "ghg", "loss",
    # Ancillary services prices (hourly at :00, $/MW)
    "nr", "rd", "rmd", "rmu", "ru", "sr"
]

# Column mapping for fuelsource CSV
FUEL_COLS = {
    "Solar": "solar_mw",
    "Wind": "wind_mw",
    "Natural Gas": "natural_gas_mw",
    "Natural gas": "natural_gas_mw",
    "Nuclear": "nuclear_mw",
    "Large Hydro": "large_hydro_mw",
    "Large hydro": "large_hydro_mw",
    "Small hydro": "small_hydro_mw",
    "Geothermal": "geothermal_mw",
    "Biomass": "biomass_mw",
    "Biogas": "biogas_mw",
    "Batteries": "batteries_mw",
    "Imports": "imports_mw",
    "Other": "other_mw",
    "Coal": "coal_mw"
}

print("\nProcessing fuelsource files...")
files = sorted(glob.glob(os.path.join(SUPPLY_DIR, "*_fuelsource.csv")))
print(f"Found {len(files)} fuelsource CSV files")

# Open output CSV
with open(OUT_FILE, "w", newline="", encoding="utf-8") as out_f:
    writer = csv.DictWriter(out_f, fieldnames=HEADER)
    writer.writeheader()

    processed_days = 0

    for i, fpath in enumerate(files):
        basename = os.path.basename(fpath)
        date_str_raw = basename.split("_")[0]

        try:
            dt = datetime.strptime(date_str_raw, "%Y%m%d")
        except ValueError:
            continue

        date_key = dt.strftime("%Y-%m-%d")

        # Load demand for this day (hourly)
        demand_file = os.path.join(DEMAND_DIR, f"{date_str_raw}_demand.csv")
        demand_hourly = {}

        if os.path.exists(demand_file):
            try:
                with open(demand_file, "r", encoding="utf-8-sig") as f:
                    lines = f.readlines()
                    if len(lines) >= 2:
                        demand_line = lines[1].strip().split(",")
                        demand_values = [float(x) if x.strip() else None for x in demand_line[1:25]]
                        if len(demand_values) >= 24:
                            for hour in range(24):
                                demand_hourly[hour] = demand_values[hour]
            except:
                pass

        # Get LMP prices for this day (hourly)
        lmp_hourly = {}
        if date_key in lmp_data:
            for hour_str, prices in lmp_data[date_key].items():
                try:
                    hour = int(hour_str) - 1  # Convert 1-24 to 0-23
                    lmp_hourly[hour] = prices
                except:
                    pass

        # Get A/S prices for this day (hourly)
        as_hourly = {}
        if date_key in as_data:
            for hour_str, as_prices in as_data[date_key].items():
                try:
                    hour = int(hour_str) - 1  # Convert 1-24 to 0-23
                    as_hourly[hour] = as_prices
                except:
                    pass

        # Process fuelsource data (5-minute intervals)
        try:
            with open(fpath, "r", newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)

                for row in reader:
                    time_str = row.get("Time", "")
                    if not time_str:
                        continue

                    try:
                        # Parse time (format: "HH:MM")
                        time_parts = time_str.split(":")
                        hour = int(time_parts[0])
                        minute = int(time_parts[1])

                        # Create timestamp
                        timestamp = datetime(dt.year, dt.month, dt.day, hour, minute)

                    except (ValueError, IndexError):
                        continue

                    # Build row data
                    row_data = {"timestamp": timestamp.strftime("%Y-%m-%d %H:%M")}

                    # Add generation data (5-minute)
                    for fuel_col, csv_col in FUEL_COLS.items():
                        try:
                            val = float(row.get(fuel_col) or 0)
                            row_data[csv_col] = round(val, 2)
                        except (ValueError, TypeError):
                            row_data[csv_col] = ""

                    # Add hourly data only at :00 minutes
                    if minute == 0:
                        # Demand
                        row_data["demand_mw"] = round(demand_hourly.get(hour, ""), 2) if hour in demand_hourly else ""

                        # LMP prices
                        if hour in lmp_hourly:
                            row_data["lmp"] = round(lmp_hourly[hour].get("LMP", ""), 2)
                            row_data["mcc"] = round(lmp_hourly[hour].get("MCC", ""), 2)
                            row_data["mec"] = round(lmp_hourly[hour].get("MEC", ""), 2)
                            row_data["ghg"] = round(lmp_hourly[hour].get("GHG", ""), 2)
                            row_data["loss"] = round(lmp_hourly[hour].get("Loss", ""), 2)
                        else:
                            row_data["lmp"] = ""
                            row_data["mcc"] = ""
                            row_data["mec"] = ""
                            row_data["ghg"] = ""
                            row_data["loss"] = ""

                        # A/S prices
                        if hour in as_hourly:
                            row_data["nr"] = round(as_hourly[hour].get("NR", ""), 2)
                            row_data["rd"] = round(as_hourly[hour].get("RD", ""), 2)
                            row_data["rmd"] = round(as_hourly[hour].get("RMD", ""), 2)
                            row_data["rmu"] = round(as_hourly[hour].get("RMU", ""), 2)
                            row_data["ru"] = round(as_hourly[hour].get("RU", ""), 2)
                            row_data["sr"] = round(as_hourly[hour].get("SR", ""), 2)
                        else:
                            row_data["nr"] = ""
                            row_data["rd"] = ""
                            row_data["rmd"] = ""
                            row_data["rmu"] = ""
                            row_data["ru"] = ""
                            row_data["sr"] = ""
                    else:
                        # Empty hourly columns for non-:00 minutes
                        for col in ["demand_mw", "lmp", "mcc", "mec", "ghg", "loss",
                                   "nr", "rd", "rmd", "rmu", "ru", "sr"]:
                            row_data[col] = ""

                    writer.writerow(row_data)

        except Exception as e:
            print(f"  ERROR processing {basename}: {e}")
            continue

        processed_days += 1

        if (i + 1) % 500 == 0 or (i + 1) == len(files):
            print(f"  Processed {i+1}/{len(files)} files ({processed_days} days written)")

print(f"\nSaved comprehensive data to {OUT_FILE}")
print(f"Processed {processed_days} days")
print()
print("CSV Structure:")
print("  - Timestamp: 5-minute intervals (YYYY-MM-DD HH:MM)")
print("  - Generation: All 5-minute intervals (MW)")
print("  - Demand: Hourly at :00 only (MW)")
print("  - LMP prices: Hourly at :00 only ($/MWh)")
print("  - A/S prices: Hourly at :00 only ($/MW)")
print()
print("To append new data in the future:")
print("  1. Add new fuelsource CSV files to caiso_supply/")
print("  2. Add new demand CSV files to caiso_demand_downloads/")
print("  3. Update caiso_prices.json and ancillary_services.json")
print("  4. Re-run this script (it will regenerate the complete file)")
