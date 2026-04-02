"""
Append new data to comprehensive CSV (incremental update).

Much faster than regenerating entire file - only processes new dates.
For 1 new day: ~5-10 seconds vs 5-10 minutes for full regeneration.
"""
import os
import csv
import json
import glob
from datetime import datetime, timedelta
from pathlib import Path

SUPPLY_DIR = Path("caiso_supply")
DEMAND_DIR = Path("caiso_demand_downloads")
CSV_FILE = Path("caiso_comprehensive_data.csv")

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

HEADER = [
    "timestamp",
    "solar_mw", "wind_mw", "natural_gas_mw", "nuclear_mw", "large_hydro_mw",
    "small_hydro_mw", "geothermal_mw", "biomass_mw", "biogas_mw",
    "batteries_mw", "imports_mw", "other_mw", "coal_mw",
    "demand_mw",
    "lmp", "mcc", "mec", "ghg", "loss",
    "nr", "rd", "rmd", "rmu", "ru", "sr"
]

def get_last_csv_date():
    """Get the last date in the comprehensive CSV"""
    if not CSV_FILE.exists():
        return None

    try:
        with open(CSV_FILE, 'r', encoding='utf-8') as f:
            # Read last non-empty line
            lines = f.readlines()
            for line in reversed(lines):
                if line.strip() and not line.startswith('timestamp'):
                    last_timestamp = line.split(',')[0]
                    last_date = datetime.strptime(last_timestamp, "%Y-%m-%d %H:%M").date()
                    return last_date
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return None

    return None

def get_dates_to_append():
    """Find dates that need to be added to CSV"""
    last_date = get_last_csv_date()

    if last_date is None:
        print("CSV file not found or empty - run create_comprehensive_csv.py first")
        return []

    # Get all fuelsource files
    all_files = sorted(glob.glob(str(SUPPLY_DIR / "*_fuelsource.csv")))

    dates_to_add = []
    for fpath in all_files:
        basename = os.path.basename(fpath)
        date_str_raw = basename.split("_")[0]
        try:
            dt = datetime.strptime(date_str_raw, "%Y%m%d").date()
            if dt > last_date:
                dates_to_add.append(dt)
        except ValueError:
            continue

    return sorted(dates_to_add)

def append_date_data(date_obj, csv_writer):
    """Append one day's data to CSV"""
    date_str_raw = date_obj.strftime("%Y%m%d")
    date_key = date_obj.strftime("%Y-%m-%d")

    # Load demand for this day
    demand_file = DEMAND_DIR / f"{date_str_raw}_demand.csv"
    demand_hourly = {}

    if demand_file.exists():
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

    # Load LMP prices
    lmp_hourly = {}
    if os.path.exists("caiso_prices.json"):
        with open("caiso_prices.json") as f:
            lmp_data = json.load(f)
            if date_key in lmp_data:
                for hour_str, prices in lmp_data[date_key].items():
                    try:
                        hour = int(hour_str) - 1
                        lmp_hourly[hour] = prices
                    except:
                        pass

    # Load A/S prices
    as_hourly = {}
    if os.path.exists("ancillary_services.json"):
        with open("ancillary_services.json") as f:
            as_data = json.load(f)
            if date_key in as_data:
                for hour_str, as_prices in as_data[date_key].items():
                    try:
                        hour = int(hour_str) - 1
                        as_hourly[hour] = as_prices
                    except:
                        pass

    # Process fuelsource data
    fuelsource_file = SUPPLY_DIR / f"{date_str_raw}_fuelsource.csv"
    if not fuelsource_file.exists():
        return False

    rows_added = 0
    try:
        with open(fuelsource_file, "r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)

            for row in reader:
                time_str = row.get("Time", "")
                if not time_str:
                    continue

                try:
                    time_parts = time_str.split(":")
                    hour = int(time_parts[0])
                    minute = int(time_parts[1])
                    timestamp = datetime(date_obj.year, date_obj.month, date_obj.day, hour, minute)
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
                    row_data["demand_mw"] = round(demand_hourly.get(hour, ""), 2) if hour in demand_hourly else ""

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
                    # Empty hourly columns
                    for col in ["demand_mw", "lmp", "mcc", "mec", "ghg", "loss",
                               "nr", "rd", "rmd", "rmu", "ru", "sr"]:
                        row_data[col] = ""

                csv_writer.writerow(row_data)
                rows_added += 1

    except Exception as e:
        print(f"  ERROR processing {date_key}: {e}")
        return False

    return rows_added > 0

def main():
    """Main execution"""
    print("=" * 70)
    print("INCREMENTAL CSV UPDATE")
    print("=" * 70)

    # Check if CSV exists
    if not CSV_FILE.exists():
        print("\nERROR: Comprehensive CSV not found")
        print("Please run create_comprehensive_csv.py first to create the base file")
        return 1

    # Find dates to append
    print("\nChecking for new dates...")
    dates_to_add = get_dates_to_append()

    if not dates_to_add:
        print("✓ CSV is up to date - no new dates to add")
        return 0

    print(f"Found {len(dates_to_add)} new dates to append:")
    for d in dates_to_add[:5]:
        print(f"  - {d.strftime('%Y-%m-%d')}")
    if len(dates_to_add) > 5:
        print(f"  ... and {len(dates_to_add) - 5} more")

    # Open CSV in append mode
    print(f"\nAppending to {CSV_FILE}...")

    with open(CSV_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=HEADER)

        for i, date_obj in enumerate(dates_to_add, 1):
            date_str = date_obj.strftime('%Y-%m-%d')
            print(f"[{i}/{len(dates_to_add)}] {date_str}...", end='', flush=True)

            success = append_date_data(date_obj, writer)
            if success:
                print(" ✓")
            else:
                print(" ✗")

    # Verify
    new_last_date = get_last_csv_date()
    print(f"\n✓ CSV updated to {new_last_date}")

    # Show file size
    size_mb = CSV_FILE.stat().st_size / (1024 * 1024)
    print(f"✓ File size: {size_mb:.1f} MB")

    print("=" * 70)
    return 0

if __name__ == "__main__":
    exit(main())
