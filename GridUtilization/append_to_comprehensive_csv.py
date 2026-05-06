"""
Append new data to comprehensive CSV (incremental update).
Matches create_comprehensive_csv.py logic exactly.
"""
import os
import csv
import json
import glob
from datetime import datetime
from pathlib import Path

script_dir = Path(__file__).parent
SUPPLY_DIR = script_dir / "caiso_supply"
DEMAND_DIR = script_dir / "caiso_demand_downloads"
CSV_FILE = script_dir / "caiso_comprehensive_data.csv"

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

HEADER = [
    "timestamp",
    "solar_mw", "wind_mw", "natural_gas_mw", "nuclear_mw", "large_hydro_mw",
    "small_hydro_mw", "geothermal_mw", "biomass_mw", "biogas_mw",
    "batteries_mw", "imports_mw", "other_mw", "coal_mw",
    "battery_charging_mw", "battery_discharging_mw",
    "demand_mw", "load_mw",
    "lmp", "mcc", "mec", "ghg", "loss",
    "nr", "rd", "rmd", "rmu", "ru", "sr"
]


def get_last_csv_date():
    if not CSV_FILE.exists():
        return None
    try:
        with open(CSV_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in reversed(lines):
                if line.strip() and not line.startswith('timestamp'):
                    last_timestamp = line.split(',')[0]
                    # Try both formats: "YYYY-MM-DD HH:MM" and "M/D/YYYY HH:MM"
                    for fmt in ["%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M"]:
                        try:
                            return datetime.strptime(last_timestamp, fmt).date()
                        except ValueError:
                            continue
                    # If neither format works, raise error
                    raise ValueError(f"Cannot parse timestamp: {last_timestamp}")
    except Exception as e:
        print(f"Error reading CSV: {e}")
    return None


def truncate_incomplete_last_day():
    if not CSV_FILE.exists():
        return None

    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    if len(lines) <= 1:
        return None

    last_date_str = None
    last_date_count = 0
    for line in reversed(lines):
        if line.strip() and not line.startswith('timestamp'):
            date_part = line.split(',')[0].split(' ')[0]
            if last_date_str is None:
                last_date_str = date_part
            if date_part == last_date_str:
                last_date_count += 1
            else:
                break

    if last_date_count < 288:
        print(f"  Last day {last_date_str} is incomplete ({last_date_count}/288 rows) - removing for re-append")
        truncated = [lines[0]]
        for line in lines[1:]:
            if line.strip():
                date_part = line.split(',')[0].split(' ')[0]
                if date_part != last_date_str:
                    truncated.append(line)
        with open(CSV_FILE, 'w', encoding='utf-8', newline='') as f:
            f.writelines(truncated)
        # Parse date with both formats
        for fmt in ["%Y-%m-%d", "%m/%d/%Y"]:
            try:
                return datetime.strptime(last_date_str, fmt).date()
            except ValueError:
                continue
    return None


def find_dates_missing_prices():
    """Find dates in the CSV that have supply data but missing LMP/AS prices.
    These dates should be re-appended if price data is now available."""
    if not CSV_FILE.exists():
        return []

    # Load current price data availability (prefer 5-min, fall back to hourly)
    lmp_dates = set()
    as_dates = set()
    prices_5min_path = script_dir / "caiso_prices_5min.json"
    prices_path = script_dir / "caiso_prices.json"
    as_path = script_dir / "ancillary_services.json"
    if prices_5min_path.exists():
        with open(prices_5min_path) as f:
            lmp_dates = set(json.load(f).keys())
    if prices_path.exists():
        with open(prices_path) as f:
            lmp_dates |= set(json.load(f).keys())
    if as_path.exists():
        with open(as_path) as f:
            as_dates = set(json.load(f).keys())

    # Scan the last 7 days of CSV for rows with empty LMP at :00
    dates_with_empty_prices = set()
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        for line in reversed(f.readlines()[-3000:]):  # ~10 days of 5-min data
            if not line.strip() or line.startswith('timestamp'):
                continue
            parts = line.strip().split(',')
            ts = parts[0]
            if not ts.endswith(':00'):
                continue
            date_str = ts.split(' ')[0]
            # Check if LMP column (index 18) is empty
            lmp_val = parts[18] if len(parts) > 18 else ''
            if not lmp_val.strip():
                # Price was missing — check if it's now available
                if date_str in lmp_dates or date_str in as_dates:
                    dates_with_empty_prices.add(date_str)

    return sorted(dates_with_empty_prices)


def get_dates_to_append():
    incomplete_date = truncate_incomplete_last_day()
    last_date = get_last_csv_date()

    if last_date is None:
        print("CSV file not found or empty - run create_comprehensive_csv.py first")
        return []

    # New dates (supply files newer than CSV)
    all_files = sorted(glob.glob(str(SUPPLY_DIR / "*_fuelsource.csv")))
    dates_to_add = set()
    for fpath in all_files:
        basename = os.path.basename(fpath)
        date_str_raw = basename.split("_")[0]
        try:
            dt = datetime.strptime(date_str_raw, "%Y%m%d").date()
            if dt > last_date:
                dates_to_add.add(dt)
            elif incomplete_date and dt == incomplete_date:
                dates_to_add.add(dt)
        except ValueError:
            continue

    # Dates that now have price data available (were missing before)
    backfill_dates = find_dates_missing_prices()
    if backfill_dates:
        print(f"  Found {len(backfill_dates)} dates with newly available price data to backfill")
        for d in backfill_dates:
            dates_to_add.add(datetime.strptime(d, "%Y-%m-%d").date())

    return sorted(dates_to_add)


def append_date_data(date_obj, csv_writer):
    """Append one day's data — mirrors create_comprehensive_csv.py logic exactly."""
    date_str_raw = date_obj.strftime("%Y%m%d")
    date_key = date_obj.strftime("%Y-%m-%d")

    # Load 5-minute demand
    demand_file = DEMAND_DIR / f"{date_str_raw}_demand.csv"
    demand_5min = {}

    if demand_file.exists():
        try:
            with open(demand_file, "r", encoding="utf-8-sig") as f:
                lines = f.readlines()
                if len(lines) >= 5:
                    header_line = lines[0].strip().split(",")
                    time_labels = header_line[1:]
                    demand_line = lines[3].strip().split(",")
                    demand_values = [float(x) if x.strip() else None for x in demand_line[1:]]
                    for idx, (time_label, demand_val) in enumerate(zip(time_labels, demand_values)):
                        if demand_val is not None:
                            try:
                                hour, minute = map(int, time_label.strip().split(":"))
                                demand_5min[(hour, minute)] = demand_val
                            except:
                                pass
        except:
            pass

    # Load LMP prices — prefer 5-min load-weighted data, fall back to hourly
    lmp_5min = {}
    lmp_hourly = {}
    prices_5min_path = script_dir / "caiso_prices_5min.json"
    prices_path = script_dir / "caiso_prices.json"
    if prices_5min_path.exists():
        with open(prices_5min_path) as f:
            lmp_5min_data = json.load(f)
            if date_key in lmp_5min_data:
                # Keys like "0:00", "0:05", ... "23:55"
                for time_str, prices in lmp_5min_data[date_key].items():
                    try:
                        parts = time_str.split(":")
                        h, m = int(parts[0]), int(parts[1])
                        lmp_5min[(h, m)] = prices
                    except:
                        pass
    if not lmp_5min and prices_path.exists():
        # Fallback to hourly simple-average data (pre-2023 dates)
        with open(prices_path) as f:
            lmp_data = json.load(f)
            if date_key in lmp_data:
                for hour_str, prices in lmp_data[date_key].items():
                    try:
                        lmp_hourly[int(hour_str) - 1] = prices
                    except:
                        pass

    # Load A/S prices
    as_hourly = {}
    as_path = script_dir / "ancillary_services.json"
    if as_path.exists():
        with open(as_path) as f:
            as_data = json.load(f)
            if date_key in as_data:
                for hour_str, as_prices in as_data[date_key].items():
                    try:
                        as_hourly[int(hour_str) - 1] = as_prices
                    except:
                        pass

    # Process fuelsource
    fuelsource_file = SUPPLY_DIR / f"{date_str_raw}_fuelsource.csv"
    if not fuelsource_file.exists():
        return False

    rows_added = 0
    try:
        seen_midnight = False

        with open(fuelsource_file, "r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            # Case-insensitive column map
            first_row = None
            col_map = {}

            for row in reader:
                if not col_map:
                    col_map = {c.lower(): c for c in row.keys()}

                time_str = row.get("Time", "")
                if not time_str:
                    continue

                try:
                    time_parts = time_str.split(":")
                    hour = int(time_parts[0])
                    minute = int(time_parts[1])

                    if hour == 0 and minute == 0:
                        if seen_midnight:
                            continue
                        seen_midnight = True

                    timestamp = datetime(date_obj.year, date_obj.month, date_obj.day, hour, minute)
                except (ValueError, IndexError):
                    continue

                row_data = {"timestamp": timestamp.strftime("%Y-%m-%d %H:%M")}

                # Generation data (5-minute) with case-insensitive lookup
                battery_mw = 0.0
                for fuel_col, csv_col in FUEL_COLS:
                    try:
                        actual_col = col_map.get(fuel_col.lower(), fuel_col)
                        val = float(row.get(actual_col) or 0)
                        row_data[csv_col] = round(val, 2)
                        if csv_col == "batteries_mw":
                            battery_mw = val
                    except (ValueError, TypeError):
                        row_data[csv_col] = ""

                # Battery charging/discharging (5-minute)
                if battery_mw < 0:
                    row_data["battery_charging_mw"] = round(abs(battery_mw), 2)
                    row_data["battery_discharging_mw"] = 0.0
                else:
                    row_data["battery_charging_mw"] = 0.0
                    row_data["battery_discharging_mw"] = round(battery_mw, 2)

                # Demand and load (5-minute where available)
                if (hour, minute) in demand_5min:
                    demand_val = demand_5min[(hour, minute)]
                    row_data["demand_mw"] = round(demand_val, 2)
                    charging_val = row_data["battery_charging_mw"]
                    if isinstance(charging_val, (int, float)):
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
                            row_data[col_name] = round(val, 2) if isinstance(val, (int, float)) else ""
                    else:
                        for col in ["lmp", "mcc", "mec", "ghg", "loss"]:
                            row_data[col] = ""
                elif minute == 0 and hour in lmp_hourly:
                    for price_key, col_name in [("LMP", "lmp"), ("MCC", "mcc"), ("MEC", "mec"), ("GHG", "ghg"), ("Loss", "loss")]:
                        val = lmp_hourly[hour].get(price_key, "")
                        row_data[col_name] = round(val, 2) if isinstance(val, (int, float)) else ""
                else:
                    for col in ["lmp", "mcc", "mec", "ghg", "loss"]:
                        row_data[col] = ""

                # A/S prices — hourly only at :00
                if minute == 0 and hour in as_hourly:
                    for as_key, col_name in [("NR", "nr"), ("RD", "rd"), ("RMD", "rmd"), ("RMU", "rmu"), ("RU", "ru"), ("SR", "sr")]:
                        val = as_hourly[hour].get(as_key, "")
                        row_data[col_name] = round(val, 2) if isinstance(val, (int, float)) else ""
                else:
                    for col in ["nr", "rd", "rmd", "rmu", "ru", "sr"]:
                        row_data[col] = ""

                csv_writer.writerow(row_data)
                rows_added += 1

    except Exception as e:
        print(f"  ERROR processing {date_key}: {e}")
        return False

    return rows_added > 0


def main():
    print("=" * 70)
    print("INCREMENTAL CSV UPDATE")
    print("=" * 70)

    if not CSV_FILE.exists():
        print("\nERROR: Comprehensive CSV not found")
        print("Please run create_comprehensive_csv.py first to create the base file")
        return 1

    print("\nChecking for new dates...")
    dates_to_add = get_dates_to_append()

    if not dates_to_add:
        print("[OK] CSV is up to date - no new dates to add")
        return 0

    print(f"Found {len(dates_to_add)} new dates to append:")
    for d in dates_to_add[:5]:
        print(f"  - {d.strftime('%Y-%m-%d')}")
    if len(dates_to_add) > 5:
        print(f"  ... and {len(dates_to_add) - 5} more")

    # Remove any existing rows for dates we're about to re-append
    all_dates_strs = {d.strftime("%Y-%m-%d") for d in dates_to_add}
    last_date = get_last_csv_date()
    dates_to_remove = {d for d in all_dates_strs}  # remove all dates we'll re-append

    if last_date and dates_to_remove:
        # Check which of these dates actually exist in the CSV
        existing_in_csv = set()
        with open(CSV_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip() and not line.startswith('timestamp'):
                    date_part = line.split(',')[0].split(' ')[0]
                    if date_part in dates_to_remove:
                        existing_in_csv.add(date_part)

        if existing_in_csv:
            print(f"\nRemoving {len(existing_in_csv)} existing dates from CSV for re-append...")
            with open(CSV_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            filtered = [lines[0]]
            for line in lines[1:]:
                if line.strip():
                    date_part = line.split(',')[0].split(' ')[0]
                    if date_part not in existing_in_csv:
                        filtered.append(line)
            with open(CSV_FILE, 'w', encoding='utf-8', newline='') as f:
                f.writelines(filtered)
            print(f"  Removed rows for: {', '.join(sorted(existing_in_csv))}")

    print(f"\nAppending to {CSV_FILE}...")

    with open(CSV_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=HEADER)

        for i, date_obj in enumerate(dates_to_add, 1):
            date_str = date_obj.strftime('%Y-%m-%d')
            print(f"[{i}/{len(dates_to_add)}] {date_str}...", end='', flush=True)

            success = append_date_data(date_obj, writer)
            if success:
                print(" [OK]")
            else:
                print(" [ERROR]")

    new_last_date = get_last_csv_date()
    print(f"\n[OK] CSV updated to {new_last_date}")

    size_mb = CSV_FILE.stat().st_size / (1024 * 1024)
    print(f"[OK] File size: {size_mb:.1f} MB")

    print("=" * 70)
    return 0


if __name__ == "__main__":
    exit(main())
