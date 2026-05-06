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

# Load LMP prices — prefer 5-min load-weighted data, fall back to hourly
lmp_5min_data = {}
prices_5min_path = os.path.join(os.path.dirname(__file__), "caiso_prices_5min.json")
if os.path.exists(prices_5min_path):
    with open(prices_5min_path) as f:
        lmp_5min_data = json.load(f)
    print(f"  5-min LMP data: {len(lmp_5min_data)} days")

with open("caiso_prices.json") as f:
    lmp_data = json.load(f)
print(f"  Hourly LMP data: {len(lmp_data)} days")

# Load ancillary services (NR, RD, RMD, RMU, RU, SR)
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
    # Battery breakdown (5-minute)
    "battery_charging_mw", "battery_discharging_mw",
    # Demand and load (hourly at :00)
    "demand_mw", "load_mw",
    # LMP prices (hourly at :00, $/MWh)
    "lmp", "mcc", "mec", "ghg", "loss",
    # Ancillary services prices (hourly at :00, $/MW)
    "nr", "rd", "rmd", "rmu", "ru", "sr"
]

# Column mapping for fuelsource CSV (use list to avoid duplicate key issues)
FUEL_COLS = [
    ("Solar", "solar_mw"),
    ("Wind", "wind_mw"),
    ("Natural Gas", "natural_gas_mw"),
    ("Nuclear", "nuclear_mw"),
    ("Large Hydro", "large_hydro_mw"),
    ("Small hydro", "small_hydro_mw"),
    ("Geothermal", "geothermal_mw"),
    ("Biomass", "biomass_mw"),
    ("Biogas", "biogas_mw"),
    ("Batteries", "batteries_mw"),
    ("Imports", "imports_mw"),
    ("Other", "other_mw"),
    ("Coal", "coal_mw")
]

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

        # Load demand for this day (5-minute intervals, 288 values per day)
        demand_file = os.path.join(DEMAND_DIR, f"{date_str_raw}_demand.csv")
        demand_5min = {}  # Key: (hour, minute) -> Value: demand_mw

        if os.path.exists(demand_file):
            try:
                with open(demand_file, "r", encoding="utf-8-sig") as f:
                    lines = f.readlines()
                    if len(lines) >= 5:  # Row 4 (index 3) has actual demand
                        demand_line = lines[3].strip().split(",")
                        demand_values = [float(x) if x.strip() else None for x in demand_line[1:]]
                        # Parse header to get time intervals
                        header_line = lines[0].strip().split(",")
                        time_labels = header_line[1:]  # Skip first column (label)

                        for idx, (time_label, demand_val) in enumerate(zip(time_labels, demand_values)):
                            if demand_val is not None:
                                try:
                                    # Parse time like "00:00", "00:05", etc.
                                    hour, minute = map(int, time_label.strip().split(":"))
                                    demand_5min[(hour, minute)] = demand_val
                                except:
                                    pass
            except Exception as e:
                pass

        # Get LMP prices — prefer 5-min, fall back to hourly
        lmp_5min = {}
        lmp_hourly = {}
        if date_key in lmp_5min_data:
            for time_str, prices in lmp_5min_data[date_key].items():
                try:
                    parts = time_str.split(":")
                    h, m = int(parts[0]), int(parts[1])
                    lmp_5min[(h, m)] = prices
                except:
                    pass
        if not lmp_5min and date_key in lmp_data:
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
            seen_midnight = False  # Track if we've seen 00:00 already

            with open(fpath, "r", newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)

                for row in reader:
                    time_str = row.get("Time", "")
                    if not time_str:
                        continue

                    try:
                        # Parse time (format: "HH:MM" or "H:MM")
                        time_parts = time_str.split(":")
                        hour = int(time_parts[0])
                        minute = int(time_parts[1])

                        # Skip duplicate "0:00" at end of file (belongs to next day)
                        # CAISO files include next day's 00:00 as the last row
                        if hour == 0 and minute == 0:
                            if seen_midnight:
                                continue  # Skip this duplicate
                            seen_midnight = True

                        # Create timestamp
                        timestamp = datetime(dt.year, dt.month, dt.day, hour, minute)

                    except (ValueError, IndexError):
                        continue

                    # Build row data
                    row_data = {"timestamp": timestamp.strftime("%Y-%m-%d %H:%M")}

                    # Add generation data (5-minute)
                    battery_mw = 0.0
                    for fuel_col, csv_col in FUEL_COLS:
                        try:
                            val = float(row.get(fuel_col) or 0)
                            row_data[csv_col] = round(val, 2)
                            if csv_col == "batteries_mw":
                                battery_mw = val
                        except (ValueError, TypeError):
                            row_data[csv_col] = ""

                    # Calculate battery charging and discharging (5-minute)
                    if battery_mw < 0:
                        row_data["battery_charging_mw"] = round(abs(battery_mw), 2)
                        row_data["battery_discharging_mw"] = 0.0
                    else:
                        row_data["battery_charging_mw"] = 0.0
                        row_data["battery_discharging_mw"] = round(battery_mw, 2)

                    # Add demand and load (5-minute)
                    if (hour, minute) in demand_5min:
                        demand_val = demand_5min[(hour, minute)]
                        row_data["demand_mw"] = round(demand_val, 2)
                        # Load = Demand + Battery Charging
                        charging_val = row_data["battery_charging_mw"]
                        if isinstance(charging_val, (int, float)) and charging_val != "":
                            row_data["load_mw"] = round(demand_val + charging_val, 2)
                        else:
                            row_data["load_mw"] = ""
                    else:
                        row_data["demand_mw"] = ""
                        row_data["load_mw"] = ""

                    # LMP prices — 5-min resolution if available, else hourly at :00
                    if lmp_5min:
                        if (hour, minute) in lmp_5min:
                            for price_key, col_name in [("LMP", "lmp"), ("MCC", "mcc"), ("MEC", "mec"), ("GHG", "ghg"), ("Loss", "loss")]:
                                val = lmp_5min[(hour, minute)].get(price_key, "")
                                if isinstance(val, (int, float)):
                                    row_data[col_name] = round(val, 2)
                                else:
                                    row_data[col_name] = ""
                        else:
                            for col in ["lmp", "mcc", "mec", "ghg", "loss"]:
                                row_data[col] = ""
                    elif minute == 0 and hour in lmp_hourly:
                        for price_key, col_name in [("LMP", "lmp"), ("MCC", "mcc"), ("MEC", "mec"), ("GHG", "ghg"), ("Loss", "loss")]:
                            val = lmp_hourly[hour].get(price_key, "")
                            if isinstance(val, (int, float)):
                                row_data[col_name] = round(val, 2)
                            else:
                                row_data[col_name] = ""
                    else:
                        for col in ["lmp", "mcc", "mec", "ghg", "loss"]:
                            row_data[col] = ""

                    # A/S prices — hourly only at :00
                    if minute == 0 and hour in as_hourly:
                        for as_key, col_name in [("NR", "nr"), ("RD", "rd"), ("RMD", "rmd"), ("RMU", "rmu"), ("RU", "ru"), ("SR", "sr")]:
                            val = as_hourly[hour].get(as_key, "")
                            if isinstance(val, (int, float)):
                                row_data[col_name] = round(val, 2)
                            else:
                                row_data[col_name] = ""
                    else:
                        for col in ["nr", "rd", "rmd", "rmu", "ru", "sr"]:
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
print("  - Battery charging/discharging: All 5-minute intervals (MW)")
print("  - Demand: All 5-minute intervals (MW)")
print("  - Load: All 5-minute intervals (MW) = Demand + Battery Charging")
print("  - LMP prices: Hourly at :00 only ($/MWh) - includes MCC, MEC, GHG, Loss breakdown")
print("  - A/S prices: Hourly at :00 only ($/MW) - includes NR, RD, RMD, RMU, RU, SR")
print()
print("To append new data in the future:")
print("  1. Add new fuelsource CSV files to caiso_supply/")
print("  2. Add new demand CSV files to caiso_demand_downloads/")
print("  3. Update caiso_prices.json and ancillary_services.json")
print("  4. Re-run this script (it will regenerate the complete file)")
